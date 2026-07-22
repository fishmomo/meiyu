"""Local web tool for manually drawing a Meiyu-front grid mask.

Run with: ``python web_mask_picker/app.py`` and open http://127.0.0.1:5000.
The application intentionally stores no uploaded data on disk: the active
dataset is held in memory only until the browser is refreshed or a new file is
loaded.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
import xarray as xr
from flask import Flask, jsonify, render_template, request, send_file


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # CRA40 diagnostics can be large


def _configure_logging() -> logging.Logger:
    """Write operational diagnostics without logging field values or uploads."""
    log_dir = Path(os.environ.get("WEB_MASK_PICKER_LOG_DIR", Path(__file__).parent / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("web_mask_picker")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_dir / "app.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


LOGGER = _configure_logging()


@dataclass
class LoadedData:
    dataset: xr.Dataset
    variables: list[str]


SESSIONS: dict[str, LoadedData] = {}
LAT_NAMES = ("lat", "latitude", "Latitude", "LAT")
LON_NAMES = ("lon", "longitude", "Longitude", "LON")


def _coordinate_name(dataset: xr.Dataset, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in dataset.coords or name in dataset.variables:
            return name
    raise ValueError(f"未找到坐标变量：需要 {', '.join(candidates)} 中的一个")


def _spatial_field(dataset: xr.Dataset, variable: str, indexes: dict[str, int]) -> tuple[xr.DataArray, str, str]:
    if variable not in dataset.data_vars:
        raise ValueError("所选变量不存在")
    lat_name = _coordinate_name(dataset, LAT_NAMES)
    lon_name = _coordinate_name(dataset, LON_NAMES)
    field = dataset[variable]
    lat_dim = dataset[lat_name].dims[0]
    lon_dim = dataset[lon_name].dims[0]
    if lat_dim not in field.dims or lon_dim not in field.dims:
        raise ValueError("所选变量不包含 lat/lon 两个空间维度")
    for dim in list(field.dims):
        if dim not in (lat_dim, lon_dim):
            field = field.isel({dim: int(indexes.get(dim, 0))})
    return field.transpose(lat_dim, lon_dim), lat_name, lon_name


def _json_field(dataset: xr.Dataset, variable: str, indexes: dict[str, int]) -> dict:
    field, lat_name, lon_name = _spatial_field(dataset, variable, indexes)
    values = np.asarray(field.values, dtype=float)
    # The canvas cannot meaningfully select a curvilinear grid. CRA40 is 1-D
    # latitude/longitude, which is the supported operational input.
    lat = np.asarray(dataset[lat_name].values, dtype=float)
    lon = np.asarray(dataset[lon_name].values, dtype=float)
    if lat.ndim != 1 or lon.ndim != 1:
        raise ValueError("当前版本只支持一维 lat/lon 规则格点")
    other_dims = [d for d in dataset[variable].dims if d not in (field.dims[0], field.dims[1])]
    selectors = [{"name": d, "size": int(dataset.sizes[d]), "selected": int(indexes.get(d, 0))} for d in other_dims]
    finite = values[np.isfinite(values)]
    return {
        "values": np.where(np.isfinite(values), values, None).tolist(),
        "lat": lat.tolist(),
        "lon": lon.tolist(),
        "units": dataset[variable].attrs.get("units", ""),
        "long_name": dataset[variable].attrs.get("long_name", variable),
        "selectors": selectors,
        "min": float(np.nanmin(finite)) if finite.size else 0.0,
        "max": float(np.nanmax(finite)) if finite.size else 1.0,
    }


def build_mask_dataset(source: xr.Dataset, variable: str, indexes: dict[str, int], mask: np.ndarray) -> xr.Dataset:
    """Build the portable mask file while preserving the source grid exactly."""
    field, lat_name, lon_name = _spatial_field(source, variable, indexes)
    bool_mask = np.asarray(mask, dtype=bool)
    if bool_mask.shape != field.shape:
        raise ValueError(f"掩码形状 {bool_mask.shape} 与数据格点 {field.shape} 不一致")
    lat_dim, lon_dim = field.dims
    result = xr.Dataset(
        data_vars={
            "meiyu_front_mask": ((lat_dim, lon_dim), bool_mask),
        },
        coords={
            lat_dim: source[lat_dim],
            lon_dim: source[lon_dim],
        },
        attrs={
            "title": "Manually selected Meiyu-front grid mask",
            "source_variable": variable,
            "Conventions": "CF-1.8",
        },
    )
    # Retain both common coordinate variable names when they differ from dims.
    if lat_name != lat_dim:
        result[lat_name] = source[lat_name]
    if lon_name != lon_dim:
        result[lon_name] = source[lon_name]
    result["meiyu_front_mask"].attrs.update({
        "long_name": "manually selected Meiyu-front area",
        "flag_values": np.array([0, 1], dtype=np.int8),
        "flag_meanings": "outside_meiyu_front inside_meiyu_front",
        "coordinates": f"{lon_name} {lat_name}",
    })
    return result


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.after_request
def disable_browser_cache(response):
    """Always serve the current local UI while it is being iterated on."""
    if request.path == "/" or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.route("/api/load", methods=["POST"])
def load_file():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        LOGGER.warning("load_rejected reason=no_file remote=%s", request.remote_addr)
        return jsonify(error="请选择一个 NetCDF 文件"), 400
    try:
        raw = io.BytesIO(upload.read())
        # Uploaded diagnostic files are commonly NetCDF4/HDF5.  This xarray
        # version cannot select the netCDF4 backend from an in-memory stream,
        # so use an ASCII temporary path (also avoids Windows Chinese-path
        # issues) and close it before loading.
        suffix = Path(upload.filename).suffix or ".nc"
        with tempfile.NamedTemporaryFile(prefix="meiyu_mask_", suffix=suffix, delete=False) as stream:
            stream.write(raw.getbuffer())
            temporary_path = Path(stream.name)
        try:
            ds = xr.open_dataset(temporary_path, engine="netcdf4").load()
            ds.close()
        finally:
            temporary_path.unlink(missing_ok=True)
        variables = [name for name, item in ds.data_vars.items() if item.ndim >= 2]
        if not variables:
            raise ValueError("文件中没有至少二维的诊断量")
        _coordinate_name(ds, LAT_NAMES)
        _coordinate_name(ds, LON_NAMES)
        token = uuid.uuid4().hex
        SESSIONS[token] = LoadedData(ds, variables)
        replaced_token = request.form.get("replace_token")
        if replaced_token and replaced_token != token:
            SESSIONS.pop(replaced_token, None)
        LOGGER.info(
            "load_ok filename=%r bytes=%d dimensions=%s variables=%s token=%s replaced=%s",
            upload.filename, raw.getbuffer().nbytes, dict(ds.sizes), variables, token[:8], str(replaced_token)[:8],
        )
        return jsonify(token=token, variables=variables)
    except Exception as exc:
        LOGGER.exception("load_failed filename=%r bytes=%d", upload.filename, raw.getbuffer().nbytes if "raw" in locals() else 0)
        return jsonify(error=str(exc)), 400


@app.route("/api/field", methods=["POST"])
def field():
    body = request.get_json(force=True)
    loaded = SESSIONS.get(body.get("token"))
    if not loaded:
        LOGGER.warning("field_rejected reason=expired_session token=%s", str(body.get("token"))[:8])
        return jsonify(error="数据会话已失效，请重新导入文件"), 404
    try:
        result = _json_field(loaded.dataset, body["variable"], body.get("indexes", {}))
        LOGGER.info("field_ok variable=%s indexes=%s shape=%dx%d", body["variable"], body.get("indexes", {}), len(result["lat"]), len(result["lon"]))
        return jsonify(result)
    except Exception as exc:
        LOGGER.exception("field_failed variable=%r indexes=%s", body.get("variable"), body.get("indexes", {}))
        return jsonify(error=str(exc)), 400


@app.route("/api/export", methods=["POST"])
def export():
    body = request.get_json(force=True)
    loaded = SESSIONS.get(body.get("token"))
    if not loaded:
        LOGGER.warning("export_rejected reason=expired_session token=%s", str(body.get("token"))[:8])
        return jsonify(error="数据会话已失效，请重新导入文件"), 404
    try:
        mask = np.asarray(body["mask"], dtype=bool)
        ds = build_mask_dataset(loaded.dataset, body["variable"], body.get("indexes", {}), mask)
        # ``path=None`` returns portable NetCDF bytes. It avoids keeping a
        # temporary file locked on Windows while Flask streams the download.
        target = io.BytesIO(ds.to_netcdf())
        # The project environment currently ships Flask 1.x, whose equivalent
        # of Flask 2's ``download_name`` is ``attachment_filename``.
        LOGGER.info("export_ok variable=%s indexes=%s shape=%s selected_cells=%d", body["variable"], body.get("indexes", {}), mask.shape, int(mask.sum()))
        return send_file(target, as_attachment=True, attachment_filename="meiyu_front_mask.nc", mimetype="application/x-netcdf")
    except Exception as exc:
        LOGGER.exception("export_failed variable=%r indexes=%s", body.get("variable"), body.get("indexes", {}))
        return jsonify(error=str(exc)), 400


@app.route("/api/client-log", methods=["POST"])
def client_log():
    """Record browser-side progress/errors to diagnose local UI failures."""
    body = request.get_json(silent=True) or {}
    event = str(body.get("event", "unknown"))[:80]
    detail = str(body.get("detail", ""))[:1000]
    LOGGER.info("client_%s detail=%s", event, detail)
    return ("", 204)


if __name__ == "__main__":
    # Keep a single stable local process. Flask's debug reloader starts a
    # watchdog child that can exit when launched from a .bat/background shell.
    app.run(host="127.0.0.1", port=5000, debug=False)
