from datetime import datetime


def cra40_front2_subarea_time_token(dt: str) -> str:
    return datetime.strptime(dt, "%Y-%m-%dT%H").strftime("%m%dT%H")
