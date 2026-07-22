const el = id => document.getElementById(id);
const canvas = el('map'), ctx = canvas.getContext('2d');
const legend = el('legend'), lctx = legend.getContext('2d');
let token, data, mask = [], history = [], mode = 'point';
let view = {scale: 1, x: 0, y: 0}, drag = null, box = null, lasso = null;
let batchFiles = [], batchIndex = -1;
let referenceMask = null, activeBatchKey = null, batchMasks = new Map();

function clientLog(event, detail=''){
  fetch('/api/client-log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event,detail})}).catch(()=>{});
}
window.addEventListener('error', event => {
  // 浏览器在画布尺寸变动时偶尔产生此无害提示；不写入日志，避免淹没真正错误。
  if (String(event.message).includes('ResizeObserver loop')) return;
  clientLog('javascript_error', `${event.message} @ ${event.filename}:${event.lineno}`);
});
window.addEventListener('unhandledrejection', event => clientLog('promise_rejection', String(event.reason)));

const stops = {
  YlOrRd: ['#ffffcc','#ffeda0','#fed976','#feb24c','#fd8d3c','#f03b20','#bd0026'],
  RdBu_r: ['#2166ac','#67a9cf','#d1e5f0','#f7f7f7','#fddbc7','#ef8a62','#b2182b'],
  PuOr_r: ['#2d004b','#542788','#8073ac','#b2abd2','#f7f7f7','#fdb863','#e08214','#b35806','#7f3b08'],
  YlGnBu: ['#ffffd9','#edf8b1','#c7e9b4','#7fcdbb','#41b6c4','#1d91c0','#225ea8']
};
function hexRgb(hex){return [parseInt(hex.slice(1,3),16),parseInt(hex.slice(3,5),16),parseInt(hex.slice(5,7),16)];}
function colour(t){
  const levels=+el('levels').value, snapped=Math.floor(Math.max(0,Math.min(.999999,t))*levels)/(levels-1);
  const s=stops[el('cmap').value], q=snapped*(s.length-1), i=Math.floor(q), f=q-i;
  // t=1 对应最后一个颜色节点，此时不能再读取 s[i+1]。
  const a=hexRgb(s[i]), b=hexRgb(s[Math.min(i+1,s.length-1)]); return `rgb(${a.map((v,k)=>Math.round(v+(b[k]-v)*f)).join(',')})`;
}
function formatValue(value){return Number(value).toFixed(2);}
function defaultExportName(sourceName){const compact=sourceName.match(/(20\d{6})[_-]?(\d{2})/);if(compact)return `front_mask_${compact[1]}_${compact[2]}.nc`;const dateOnly=sourceName.match(/(20\d{6})/);return dateOnly?`front_mask_${dateOnly[1]}.nc`:'front_mask.nc';}
function selectors(){const o={}; document.querySelectorAll('[data-dim]').forEach(x=>o[x.dataset.dim]=+x.value); return o;}
function setEnabled(value){document.querySelectorAll('button').forEach(b=>{if(b.id !== 'apply-range' || data)b.disabled=!value}); el('variable').disabled=!value;el('export-name').disabled=!value;}
function resetMask(){mask=Array.from({length:data.lat.length},()=>Array(data.lon.length).fill(false));history=[]; updateCount();}
function updateCount(){el('count').textContent=`已选取：${mask.flat().filter(Boolean).length} 格点`;el('undo').disabled=!history.length;}
function saveHistory(){history.push(mask.map(row=>row.slice())); if(history.length>30)history.shift();}
function resize(){const r=canvas.parentElement.getBoundingClientRect(), d=devicePixelRatio;canvas.width=r.width*d;canvas.height=r.height*d;ctx.setTransform(d,0,0,d,0,0);draw();}
function bounds(){return {w:data.lon.length*view.scale,h:data.lat.length*view.scale};}
function coordinatePixel(value, coords, origin){const first=Number(coords[0]),last=Number(coords[coords.length-1]);if(!Number.isFinite(first)||!Number.isFinite(last)||first===last)return null;return origin+(value-first)/(last-first)*(coords.length-1)*view.scale;}
function drawDomainBox(){if(!el('domain-box').checked)return;const x1=coordinatePixel(90,data.lon,view.x),x2=coordinatePixel(135,data.lon,view.x),y1=coordinatePixel(20,data.lat,view.y),y2=coordinatePixel(50,data.lat,view.y);if([x1,x2,y1,y2].some(v=>v===null||!Number.isFinite(v)))return;const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.abs(x2-x1),h=Math.abs(y2-y1);ctx.save();ctx.strokeStyle='rgba(0,0,0,.9)';ctx.lineWidth=5;ctx.strokeRect(x,y,w,h);ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);ctx.fillStyle='#ffffff';ctx.font='bold 12px sans-serif';ctx.fillText('90–135°E, 20–50°N',x+6,y+16);ctx.restore();}
function fit(){if(!data)return;const r=canvas.getBoundingClientRect();view.scale=Math.min((r.width-20)/data.lon.length,(r.height-20)/data.lat.length);view.x=(r.width-data.lon.length*view.scale)/2;view.y=(r.height-data.lat.length*view.scale)/2;draw();}
function point(ev){const r=canvas.getBoundingClientRect();return{x:ev.clientX-r.left,y:ev.clientY-r.top};}
function cellAt(p){if(!data)return null;const c=Math.floor((p.x-view.x)/view.scale),r=Math.floor((p.y-view.y)/view.scale);return r>=0&&r<data.lat.length&&c>=0&&c<data.lon.length?{r,c}:null;}
function drawLegend(){if(!data)return;lctx.clearRect(0,0,legend.width,legend.height);const levels=+el('levels').value,w=legend.width/levels;for(let i=0;i<levels;i++){lctx.fillStyle=colour(i/(levels-1));lctx.fillRect(i*w,0,Math.ceil(w),legend.height);}el('legend-label').textContent=`${formatValue(el('vmin').value)} — ${formatValue(el('vmax').value)} ${data.units||''} (${levels} 层)`;}
function drawMaskPoints(points, colour){if(!points)return;ctx.fillStyle=colour;for(let i=0;i<points.length;i++)for(let j=0;j<(points[i]||[]).length;j++)if(points[i][j]){ctx.beginPath();ctx.arc(view.x+(j+.5)*view.scale,view.y+(i+.5)*view.scale,Math.max(2,Math.min(5,view.scale*.22)),0,Math.PI*2);ctx.fill();}}
function draw(){if(!data)return;const r=canvas.getBoundingClientRect();ctx.clearRect(0,0,r.width,r.height);const min=+el('vmin').value,max=+el('vmax').value, span=max-min||1;
  for(let i=0;i<data.lat.length;i++)for(let j=0;j<data.lon.length;j++){const v=data.values[i][j];ctx.fillStyle=v===null?'#e2e8f0':colour((v-min)/span);ctx.fillRect(view.x+j*view.scale,view.y+i*view.scale,view.scale,view.scale);}
  if(view.scale>=5){ctx.strokeStyle='rgba(0,0,0,.8)';ctx.lineWidth=1;ctx.beginPath();for(let i=0;i<=data.lat.length;i++){let y=view.y+i*view.scale;ctx.moveTo(view.x,y);ctx.lineTo(view.x+data.lon.length*view.scale,y);}for(let j=0;j<=data.lon.length;j++){let x=view.x+j*view.scale;ctx.moveTo(x,view.y);ctx.lineTo(x,view.y+data.lat.length*view.scale);}ctx.stroke();}
  drawDomainBox();
  drawMaskPoints(referenceMask,'#ffffff');drawMaskPoints(mask,'#7e22ce');
  if(box){ctx.strokeStyle='#ef4444';ctx.lineWidth=2;ctx.strokeRect(box.x,box.y,box.w,box.h);}
  if(lasso?.length>1){ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(lasso[0].x,lasso[0].y);for(let i=1;i<lasso.length;i++)ctx.lineTo(lasso[i].x,lasso[i].y);ctx.lineTo(lasso[0].x,lasso[0].y);ctx.stroke();}drawLegend();
}
async function loadField({resetSelection=true,preserveRange=false,preserveView=false}={}){clientLog('field_request',`variable=${el('variable').value}`);const response=await fetch('/api/field',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,variable:el('variable').value,indexes:selectors()})});const body=await response.json();if(!response.ok)throw Error(body.error);data=body;
  if(!preserveRange){el('vmin').value=body.min;el('vmax').value=body.max;}el('field-title').textContent=`${body.long_name} (${body.units||'无单位'}) · ${body.lat.length} × ${body.lon.length}`;
  el('selectors').innerHTML=body.selectors.map(s=>`<label>${s.name} <select data-dim="${s.name}">${Array.from({length:s.size},(_,i)=>`<option value="${i}" ${i===s.selected?'selected':''}>${i}</option>`).join('')}</select></label>`).join('');document.querySelectorAll('[data-dim]').forEach(s=>s.onchange=()=>loadField({resetSelection:false}));
  const gridChanged=mask.length!==body.lat.length||mask[0]?.length!==body.lon.length;
  if(resetSelection||gridChanged)resetMask();if(!preserveView||gridChanged)fit();else draw();setEnabled(true);updateBatchControls();clientLog('field_rendered',`variable=${el('variable').value} shape=${body.lat.length}x${body.lon.length} mask=${resetSelection||gridChanged?'reset':'preserved'}`);
}
function updateBatchControls(){const enabled=el('import-mode').value==='batch'&&batchFiles.length>0;el('batch-controls').hidden=!enabled;el('batch-status').hidden=!enabled;if(!enabled)return;el('previous-file').disabled=batchIndex<=0;el('next-file').disabled=batchIndex<0||batchIndex>=batchFiles.length-1;el('batch-status').textContent=`${batchIndex+1} / ${batchFiles.length}：${batchFiles[batchIndex].name}`;}
function cloneMask(source){return source.map(row=>row.slice());}
function batchKey(file){return file.webkitRelativePath||file.name;}
function rememberCurrentBatchMask(){if(activeBatchKey&&mask.length)batchMasks.set(activeBatchKey,cloneMask(mask));}
function prepareBatchMask(file){const cached=batchMasks.get(batchKey(file));if(cached){mask=cloneMask(cached);referenceMask=null;}else{referenceMask=mask.length?cloneMask(mask):null;mask=[];history=[];}}
async function importFile(file,{preserveControls=false,switchBatch=false}={}){const previous={variable:el('variable').value};clientLog('upload_selected',`${file.name} bytes=${file.size}`);el('file-status').textContent='正在读取…';try{const form=new FormData();form.append('file',file);if(token)form.append('replace_token',token);const res=await fetch('/api/load',{method:'POST',body:form}),body=await res.json();if(!res.ok)throw Error(body.error);token=body.token;const selected=preserveControls&&body.variables.includes(previous.variable)?previous.variable:body.variables[0];el('variable').innerHTML=body.variables.map(v=>`<option ${v===selected?'selected':''}>${v}</option>`).join('');el('export-name').value=defaultExportName(file.name);if(switchBatch)prepareBatchMask(file);else referenceMask=null;el('file-status').textContent=`已导入：${file.name}`;clientLog('upload_complete',`${file.name} variables=${body.variables.length}`);await loadField({resetSelection:!switchBatch,preserveRange:preserveControls,preserveView:preserveControls});if(switchBatch)activeBatchKey=batchKey(file);}catch(e){clientLog('upload_failed',`${file.name}: ${e.message}`);el('file-status').textContent=`导入失败：${e.message}`;throw e;}}
el('file').onchange=async()=>{const file=el('file').files[0];if(!file)return;batchFiles=[];batchIndex=-1;batchMasks.clear();activeBatchKey=null;referenceMask=null;updateBatchControls();try{await importFile(file);}catch(_){}};
el('batch-files').onchange=async()=>{batchFiles=Array.from(el('batch-files').files).filter(f=>/\.(nc|nc4|cdf)$/i.test(f.name)).sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}));batchMasks.clear();activeBatchKey=null;referenceMask=null;if(!batchFiles.length){el('file-status').textContent='所选文件夹内没有 NC 文件。';batchIndex=-1;updateBatchControls();return;}batchIndex=0;try{await importFile(batchFiles[batchIndex],{preserveControls:false});activeBatchKey=batchKey(batchFiles[batchIndex]);}catch(_){ }updateBatchControls();};
el('previous-file').onclick=async()=>{if(batchIndex<=0)return;rememberCurrentBatchMask();batchIndex--;try{await importFile(batchFiles[batchIndex],{preserveControls:true,switchBatch:true});}catch(_){batchIndex++;}updateBatchControls();};
el('next-file').onclick=async()=>{if(batchIndex>=batchFiles.length-1)return;rememberCurrentBatchMask();batchIndex++;try{await importFile(batchFiles[batchIndex],{preserveControls:true,switchBatch:true});}catch(_){batchIndex--;}updateBatchControls();};
el('import-mode').onchange=()=>{const batch=el('import-mode').value==='batch';el('single-file-wrap').hidden=batch;el('batch-file-wrap').hidden=!batch;updateBatchControls();};
el('variable').onchange=()=>loadField({resetSelection:false});el('cmap').onchange=draw;el('levels').onchange=draw;el('domain-box').onchange=draw;el('apply-range').onclick=draw;
function setMode(next){mode=next;['point','remove','box','lasso','pan'].forEach(name=>el(`mode-${name}`).classList.toggle('active',name===next));}
el('mode-point').onclick=()=>setMode('point');el('mode-remove').onclick=()=>setMode('remove');el('mode-box').onclick=()=>setMode('box');el('mode-lasso').onclick=()=>setMode('lasso');el('mode-pan').onclick=()=>setMode('pan');
el('undo').onclick=()=>{if(history.length){mask=history.pop();updateCount();draw();}};el('clear').onclick=()=>{saveHistory();resetMask();draw();};
function insidePolygon(point, polygon){let inside=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){const a=polygon[i],b=polygon[j],cross=(a.y>point.y)!==(b.y>point.y)&&point.x<(b.x-a.x)*(point.y-a.y)/(b.y-a.y)+a.x;if(cross)inside=!inside;}return inside;}
canvas.addEventListener('contextmenu',e=>e.preventDefault());canvas.onmousedown=e=>{const p=point(e);if(e.button===2||mode==='pan'){drag={p,x:view.x,y:view.y};return;}if(e.button!==0||!data)return;if(mode==='point'||mode==='remove'){const c=cellAt(p);if(c){saveHistory();mask[c.r][c.c]=mode==='point';updateCount();draw();}}else if(mode==='lasso'){lasso=[p];}else{box={x:p.x,y:p.y,w:0,h:0};}};
canvas.onmousemove=e=>{const p=point(e),c=cellAt(p);el('cursor').textContent=c?`lat ${data.lat[c.r].toFixed(3)}, lon ${data.lon[c.c].toFixed(3)}, 值 ${data.values[c.r][c.c]??'缺测'}`:'';if(drag){view.x=drag.x+p.x-drag.p.x;view.y=drag.y+p.y-drag.p.y;draw();}if(box){box.w=p.x-box.x;box.h=p.y-box.y;draw();}if(lasso){const last=lasso[lasso.length-1];if(Math.hypot(p.x-last.x,p.y-last.y)>=2)lasso.push(p);draw();}};
canvas.onmouseup=e=>{if(box){const a=cellAt({x:Math.min(box.x,box.x+box.w),y:Math.min(box.y,box.y+box.h)}),b=cellAt({x:Math.max(box.x,box.x+box.w),y:Math.max(box.y,box.y+box.h)});if(a&&b){saveHistory();for(let i=a.r;i<=b.r;i++)for(let j=a.c;j<=b.c;j++)mask[i][j]=true;updateCount();}box=null;draw();}if(lasso){const p=point(e),last=lasso[lasso.length-1];if(Math.hypot(p.x-last.x,p.y-last.y)>=2)lasso.push(p);if(lasso.length>=3){saveHistory();for(let i=0;i<data.lat.length;i++)for(let j=0;j<data.lon.length;j++)if(insidePolygon({x:view.x+(j+.5)*view.scale,y:view.y+(i+.5)*view.scale},lasso))mask[i][j]=true;updateCount();}lasso=null;draw();}drag=null;};
canvas.addEventListener('wheel',e=>{if(!data)return;e.preventDefault();const p=point(e),old=view.scale,scale=Math.max(2,Math.min(80,old*(e.deltaY<0?1.15:1/1.15)));view.x=p.x-(p.x-view.x)*scale/old;view.y=p.y-(p.y-view.y)*scale/old;view.scale=scale;draw();},{passive:false});
el('export').onclick=async()=>{try{let filename=el('export-name').value.trim();if(!filename){alert('请先填写输出文件名。');el('export-name').focus();return;}filename=filename.replace(/[\\/:*?"<>|]/g,'_');if(!filename.toLowerCase().endsWith('.nc'))filename+='.nc';el('export-name').value=filename;const r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,variable:el('variable').value,indexes:selectors(),mask})});if(!r.ok){const x=await r.json();throw Error(x.error);}const a=document.createElement('a');a.href=URL.createObjectURL(await r.blob());a.download=filename;a.click();URL.revokeObjectURL(a.href);}catch(e){alert(`导出失败：${e.message}`);}};
new ResizeObserver(resize).observe(canvas.parentElement);
clientLog('page_loaded',location.href);
