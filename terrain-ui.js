/* All terrain measurements use native projected metre grids. No remote requests contain user input. */
(() => {
  'use strict';
  const el = name => document.getElementById('terrain-' + name);
  const core = window.RailTerrain;
  const nf = (x, digits = 1) => Number.isFinite(x)
    ? x.toLocaleString('zh-TW', {maximumFractionDigits: digits, minimumFractionDigits: digits}) : '—';
  const regions = {northlink:'北迴・花蓮北部', yilan:'宜蘭・蘇澳周邊', southlink:'南迴・太麻里周邊', neiwan:'內灣・新竹山區'};
  const stops = {edge:'到達圖幅邊界，圖外流向未知', sink:'抵達局部低點', flat:'抵達無法辨識下坡方向的平地', nodata:'碰到缺值或其邊緣', invalid:'起點無有效高程'};
  const NS = 'http://www.w3.org/2000/svg';
  let entries = [], loadingCatalog = false, grid = null, network = null, token = 0;
  let requestedRegion = 'yilan', comparisons = {};
  let mode = 'line', vertices = [], path = [], samples = [], stop = '', cursor = 0, inspecting = 0, preset = false;
  let minimum = 0, maximum = 0, localGrid = null;

  function svg(tag, attrs, content) {
    const node = document.createElementNS(NS, tag);
    for (const [key, val] of Object.entries(attrs)) node.setAttribute(key, val);
    if (content !== undefined) node.textContent = content;
    return node;
  }
  function options(select, pairs, active) {
    select.replaceChildren(...pairs.map(([value, title]) => new Option(title, value)));
    if (pairs.some(([value]) => value === active)) select.value = active;
  }
  const col = i => i % grid.cols;
  const row = i => Math.floor(i / grid.cols);
  const point = i => [col(i) + .5, row(i) + .5];
  const valid = i => Number.isFinite(grid.values[i]);
  function closestTo(c, r) {
    let id = -1, best = Infinity;
    for (let i = 0; i < grid.values.length; i++) {
      if (!valid(i)) continue;
      const d = (col(i) - c) ** 2 + (row(i) - r) ** 2;
      if (d < best) { id = i; best = d; }
    }
    return id;
  }

  async function loadCatalog() {
    if (entries.length || loadingCatalog) return;
    loadingCatalog = true;
    fetch('data/terrain/comparison.json').then(response => response.ok ? response.json() : null)
      .then(data => {comparisons = data?.regions || {}; if (grid) showEvidence();})
      .catch(() => {});
    try {
      const response = await fetch('data/terrain/catalog.json');
      if (!response.ok) throw Error();
      const data = await response.json();
      if (!Array.isArray(data) || !data.length) throw Error();
      entries = data;
      regionOptions(requestedRegion);
      await selectSource();
    } catch (_) {
      el('status').textContent = '無法讀取地形目錄。可重新開啟地形分頁，或匯入本機 .asc 網格。';
    } finally { loadingCatalog = false; }
  }
  function regionOptions(keep) {
    const available = Object.entries(regions).filter(([id]) => entries.some(e => e.region === id));
    if (localGrid) available.push(['local','本機匯入']);
    options(el('region'), available, keep);
  }
  async function selectSource(preferred) {
    const id = el('region').value;
    const pairs = id === 'local' ? [['local','本機高程網格']] :
      entries.filter(e => e.region === id).map(e => [e.id, e.label]);
    options(el('source'), pairs, preferred);
    await loadGrid();
  }
  async function loadGrid() {
    const request = ++token;
    const selection = el('source').value;
    grid = null; network = null; samples = [];
    el('work').hidden = true;
    el('status').textContent = '正在讀取高程網格…';
    try {
      let data;
      if (selection === 'local') data = localGrid;
      else {
        const entry = entries.find(e => e.id === selection);
        if (!entry) throw Error('尚無可讀取圖幅。');
        const response = await fetch('data/terrain/' + entry.file);
        if (!response.ok) throw Error('圖幅下載失敗。');
        data = await response.json();
      }
      if (request !== token) return;
      installGrid(data);
    } catch (err) {
      if (request !== token) return;
      grid = null;
      el('status').textContent = (err.message || '圖幅無法載入。') + ' 請重選資料來源或匯入本機網格。';
    }
  }
  function installGrid(data) {
    grid = data;
    if (grid.status === 'unavailable' && grid.validCells === 0) {
      network = null; samples = []; path = []; vertices = [];
      el('work').hidden = false;
      el('work').querySelector('.terrain-layout').hidden = true;
      el('status').textContent = grid.name+'：'+grid.source+' 的 '+grid.values.length.toLocaleString('zh-TW')+' 格全部缺值。這個來源無法計算剖面或流向。';
      showEvidence(); return;
    }
    network = core.drainage(data);
    el('work').querySelector('.terrain-layout').hidden = false;
    el('status').textContent = '';
    minimum = Infinity; maximum = -Infinity;
    for (const h of grid.values) if (Number.isFinite(h)) {minimum = Math.min(minimum,h);maximum = Math.max(maximum,h);}
    if (!Number.isFinite(minimum)) throw Error('此圖幅沒有有效高程。');
    mode = 'line'; preset = true;
    const a = closestTo(grid.cols * .19, grid.rows * .72);
    const b = closestTo(grid.cols * .8, grid.rows * .28);
    vertices = a === b ? [a] : [a,b]; cursor = a; inspecting = 0;
    const available = grid.values.reduce((n,z) => n + Number(Number.isFinite(z)),0);
    el('spacing').textContent = nf(grid.cellSize, grid.cellSize % 1 ? 1 : 0) + ' m 網格';
    const centre = Math.floor(grid.rows / 2) * grid.cols + Math.floor(grid.cols / 2);
    el('coverage').textContent = grid.name + ' · 有效覆蓋 ' + nf(100 * available / grid.values.length) + '%' + (!valid(centre) ? ' · 圖幅中心缺值' : '');
    el('range').textContent = nf(minimum,0) + ' 至 ' + nf(maximum,0) + ' m';
    el('work').hidden = false;
    el('context').hidden = !regions[grid.region];
    const frame = el('frame');
    frame.style.width = 'min(100%, ' + (370 * Math.min(1.85,grid.cols / grid.rows)) + 'px)';
    frame.style.aspectRatio = grid.cols + ' / ' + grid.rows;
    el('overlay').setAttribute('viewBox', '0 0 ' + grid.cols + ' ' + grid.rows);
    showEvidence(); paint(); recalculate();
  }

  const colors = [[35,72,75],[77,115,103],[132,158,127],[211,199,149],[239,229,201]];
  function paint() {
    if (!grid || !network) return;
    const canvas = el('raster');
    canvas.width = grid.cols; canvas.height = grid.rows;
    const ctx = canvas.getContext('2d');
    const bitmap = ctx.createImageData(grid.cols,grid.rows);
    const threshold = Number(el('threshold').value) * 10000;
    for (let i = 0; i < grid.values.length; i++) {
      const h = grid.values[i];
      let rgb;
      if (!valid(i)) rgb = (col(i) + row(i)) % 6 < 2 ? [61,73,78] : [43,56,59];
      else {
        const u = 4 * (h - minimum) / (maximum - minimum || 1);
        const k = Math.min(3, Math.floor(u)), t = u - k;
        const east = col(i) + 1 < grid.cols && valid(i + 1) ? grid.values[i + 1] : h;
        const south = row(i) + 1 < grid.rows && valid(i + grid.cols) ? grid.values[i + grid.cols] : h;
        const shade = 1 + .23 * Math.tanh((east + south - 2 * h) / grid.cellSize);
        rgb = colors[k].map((v,j) => (v * (1-t) + colors[k+1][j]*t) * shade);
        if (threshold > 0 && network.area[i] >= threshold) rgb = [72,185,232];
      }
      bitmap.data.set([...rgb,255],4*i);
    }
    ctx.putImageData(bitmap,0,0); scaleBar();
  }
  function scaleBar() {
    if (!grid || !el('frame').clientWidth) return;
    const m = grid.cellSize * grid.cols * .22, p = 10 ** Math.floor(Math.log10(m));
    const metres = ([5,2,1].find(v => v*p <= m) || 1) * p;
    el('scale').replaceChildren(document.createTextNode(nf(metres,metres < 1 ? 2 : 0)+' m'),document.createElement('i'));
    el('scale').lastChild.style.width = (metres * el('frame').clientWidth / (grid.cols * grid.cellSize)) + 'px';
  }
  function addPoint(i) {
    if (!grid) return;
    if (!valid(i)) {el('status').textContent = '此格沒有有效高程，請在有色地形中選點。';return;}
    if (mode === 'flow' || preset) vertices = [];
    if (vertices.length >= 64) {el('status').textContent='剖面最多可選 64 個轉折點。';return;}
    if (vertices.at(-1) !== i) vertices.push(i);
    preset = false; cursor = i; inspecting = 0; el('status').textContent=''; recalculate();
  }
  function setMode(nextMode) {
    if (!grid || mode === nextMode) return;
    mode = nextMode; preset = false; vertices = []; inspecting = 0;
    el('status').textContent = ''; recalculate();
  }
  function recalculate() {
    if (!grid) return;
    stop = ''; path = vertices;
    if (mode === 'flow' && vertices.length) {
      const traced = core.route(grid, vertices[0]);
      path = traced.indices; stop = traced.stop;
    }
    samples = path.length ? core.profile(grid, path) : [];
    inspecting = Math.min(inspecting, Math.max(0,samples.length-1));
    el('line').setAttribute('aria-pressed',String(mode === 'line'));
    el('flow').setAttribute('aria-pressed',String(mode === 'flow'));
    el('help').textContent = mode === 'line' ? '點選起點、終點或轉折點。方向鍵移動游標，Enter 選點。' : '點選有高程的格點，沿最陡下降方向追蹤至停止處。';
    el('selection').textContent = preset ? '預設剖面 · 點選地圖可重畫' : mode === 'line' ? '自訂折線 · 已選 '+vertices.length+' 點' : 'D8 地表流線 · '+path.length+' 個網格';
    el('chart-title').textContent = mode === 'line' ? '地形縱剖面' : '沿流線高程';
    el('undo').disabled = el('clear').disabled = !vertices.length;
    el('csv').disabled = samples.length < 2;
    const a = samples[0], b = samples.at(-1);
    const length = b?.distance;
    const hasGap = samples.some(s => s.elevation === null);
    const dz = a && b && !hasGap ? b.elevation - a.elevation : null;
    el('length').textContent = length > 0 ? nf(length)+' m' : '—';
    el('delta').textContent = length > 0 && dz !== null ? nf(dz)+' m' : '—';
    el('slope').textContent = length > 0 && dz !== null ? nf(100*dz/length)+' %' : '—';
    el('note-title').textContent = mode === 'flow' ? '流向與停止原因' : '剖面判讀';
    el('note').textContent = mode === 'line'
      ? (hasGap ? '剖面穿過缺值，缺口保留，整線平均縱坡暫缺。' : '平均縱坡是終點與起點的高程差除以水平長度。')+' 可用於選定踏勘斷面；軌面、涵管及截水溝的位置需要現地核對。'
      : (path.length ? (stops[stop] || stop)+'。起點格的上游貢獻面積為 '+nf(network.area[path[0]]/10000,2)+' 公頃'+(network.partial[path[0]] ? '（受邊界或缺值影響，僅為下限）' : '')+'。' : '請先在坡面選一個起點。')+' D8 只使用較低的相鄰網格；圖中流線供踏勘比對。';
    el('readout').hidden = !samples.length;
    el('sample').max = Math.max(0,samples.length-1);
    el('sample').value = inspecting;
    drawChart(); updateMarker();
  }
  function updateMarker() {
    if (!grid) return;
    const overlay = el('overlay'), radius = Math.max(.23,Math.max(grid.rows,grid.cols)*.009);
    overlay.replaceChildren();
    if (path.length) {
      const points = path.map(i => point(i).join(',')).join(' ');
      for (const [stroke,w] of [['#243533',4.4],[mode === 'flow' ? '#a6f4ff' : '#ffd16c',2.7]])
        overlay.append(svg('polyline',{points,fill:'none',stroke,'stroke-width':w,'vector-effect':'non-scaling-stroke','stroke-linejoin':'round'}));
      const markers = mode === 'flow' ? [path[0],path.at(-1)] : vertices;
      markers.forEach((i,n) => {
        const [cx,cy] = point(i);
        overlay.append(svg('circle',{cx,cy,r:radius,fill:n === 0 ? '#fff9db':'#ffc362',stroke:'#364c45','stroke-width':1.2,'vector-effect':'non-scaling-stroke'}));
      });
    }
    const s = samples[inspecting];
    if (s) {
      const cx = (s.x-grid.x0)/grid.cellSize+.5, cy = (grid.y0-s.y)/grid.cellSize+.5;
      overlay.append(svg('circle',{cx,cy,r:1.6*radius,fill:'none',stroke:'white','stroke-width':2,'vector-effect':'non-scaling-stroke'}));
      el('value').textContent = '距起點 '+nf(s.distance)+' m　｜　高程 '+(s.elevation === null ? '缺值' : nf(s.elevation)+' m');
    }
    if (document.activeElement === overlay) {
      const [cx,cy] = point(cursor);
      overlay.append(svg('rect',{x:cx-radius*1.7,y:cy-radius*1.7,width:3.4*radius,height:3.4*radius,fill:'none',stroke:'#fff','stroke-width':2,'vector-effect':'non-scaling-stroke'}));
    }
    overlay.setAttribute('aria-label','地形網格，第 '+(row(cursor)+1)+' 列、第 '+(col(cursor)+1)+' 欄，高程 '+(valid(cursor)?nf(grid.values[cursor])+' 公尺':'缺值')+'。方向鍵移動，Enter 選點。');
  }
  function drawChart() {
    const host = el('chart'); host.replaceChildren();
    if (samples.length < 2) {
      const p = document.createElement('p'); p.textContent = mode === 'line' ? '選取至少兩點即可顯示剖面。' : stop ? '流線在起點停止，原因見下方。' : '選取起點即可查看沿程高程。'; host.append(p); return;
    }
    const values = samples.filter(s=>s.elevation !== null).map(s=>s.elevation);
    if (!values.length) return;
    let lo = Infinity, hi = -Infinity;
    for (const v of values) {lo = Math.min(lo,v);hi = Math.max(hi,v);}
    const pad = Math.max((hi-lo)*.12,.5);lo-=pad;hi+=pad;
    const length = samples.at(-1).distance;
    const x = d => 56 + 375*d/(length || 1), y = h => 134 - 112*(h-lo)/(hi-lo);
    const chart = svg('svg',{viewBox:'0 0 455 173',role:'img','aria-label':'水平距離與高程剖面，距離及高程的單位為公尺'});
    for (let n=0;n<=3;n++) {
      const level = lo + n*(hi-lo)/3, yy=y(level);
      chart.append(svg('line',{x1:56,y1:yy,x2:431,y2:yy,stroke:'#dce8e4'}),svg('text',{x:50,y:yy+4,'text-anchor':'end','font-size':11,fill:'#546f70'},nf(level,hi-lo<4?1:0)));
    }
    chart.append(svg('text',{x:12,y:12,'font-size':11,fill:'#546f70'},'高程 m'));
    for(let n=0;n<=2;n++) chart.append(svg('text',{x:x(length*n/2),y:150,'text-anchor':'middle','font-size':11,fill:'#546f70'},nf(length*n/2,0)));
    chart.append(svg('text',{x:242,y:169,'text-anchor':'middle','font-size':11,fill:'#546f70'},'水平距離 m'));
    let segment = [], previous;
    const flush = () => {
      if (segment.length) chart.append(svg('polyline',{points:segment.join(' '),stroke:'#28786f','stroke-width':2.6,fill:'none','stroke-linejoin':'round'}));
      if (segment.length===1) chart.append(svg('circle',{cx:x(previous.distance),cy:y(previous.elevation),r:2,fill:'#28786f'}));
      segment=[];
    };
    for (const s of samples) {
      if (s.elevation===null) flush();
      else {segment.push(x(s.distance).toFixed(2)+','+y(s.elevation).toFixed(2));previous=s;}
    }
    flush();
    const s=samples[inspecting];
    chart.append(svg('line',{x1:x(s.distance),y1:20,x2:x(s.distance),y2:134,stroke:'#c4832c','stroke-dasharray':'3 3'}));
    if(s.elevation!==null)chart.append(svg('circle',{cx:x(s.distance),cy:y(s.elevation),r:3.5,fill:'#bc761e'}));
    host.append(chart);
  }
  function showEvidence() {
    const dl = document.createElement('dl');
    function item(name, value) {
      const dt=document.createElement('dt'),dd=document.createElement('dd');
      dt.textContent=name;
      if (value instanceof Node) dd.append(value); else dd.textContent=value || '未提供';
      dl.append(dt,dd);
    }
    function link(url,text) {
      const a=document.createElement('a'); a.href=url; a.textContent=text; a.target='_blank'; a.rel='noopener noreferrer'; return a;
    }
    item('資料來源',grid.sourceUrl ? link(grid.sourceUrl,grid.source) : grid.source);
    item('版本',grid.edition);
    item('平面坐標',grid.crs); item('高程基準',grid.verticalDatum);
    item('網格間距',nf(grid.cellSize,grid.cellSize%1?2:0)+' m'); item('圖幅大小',grid.cols+' × '+grid.rows+' 格');
    if (grid.center) item('圖幅中心',nf(grid.center.lat,5)+'° N，'+nf(grid.center.lon,5)+'° E');
    const ref = grid.requestedAnchor || grid.referencePoint;
    if (ref) item('區域參考點',link('https://www.openstreetmap.org/?mlat='+ref.lat+'&mlon='+ref.lon+'#map=14/'+ref.lat+'/'+ref.lon,nf(ref.lat,4)+'° N，'+nf(ref.lon,4)+'° E'));
    const offset = grid.centerOffsetM ?? ref?.centerOffsetM;
    if (Number.isFinite(offset)) item('中心距參考點',nf(offset)+' m');
    item('授權',grid.licenseUrl ? link(grid.licenseUrl,grid.license) : grid.license);
    if (grid.attribution || grid.credits) item('資料標示',grid.attribution || grid.credits);
    if (grid.derivedFrom) item('轉製來源',link(grid.derivedFrom,'OsmHackTW 轉製版本'));
    if (grid.waterMask) item('水域遮罩',link('https://esa-worldcover.org/en/data-access',grid.waterMask.credit));
    item('適用位置',regions[grid.region] ? '區域參考圖幅，逐坡資產位置待核定' : '使用者選定範圍');
    const note=document.createElement('p');
    note.textContent = (grid.caution || grid.processing || (grid.source?.includes('GEM-15') ? 'GEM-15 以不同時期的光學立體影像估計裸地高程。林冠遮蔽、水面遮罩與區域性高程偏差會影響判讀。' : '本機檔案由使用者提供，座標系、垂直基準與資料來源須另行核對。'))+
      ' 流線與貢獻面積按原始網格的八鄰域最陡下降方向計算，保留窪地；匯流門檻只控制圖面顯示。未納入管涵、逕流量與短延時降雨。正式資產定位、養護分級及預警應另依工程證據。';
    el('evidence').replaceChildren(dl,note);
    const match = comparisons[grid.region];
    if (match) {
      const check = document.createElement('p'), bold = document.createElement('strong');
      bold.textContent = '兩來源地形比對　';
      const summary = match.pairedCells ? '將本土 40 m 格點中心投影至 GEM-15，配對最近格點，保留兩者皆有高程的位置。'+match.pairedCells+' 對，地勢相關 r = '+nf(match.pearsonR,3)+'，兩者高程差扣除中位數後的絕對偏差中位數為 '+nf(match.centeredMadM,2)+' m。此值描述兩份地形在重疊範圍內的差異；高程精度仍須地面控制點驗證。' : '此區兩個圖幅共有 0 對有效格點，無法估計地勢相關或差值。';
      check.append(bold,document.createTextNode(summary));el('evidence').append(check);
    }
  }
  function csvField(v) {
    if (v == null) return '';
    const text = typeof v === 'string' && /^[=+@\t\r-]/.test(v) ? "'" + v : String(v);
    return '"' + text.replace(/"/g,'""') + '"';
  }
  function exportCsv() {
    if (!grid || samples.length<2) return;
    const header=['grid_id','source','source_url','derivative_url','attribution','water_mask_credit','license','edition','horizontal_crs','vertical_datum','cell_size_m','selection','route_stop','distance_m','easting_m','northing_m','elevation_m','valid'];
    const rows=samples.map(s=>[grid.id,grid.source,grid.sourceUrl,grid.derivedFrom,grid.attribution || grid.credits,grid.waterMask?.credit,grid.license,grid.edition,grid.crs,grid.verticalDatum,grid.cellSize,preset?'preset_profile':mode==='flow'?'d8_downhill':'user_profile',stop,s.distance,s.x,s.y,s.elevation,s.elevation!==null]);
    const text=[header,...rows].map(r=>r.map(csvField).join(',')).join('\r\n');
    download('RailEye_'+grid.id+'_'+mode+'.csv','\ufeff'+text,'text/csv');
  }
  function locate(event) {
    const rect = el('overlay').getBoundingClientRect();
    const c=Math.floor((event.clientX-rect.left)/rect.width*grid.cols);
    const r=Math.floor((event.clientY-rect.top)/rect.height*grid.rows);
    if (c>=0&&c<grid.cols&&r>=0&&r<grid.rows) addPoint(r*grid.cols+c);
  }
  function key(event) {
    if (!grid) return;
    const moves={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
    if (moves[event.key]) {
      event.preventDefault(); const [dx,dy]=moves[event.key];
      cursor=Math.max(0,Math.min(grid.rows-1,row(cursor)+dy))*grid.cols+Math.max(0,Math.min(grid.cols-1,col(cursor)+dx));
      updateMarker();
    } else if (['Enter',' '].includes(event.key)) {event.preventDefault();addPoint(cursor);}
  }
  async function importGrid() {
    const f=el('file').files[0]; if (!f || !el('metric').checked) return;
    const selection=++token;
    try {
      if (f.size>16*1024*1024) throw Error('檔案超過 16 MiB。');
      const g=core.parseAscii(await f.text());
      if (selection!==token) return;
      if (Math.max(g.cols,g.rows)>8192) throw Error('單邊超過 8,192 格，請先裁切研究區域。');
      if (!g.values.some(Number.isFinite)) throw Error('網格沒有有效高程。');
      localGrid={...g,id:'local',region:'local',name:f.name,crs:'使用者確認為公尺制投影',verticalDatum:'未提供',source:'使用者本機 ASCII Grid',edition:'使用者匯入',license:'依原檔授權'};
      regionOptions('local');el('import').open=false;await selectSource();
    } catch (err) {
      if (selection === token) el('status').textContent='匯入失敗，請檢查 ASCII Grid 表頭、列數與數值。 '+err.message;
    } finally { el('file').value=''; }
  }
  function openRelated(view) {
    if (!grid || !regions[grid.region]) return;
    const select=document.getElementById(view+'-region');
    select.value=grid.region;
    select.dispatchEvent(new Event('change'));
    window.changeView(view);
  }
  document.addEventListener('DOMContentLoaded',() => {
    el('region').onchange=()=>{requestedRegion=el('region').value;selectSource();}; el('source').onchange=loadGrid;
    el('line').onclick=()=>setMode('line');el('flow').onclick=()=>setMode('flow');
    el('overlay').onclick=e=>grid&&locate(e);el('overlay').onkeydown=key;
    el('overlay').onfocus=updateMarker;el('overlay').onblur=updateMarker;
    el('threshold').onchange=paint;
    el('undo').onclick=()=>{preset=false;vertices.pop();inspecting=0;recalculate();};
    el('clear').onclick=()=>{preset=false;vertices=[];inspecting=0;recalculate();};
    el('sample').oninput=()=>{inspecting=Number(el('sample').value);drawChart();updateMarker();};
    el('csv').onclick=exportCsv;el('metric').onchange=()=>{el('file').disabled=!el('metric').checked;};el('file').onchange=importGrid;
    el('live').onclick=()=>openRelated('live');el('hydro').onclick=()=>openRelated('hydro');
    for (const view of ['live','hydro']) {
      const regionSelect=document.getElementById(view+'-region');
      const link=document.createElement('button'); link.type='button'; link.className='button secondary'; link.textContent='同區地形剖面';
      (regionSelect.closest('label') || regionSelect).insertAdjacentElement('afterend',link);
      link.onclick=()=>{requestedRegion=regionSelect.value;window.changeView('terrain');
        if (entries.length) {el('region').value=requestedRegion;selectSource();}};
    }
    const oldExport=document.getElementById('export').onclick;
    document.getElementById('export').onclick=()=>document.getElementById('view-terrain').classList.contains('hidden') ? oldExport() : exportCsv();
    document.querySelector('.rail-bottom').innerHTML='v0.6<br>研究版';
    document.addEventListener('rail-terrain-open',()=>{loadCatalog();requestAnimationFrame(scaleBar);});
    if (!document.getElementById('view-terrain').classList.contains('hidden')) loadCatalog();
    if (window.ResizeObserver) new ResizeObserver(scaleBar).observe(el('frame'));
  });
})();
