<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>
<title>Smart Campus Digital Twin</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: survey-sheet dashboard. A live campus map on the left, a tabbed workbench of the DSA modules on the right. */
:root{
  --bg:#edf1f2; --surface:#f8fafa; --surface2:#e3eaeb; --ink:#13262b; --muted:#566b70;
  --line:#c9d5d7; --edge:#98adb1; --accent:#0b6b73; --accent-ink:#ffffff;
  --route:#d4501a; --ok:#25804a; --warn:#a96a0b; --crit:#b8332a;
  --f-display:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;
  --f-body:'Instrument Sans','Segoe UI',system-ui,sans-serif;
  --f-mono:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0e191c; --surface:#152327; --surface2:#1d3036; --ink:#e2edee; --muted:#8fa6ab;
  --line:#2c4349; --edge:#43616a; --accent:#52c3cc; --accent-ink:#06282b;
  --route:#ff8f57; --ok:#58c27f; --warn:#e0a53f; --crit:#ff7b70; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0e191c; --surface:#152327; --surface2:#1d3036; --ink:#e2edee; --muted:#8fa6ab;
  --line:#2c4349; --edge:#43616a; --accent:#52c3cc; --accent-ink:#06282b;
  --route:#ff8f57; --ok:#58c27f; --warn:#e0a53f; --crit:#ff7b70; color-scheme:dark}

*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:15px;line-height:1.5;
  padding-block:20px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.wrap{max-width:1240px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
h1,h2,h3{font-family:var(--f-display);margin:0;text-wrap:balance;line-height:1.15}
h1{font-size:clamp(1.7rem,4vw,2.5rem);font-weight:700;letter-spacing:-.01em}
h2{font-size:1.15rem;font-weight:700}
h3{font-size:.95rem;font-weight:700;margin-top:6px}
p{margin:0}
.muted{color:var(--muted)}
.mono,td.num,.stat b{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.eyebrow{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600}

header{display:flex;flex-wrap:wrap;gap:16px 32px;align-items:flex-end;justify-content:space-between}
.title{display:flex;flex-direction:column;gap:6px;min-width:0;max-width:62ch}
.stats{display:flex;flex-wrap:wrap;gap:8px}
.stat{background:var(--surface);border:1px solid var(--line);padding:8px 14px;min-width:104px;display:flex;flex-direction:column;gap:2px}
.stat b{font-size:1.2rem;font-weight:500}
.stat span{font-size:.72rem;color:var(--muted);letter-spacing:.06em;text-transform:uppercase}

.layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:18px;align-items:start}
@media (max-width:980px){.layout{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--surface);border:1px solid var(--line);min-width:0}
.mapcard{padding:14px;display:flex;flex-direction:column;gap:10px;position:sticky;top:12px}
@media (max-width:980px){.mapcard{position:static}}
.mapcard header{align-items:center}
svg#map{width:100%;height:auto;display:block;background:var(--bg);border:1px solid var(--line);touch-action:manipulation;cursor:crosshair}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.78rem;color:var(--muted)}
.legend i{display:inline-block;width:18px;height:0;border-top:3px solid;vertical-align:middle;margin-right:6px}
.hint{font-size:.82rem;color:var(--muted)}
#map-note{font-family:var(--f-mono);font-size:.8rem;min-height:1.4em}

/* map drawing */
.edge{stroke:var(--edge);stroke-width:.7;stroke-linecap:round}
.edge.blocked{stroke:var(--crit);stroke-dasharray:1.6 1.2}
.mst{stroke:var(--accent);stroke-width:1.5;stroke-linecap:round;opacity:.85}
.route{stroke:var(--route);stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:0;animation:draw .7s ease-out}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.tag rect{fill:var(--surface);stroke:var(--edge);stroke-width:.25}
.tag text{font-family:var(--f-mono);font-size:1.9px;fill:var(--muted);text-anchor:middle;dominant-baseline:central}
.tag.blocked rect{stroke:var(--crit);fill:var(--surface)}
.tag.blocked text{fill:var(--crit);font-size:2.4px}
.tag{cursor:pointer}
.tag:hover rect,.tag:focus rect{stroke:var(--accent)}
.node circle.dot{fill:var(--surface);stroke:var(--ink);stroke-width:.5}
.node text.code{font-family:var(--f-mono);font-size:1.7px;fill:var(--ink);text-anchor:middle;dominant-baseline:central;font-weight:500}
.node text.nm{font-family:var(--f-body);font-size:2.3px;fill:var(--ink);text-anchor:middle;font-weight:600}
.node{cursor:pointer}
.node:hover circle.dot,.node:focus circle.dot{stroke:var(--accent);stroke-width:.9}
.node.is-start circle.dot{fill:var(--accent)}
.node.is-start text.code{fill:var(--accent-ink)}
.node.is-goal circle.dot{fill:var(--route);stroke:var(--route)}
.node.is-goal text.code{fill:#fff}
.node circle.ring{fill:none;stroke:var(--route);stroke-width:.4;stroke-dasharray:.8 .6}
.kd line{stroke:var(--ok);stroke-width:.5;stroke-dasharray:1 .8}
.kd circle{fill:var(--ok)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
svg :focus-visible{outline:none}

/* workbench */
.bench{display:flex;flex-direction:column;min-width:0}
.tabs{display:flex;overflow-x:auto;border-bottom:1px solid var(--line);scrollbar-width:thin}
.tabs button{flex:0 0 auto;background:none;border:0;border-bottom:3px solid transparent;color:var(--muted);font:600 .85rem var(--f-body);padding:12px 14px 9px;cursor:pointer;display:flex;flex-direction:column;align-items:flex-start;gap:1px}
.tabs button small{font:500 .66rem var(--f-mono);letter-spacing:.04em;opacity:.85}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.tabs button:hover{color:var(--ink)}
.pane{padding:16px;display:flex;flex-direction:column;gap:12px;min-width:0}
.pane[hidden]{display:none}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end}
label{display:flex;flex-direction:column;gap:3px;font-size:.78rem;color:var(--muted);font-weight:600;min-width:0}
label.chk{flex-direction:row;align-items:center;gap:8px;color:var(--ink);font-weight:500;font-size:.88rem}
select,input[type=number],input[type=text]{font:500 .9rem var(--f-body);color:var(--ink);background:var(--bg);border:1px solid var(--line);padding:7px 9px;min-width:0;max-width:100%}
input[type=number]{width:92px}
input[type=text]{width:100%}
button.btn{font:600 .85rem var(--f-body);background:var(--accent);color:var(--accent-ink);border:1px solid var(--accent);padding:7px 12px;cursor:pointer}
button.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}
button.btn.ghost:hover{border-color:var(--accent)}
button.btn.danger{background:transparent;color:var(--crit);border-color:var(--crit)}
button.btn.sm{padding:3px 9px;font-size:.78rem}
.seg{display:inline-flex;border:1px solid var(--line)}
.seg button{font:600 .82rem var(--f-body);padding:6px 12px;background:transparent;border:0;color:var(--muted);cursor:pointer}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.note{font-size:.8rem;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}
.note code,.mono-inline{font-family:var(--f-mono);font-size:.76rem}
.result{background:var(--bg);border:1px solid var(--line);padding:10px 12px;display:flex;flex-direction:column;gap:4px}
.result .big{font-family:var(--f-display);font-size:1.5rem;font-weight:700}
.result .path{font-size:.88rem}
.pill{display:inline-block;font:600 .68rem var(--f-mono);padding:1px 7px;border:1px solid currentColor;letter-spacing:.04em}
.pill.ok{color:var(--ok)}.pill.warn{color:var(--warn)}.pill.crit{color:var(--crit)}.pill.mut{color:var(--muted)}
.tablewrap{overflow-x:auto;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.84rem}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--bg)}
tr:last-child td{border-bottom:0}
td.num{text-align:right}
tr.sel td{background:var(--surface2)}
tr.dim td{color:var(--muted)}
ul.plain{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
ul.plain li{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line);font-size:.86rem}
ul.plain li:last-child{border-bottom:0}
.bars{display:flex;flex-direction:column;gap:8px}
.bar{display:grid;grid-template-columns:70px minmax(0,1fr) auto;gap:10px;align-items:center;font-size:.86rem}
.bar .track{height:12px;background:var(--bg);border:1px solid var(--line)}
.bar .fill{height:100%;background:var(--accent)}
.fw{display:flex;gap:4px;flex-wrap:wrap}
.fw span{font:500 .78rem var(--f-mono);background:var(--bg);border:1px solid var(--line);padding:3px 8px}
.fw span em{font-style:normal;color:var(--muted);margin-right:6px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:var(--bg);border:1px solid var(--line);padding:3px 9px;font-size:.84rem}
mark{background:var(--route);color:#fff;padding:0 1px}
.alert{display:flex;gap:10px;align-items:baseline;padding:6px 0;border-bottom:1px solid var(--line);font-size:.88rem}
.alert:last-child{border-bottom:0}
.empty{color:var(--muted);font-size:.88rem;padding:6px 0}
.ref{margin-top:4px}
.ref .tablewrap{margin-top:10px}
footer{font-size:.8rem;color:var(--muted)}
@media (prefers-reduced-motion:reduce){.route{animation:none}}
</style>

<div class="wrap">
  <header>
    <div class="title">
      <span class="eyebrow">Campus services</span>
      <h1>Smart Campus Digital Twin</h1>
      <p class="muted">Find a free room, plan the shortest walk between buildings, and keep an eye on energy use and alerts across the campus.</p>
    </div>
    <div class="stats" id="stats"></div>
  </header>

  <div class="layout">
    <section class="card mapcard" aria-label="Campus map">
      <header>
        <h2>Campus map</h2>
        <div class="legend">
          <span><i style="border-color:var(--route)"></i>Route</span>
          <span><i style="border-color:var(--accent)"></i>Core network</span>
          <span><i style="border-color:var(--crit);border-top-style:dashed"></i>Blocked</span>
        </div>
      </header>
      <svg id="map" viewBox="-9 -8 106 60" role="img" aria-label="Weighted graph of campus buildings and walkways"></svg>
      <p class="hint">Click a building to set the start, then the destination. Click a distance tag to block or reopen a walkway. Click empty ground to find the nearest building.</p>
      <p id="map-note" aria-live="polite"></p>
    </section>

    <section class="card bench" aria-label="Campus tools">
      <div class="tabs" role="tablist" id="tabs"></div>

      <!-- Route -->
      <div class="pane" id="p-route" role="tabpanel">
        <div class="row">
          <label>From<select id="sel-start"></select></label>
          <label>To<select id="sel-goal"></select></label>
          <button class="btn ghost" id="swap" type="button">Swap</button>
        </div>
        <div class="result" id="route-result"></div>
        <h3>Walkways</h3>
        <ul class="plain" id="edge-list"></ul>
        </div>

      <!-- Network -->
      <div class="pane" id="p-net" role="tabpanel" hidden>
        <h3>Can you get there?</h3>
        <div class="row">
          <label>Location A<select id="sel-a"></select></label>
          <label>Location B<select id="sel-b"></select></label>
        </div>
        <div class="result" id="dsu-result"></div>
        <div class="chips" id="components"></div>
        <h3>Core walkway network</h3>
        <label class="chk"><input type="checkbox" id="show-mst"> Show on the map</label>
        <div class="tablewrap"><table id="kruskal"></table></div>
        <div class="result" id="mst-result"></div>
        <h3>Nearest building</h3>
        <div class="result" id="kd-result"></div>
        <p class="note">Block a walkway on the Route tab and this tab updates.</p>
      </div>

      <!-- Rooms -->
      <div class="pane" id="p-rooms" role="tabpanel" hidden>
        <div class="row">
          <label>Walking from<select id="r-origin"></select></label>
          <label>Type<select id="r-type"><option value="">Any</option><option value="classroom">Classroom</option><option value="laboratory">Laboratory</option></select></label>
          <label>Min capacity<input type="number" id="r-cap" min="0" value="0"></label>
        </div>
        <div class="row">
          <label class="chk"><input type="checkbox" id="r-proj"> Projector</label>
          <label class="chk"><input type="checkbox" id="r-comp"> Computers</label>
          <label class="chk"><input type="checkbox" id="r-avail" checked> Available only</label>
        </div>
        <div class="tablewrap"><table id="rooms"></table></div>
        <p class="note">Rooms are ranked by real walking distance, so a blocked walkway can change the order. A room counts as available when it is switched on and has a free seat.</p>
      </div>

      <!-- Energy -->
      <div class="pane" id="p-energy" role="tabpanel" hidden>
        <div class="result"><span class="eyebrow">Total daily energy</span><span class="big mono" id="e-total"></span></div>
        <div class="bars" id="e-bars"></div>
        <h3>Range total</h3>
        <div class="row">
          <label>From building<select id="e-from"></select></label>
          <label>To building<select id="e-to"></select></label>
        </div>
        <div class="result" id="e-range"></div>
        </div>

      <!-- Alerts -->
      <div class="pane" id="p-alerts" role="tabpanel" hidden>
        <h3>Alerts</h3>
        <div id="alerts"></div>
        <div class="row"><button class="btn" id="pop" type="button">Process most urgent</button><span class="muted" id="pop-out"></span></div>
        <h3>Room sensors</h3>
        <div class="tablewrap"><table id="sensors"></table></div>
        <p class="note">Readings are simulated for this demo. Full rooms and temperatures of 28 °C or more raise a priority 1 alert, and the most urgent alert is always handled first.</p>
      </div>

      <!-- Search -->
      <div class="pane" id="p-search" role="tabpanel" hidden>
        <label>Search building names, room names and room codes<input type="text" id="s-q" value="lab" autocomplete="off"></label>
        <div class="result" id="s-result"></div>
        <div class="chips" id="s-entries"></div>
        <p class="note">Matches are highlighted in the building, room and code names below.</p>
      </div>
    </section>
  </div>

  <footer>Sample data and simulated sensors only. Coordinates are map units; walkway weights are metres.</footer>
</div>

<script>
(function(){
"use strict";
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=(n,d=1)=>Number(n).toFixed(d);

/* ---------- campus engine ---------- */
class MinHeap{
  constructor(cmp){this.a=[];this.cmp=cmp}
  get size(){return this.a.length}
  push(x){const a=this.a;a.push(x);let i=a.length-1;
    while(i>0){const p=(i-1)>>1;if(this.cmp(a[i],a[p])<0){[a[i],a[p]]=[a[p],a[i]];i=p}else break}}
  pop(){const a=this.a;if(!a.length)return undefined;const top=a[0],last=a.pop();
    if(a.length){a[0]=last;let i=0;
      for(;;){const l=2*i+1,r=l+1;let m=i;
        if(l<a.length&&this.cmp(a[l],a[m])<0)m=l;
        if(r<a.length&&this.cmp(a[r],a[m])<0)m=r;
        if(m===i)break;[a[i],a[m]]=[a[m],a[i]];i=m}}
    return top}
}

class Graph{
  constructor(){this.loc=new Map();this.adj=new Map();this.blocked=new Set()}
  addLoc(l){this.loc.set(l.id,l);if(!this.adj.has(l.id))this.adj.set(l.id,[])}
  addPath(a,b,d){this.adj.get(a).push([b,d]);this.adj.get(b).push([a,d])}
  key(a,b){return a<b?a+"|"+b:b+"|"+a}
  isBlocked(a,b){return this.blocked.has(this.key(a,b))}
  setBlocked(a,b,v){v?this.blocked.add(this.key(a,b)):this.blocked.delete(this.key(a,b))}
  *nb(id){for(const [n,d] of this.adj.get(id))if(!this.isBlocked(id,n))yield [n,d]}
  sld(a,b){const p=this.loc.get(a),q=this.loc.get(b);return Math.hypot(p.x-q.x,p.y-q.y)}
  scale(){let s=1;for(const [u,list] of this.adj)for(const [v,w] of list){const g=this.sld(u,v);if(g>0)s=Math.min(s,w/g)}return s}
  build(came,g){const p=[g];while(came[p[p.length-1]]!==undefined)p.push(came[p[p.length-1]]);return p.reverse()}
  aStar(s,g){
    if(s===g)return{path:[s],dist:0,expanded:[s]};
    const sc=this.scale(),h=n=>sc*this.sld(n,g);
    const heap=new MinHeap((x,y)=>x[0]-y[0]||x[1]-y[1]);
    heap.push([h(s),0,s]);
    const came={},best={[s]:0},closed=new Set(),exp=[];
    while(heap.size){
      const [,cg,cur]=heap.pop();
      if(cg>(best[cur]??Infinity)||closed.has(cur))continue;
      exp.push(cur);
      if(cur===g)return{path:this.build(came,g),dist:best[g],expanded:exp};
      closed.add(cur);
      for(const [n,w] of this.nb(cur)){
        const c=best[cur]+w;
        if(c<(best[n]??Infinity)){best[n]=c;came[n]=cur;heap.push([c+h(n),c,n]);closed.delete(n)}
      }
    }
    return{path:null,dist:Infinity,expanded:exp};
  }
  dijkstra(s,g){
    const dist={},came={},exp=[],done=new Set();
    for(const k of this.loc.keys())dist[k]=Infinity;
    dist[s]=0;
    const heap=new MinHeap((x,y)=>x[0]-y[0]);heap.push([0,s]);
    while(heap.size){
      const [d,u]=heap.pop();
      if(d!==dist[u]||done.has(u))continue;
      done.add(u);exp.push(u);
      if(u===g)break;
      for(const [n,w] of this.nb(u)){
        if(d+w<dist[n]){dist[n]=d+w;came[n]=u;heap.push([d+w,n])}
      }
    }
    if(!isFinite(dist[g]))return{path:null,dist:Infinity,expanded:exp};
    return{path:this.build(came,g),dist:dist[g],expanded:exp};
  }
  bfs(s,g){
    const q=[s],seen=new Set([s]),came={},exp=[];let head=0;
    while(head<q.length){
      const u=q[head++];exp.push(u);
      if(u===g)break;
      for(const [n] of this.nb(u))if(!seen.has(n)){seen.add(n);came[n]=u;q.push(n)}
    }
    if(!seen.has(g))return{path:null,dist:Infinity,expanded:exp};
    const path=this.build(came,g);
    let dist=0;for(let i=1;i<path.length;i++)dist+=this.weight(path[i-1],path[i]);
    return{path,dist,expanded:exp};
  }
  weight(a,b){for(const [n,d] of this.adj.get(a))if(n===b)return d;return null}
  mst(){
    const edges=[];
    for(const [u] of this.adj)for(const [v,w] of this.nb(u))if(u<v)edges.push([w,u,v]);
    edges.sort((x,y)=>x[0]-y[0]||(x[1]<y[1]?-1:x[1]>y[1]?1:0)||(x[2]<y[2]?-1:x[2]>y[2]?1:0));
    const dsu=new DSU([...this.loc.keys()]),kept=[],log=[];
    for(const [w,a,b] of edges){
      const ok=dsu.union(a,b);
      log.push({a,b,w,ok});
      if(ok)kept.push([a,b,w]);
    }
    return{kept,log};
  }
}

class DSU{
  constructor(items){this.p={};this.r={};for(const i of items){this.p[i]=i;this.r[i]=0}}
  find(x){let root=x;while(this.p[root]!==root)root=this.p[root];
    while(this.p[x]!==root){const n=this.p[x];this.p[x]=root;x=n}return root}
  union(a,b){let ra=this.find(a),rb=this.find(b);if(ra===rb)return false;
    if(this.r[ra]<this.r[rb])[ra,rb]=[rb,ra];
    this.p[rb]=ra;if(this.r[ra]===this.r[rb])this.r[ra]++;return true}
  connected(a,b){return this.find(a)===this.find(b)}
}

class KDTree{
  constructor(points){this.root=this.build(points.slice(),0)}
  build(pts,depth){
    if(!pts.length)return null;
    const axis=depth%2;pts.sort((a,b)=>a[axis]-b[axis]);
    const m=pts.length>>1;
    return{pt:pts[m],axis,left:this.build(pts.slice(0,m),depth+1),right:this.build(pts.slice(m+1),depth+1)};
  }
  nearest(x,y){
    let best=null,visited=0;
    const visit=n=>{
      if(!n)return;visited++;
      const [px,py,id]=n.pt,d2=(x-px)**2+(y-py)**2;
      if(!best||d2<best[0])best=[d2,id];
      const delta=n.axis===0?x-px:y-py;
      visit(delta<0?n.left:n.right);
      if(!best||delta*delta<best[0])visit(delta<0?n.right:n.left);
    };
    visit(this.root);
    return best?{id:best[1],dist:Math.sqrt(best[0]),visited}:null;
  }
}

class Fenwick{
  constructor(vals){this.n=vals.length;this.t=Array(this.n+1).fill(0);vals.forEach((v,i)=>this.add(i+1,v))}
  add(i,d){for(;i<=this.n;i+=i&-i)this.t[i]+=d}
  prefix(i){let s=0;for(;i>0;i-=i&-i)s+=this.t[i];return s}
  range(l,r){return this.prefix(r)-this.prefix(l-1)}
  set(i,v){this.add(i,v-this.range(i,i))}
}

class AlertQueue{
  constructor(){this.h=new MinHeap((a,b)=>a[0]-b[0]||a[1]-b[1]);this.c=0}
  add(p,m){this.h.push([p,++this.c,m])}
  pop(){const x=this.h.pop();return x?{p:x[0],m:x[2]}:null}
  view(){return this.h.a.slice().sort((a,b)=>a[0]-b[0]||a[1]-b[1]).map(x=>({p:x[0],m:x[2]}))}
}

function kmp(text,pat){
  if(!pat)return{matches:[],cmp:0,lps:[]};
  let cmp=0;const lps=Array(pat.length).fill(0);let len=0,i=1;
  while(i<pat.length){cmp++;
    if(pat[i]===pat[len]){len++;lps[i]=len;i++}else if(len){len=lps[len-1]}else{lps[i]=0;i++}}
  const out=[];let j=0;i=0;
  while(i<text.length){cmp++;
    if(text[i]===pat[j]){i++;j++;if(j===pat.length){out.push(i-j);j=lps[j-1]}}
    else if(j){j=lps[j-1]}else i++}
  return{matches:out,cmp,lps};
}
function rabinKarp(text,pat){
  const M=1000000007,B=256,m=pat.length;
  if(!m||m>text.length)return{matches:[],verifs:0,windows:0};
  let hp=1;for(let i=0;i<m-1;i++)hp=(hp*B)%M;
  let ph=0,wh=0;
  for(let i=0;i<m;i++){ph=(ph*B+pat.charCodeAt(i))%M;wh=(wh*B+text.charCodeAt(i))%M}
  const out=[];let verifs=0;
  for(let s=0;s<=text.length-m;s++){
    if(ph===wh){verifs++;if(text.substr(s,m)===pat)out.push(s)}
    if(s<text.length-m){
      wh=((wh-text.charCodeAt(s)*hp)%M+M)%M;
      wh=(wh*B+text.charCodeAt(s+m))%M;
    }
  }
  return{matches:out,verifs,windows:text.length-m+1};
}

/* ---------- sample campus ---------- */
const G=new Graph();
[["GATE","Main Gate","Main Gate",0,0],["LIB","Central Library","Library",20,10],
 ["CSE","Computer Science Block","CS Block",45,12],["LAB","Innovation Laboratory","Innovation Lab",55,35],
 ["SCI","Science Block","Science Block",25,42],["CAF","Cafeteria","Cafeteria",5,35],
 ["AUD","Auditorium","Auditorium",70,10],["HOST","Hostel","Hostel",85,38]
].forEach(([id,name,short,x,y])=>G.addLoc({id,name,short,x,y}));
const PATHS=[["GATE","LIB",23],["GATE","CAF",36],["LIB","CSE",26],["LIB","SCI",34],["CAF","SCI",25],
  ["SCI","LAB",34],["CSE","LAB",28],["CSE","AUD",26],["LAB","HOST",32],["AUD","HOST",39],["AUD","LAB",30]];
PATHS.forEach(([a,b,d])=>G.addPath(a,b,d));
const KD=new KDTree([...G.loc.values()].map(l=>[l.x,l.y,l.id]));

const ROOMS=[
 {id:"CSE101",name:"CSE Classroom 101",b:"CSE",type:"classroom",cap:60,on:true,occ:12,proj:true,comp:false,temp:23.5,kwh:12.4},
 {id:"CSE102",name:"CSE Classroom 102",b:"CSE",type:"classroom",cap:40,on:true,occ:5,proj:true,comp:false,temp:24.0,kwh:9.8},
 {id:"CSELAB1",name:"Programming Lab 1",b:"CSE",type:"laboratory",cap:35,on:true,occ:18,proj:true,comp:true,temp:22.8,kwh:21.2},
 {id:"INNO1",name:"Innovation Lab 1",b:"LAB",type:"laboratory",cap:28,on:true,occ:7,proj:true,comp:true,temp:23.2,kwh:18.5},
 {id:"SCI201",name:"Science Classroom 201",b:"SCI",type:"classroom",cap:50,on:true,occ:50,proj:false,comp:false,temp:26.5,kwh:14.3},
 {id:"SCI-LAB",name:"Science Lab",b:"SCI",type:"laboratory",cap:24,on:false,occ:0,proj:false,comp:true,temp:24.5,kwh:16.8},
 {id:"AUD1",name:"Seminar Room",b:"AUD",type:"classroom",cap:80,on:true,occ:10,proj:true,comp:true,temp:22.0,kwh:25.1}];
const ENERGY_ORDER=["CSE","LIB","LAB","SCI","AUD"];
const ENERGY={CSE:124.5,LIB:80.2,LAB:112.8,SCI:97.1,AUD:75.4};
const FW=new Fenwick(ENERGY_ORDER.map(b=>ENERGY[b]));
const ALERTS=new AlertQueue();
ALERTS.add(1,"Room SCI201 is at full capacity.");

const S={start:"GATE",goal:"HOST",algo:"astar",pick:"start",tab:"route",showMst:false,kd:null,lastPop:""};
const name=id=>G.loc.get(id).name;
const free=r=>Math.max(0,r.cap-r.occ);
const isAvail=r=>r.on&&free(r)>0;

/* ---------- map ---------- */
const svg=$("#map");
function renderMap(){
  const cur=S.res[S.algo];
  let h="";
  if(S.showMst){
    for(const [a,b] of S.mstRes.kept){const p=G.loc.get(a),q=G.loc.get(b);
      h+=`<line class="mst" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`}
  }
  for(const [a,b,d] of PATHS){
    const p=G.loc.get(a),q=G.loc.get(b),bl=G.isBlocked(a,b);
    h+=`<line class="edge${bl?" blocked":""}" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`;
  }
  if(cur.path&&cur.path.length>1){
    h+=`<polyline class="route" pathLength="1" points="${cur.path.map(id=>G.loc.get(id).x+","+G.loc.get(id).y).join(" ")}"/>`;
  }
  for(const [a,b,d] of PATHS){
    const p=G.loc.get(a),q=G.loc.get(b),bl=G.isBlocked(a,b),mx=(p.x+q.x)/2,my=(p.y+q.y)/2;
    const label=bl?"×":String(d),w=bl?3.6:label.length*1.25+2;
    h+=`<g class="tag${bl?" blocked":""}" data-edge="${a}|${b}" tabindex="0" role="button" aria-label="${bl?"Reopen":"Block"} walkway ${esc(name(a))} to ${esc(name(b))}, ${d} metres">
      <rect x="${mx-w/2}" y="${my-1.6}" width="${w}" height="3.2" rx=".4"/><text x="${mx}" y="${my+.1}">${label}</text></g>`;
  }
  const exp=new Set();
  for(const l of G.loc.values()){
    const cls=["node"];if(l.id===S.start)cls.push("is-start");if(l.id===S.goal)cls.push("is-goal");
    h+=`<g class="${cls.join(" ")}" data-node="${l.id}" tabindex="0" role="button" aria-label="${esc(l.name)}">
      ${exp.has(l.id)?`<circle class="ring" cx="${l.x}" cy="${l.y}" r="4.3"/>`:""}
      <circle class="dot" cx="${l.x}" cy="${l.y}" r="3"/>
      <text class="code" x="${l.x}" y="${l.y+.1}">${l.id.length>3?l.id.slice(0,4):l.id}</text>
      <text class="nm" x="${l.x}" y="${l.y+6.4}">${esc(l.short)}</text></g>`;
  }
  if(S.kd){
    const n=G.loc.get(S.kd.id);
    h+=`<g class="kd"><line x1="${S.kd.x}" y1="${S.kd.y}" x2="${n.x}" y2="${n.y}"/><circle cx="${S.kd.x}" cy="${S.kd.y}" r=".9"/></g>`;
  }
  svg.innerHTML=h;
}
function svgPoint(e){
  const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}
function onNode(id){
  if(S.pick==="start"){S.start=id;S.pick="goal"}else{S.goal=id;S.pick="start"}
  $("#sel-start").value=S.start;$("#sel-goal").value=S.goal;refresh();
}
function onEdge(key){
  const [a,b]=key.split("|"),now=!G.isBlocked(a,b);
  G.setBlocked(a,b,now);
  ALERTS.add(now?1:3,(now?"Pathway blocked: ":"Pathway reopened: ")+a+" <-> "+b);
  refresh();
}
svg.addEventListener("click",e=>{
  const n=e.target.closest("[data-node]"),ed=e.target.closest("[data-edge]");
  if(n)return onNode(n.dataset.node);
  if(ed)return onEdge(ed.dataset.edge);
  const p=svgPoint(e),r=KD.nearest(p.x,p.y);
  if(r){S.kd={x:p.x,y:p.y,id:r.id,dist:r.dist,visited:r.visited};refresh()}
});
svg.addEventListener("keydown",e=>{
  if(e.key!=="Enter"&&e.key!==" ")return;
  const n=e.target.closest("[data-node]"),ed=e.target.closest("[data-edge]");
  if(n){e.preventDefault();onNode(n.dataset.node)}else if(ed){e.preventDefault();onEdge(ed.dataset.edge)}
});

/* ---------- tabs ---------- */
const TABS=[["route","Route","Member 1"],["net","Network","Member 2"],["rooms","Rooms","Member 4"],
  ["energy","Energy","Member 3"],["alerts","Alerts","Member 3"],["search","Search","Member 4"]];
function buildTabs(){
  $("#tabs").innerHTML=TABS.map(([id,t,m])=>`<button type="button" role="tab" data-tab="${id}" aria-selected="${id===S.tab}">${t}</button>`).join("");
  $("#tabs").addEventListener("click",e=>{
    const b=e.target.closest("[data-tab]");if(!b)return;S.tab=b.dataset.tab;showTab();
  });
}
function showTab(){
  for(const [id] of TABS)$("#p-"+id).hidden=id!==S.tab;
  document.querySelectorAll("#tabs button").forEach(b=>b.setAttribute("aria-selected",b.dataset.tab===S.tab));
}

/* ---------- route tab ---------- */
function fillSelects(){
  const opts=[...G.loc.values()].map(l=>`<option value="${l.id}">${esc(l.name)} (${l.id})</option>`).join("");
  for(const id of ["#sel-start","#sel-goal","#sel-a","#sel-b","#r-origin"])$(id).innerHTML=opts;
  $("#sel-start").value=S.start;$("#sel-goal").value=S.goal;
  $("#sel-a").value="GATE";$("#sel-b").value="HOST";$("#r-origin").value="GATE";
}
const ALGO_NAME={astar:"A*",dijkstra:"Dijkstra",bfs:"BFS"};
function updateRoute(){
  const cur=S.res[S.algo];
  const hops=cur.path?cur.path.length-1:0;
  $("#route-result").innerHTML=cur.path
    ?`<span class="eyebrow">Shortest walk · ${hops} stop${hops===1?"":"s"}</span>
      <span class="big mono">${fmt(cur.dist)} m</span>
      <span class="path">${cur.path.map(id=>esc(name(id))).join(" → ")}</span>`
    :`<span class="eyebrow">Route</span><span class="big">No open route</span>
      <span class="path muted">Blocked walkways have cut these two buildings apart. Reopen one below.</span>`;
  $("#edge-list").innerHTML=PATHS.map(([a,b,d])=>{
    const bl=G.isBlocked(a,b);
    return `<li><span>${esc(G.loc.get(a).short)} — ${esc(G.loc.get(b).short)} <span class="mono muted">${d} m</span> ${bl?'<span class="pill crit">BLOCKED</span>':""}</span>
      <button type="button" class="btn sm ${bl?"ghost":"danger"}" data-edge="${a}|${b}">${bl?"Reopen":"Block"}</button></li>`}).join("");
}
$("#edge-list").addEventListener("click",e=>{const b=e.target.closest("[data-edge]");if(b)onEdge(b.dataset.edge)});
$("#sel-start").addEventListener("change",e=>{S.start=e.target.value;refresh()});
$("#sel-goal").addEventListener("change",e=>{S.goal=e.target.value;refresh()});
$("#swap").addEventListener("click",()=>{[S.start,S.goal]=[S.goal,S.start];$("#sel-start").value=S.start;$("#sel-goal").value=S.goal;refresh()});

/* ---------- network tab ---------- */
function components(){
  const dsu=new DSU([...G.loc.keys()]);
  for(const [u] of G.adj)for(const [v] of G.nb(u))if(u<v)dsu.union(u,v);
  return dsu;
}
function updateNet(){
  const dsu=components(),groups={};
  for(const id of G.loc.keys())(groups[dsu.find(id)]??=[]).push(id);
  const list=Object.values(groups);
  const a=$("#sel-a").value,b=$("#sel-b").value,ok=dsu.connected(a,b);
  $("#dsu-result").innerHTML=`<span class="eyebrow">${esc(name(a))} and ${esc(name(b))}</span>
    <span><span class="pill ${ok?"ok":"crit"}">${ok?"CONNECTED":"NOT CONNECTED"}</span> through open walkways</span>`;
  $("#components").innerHTML=list.length===1
    ?`<span class="chip">All ${G.loc.size} locations are connected</span>`
    :list.map((g,i)=>`<span class="chip"><b>Area ${i+1}</b> ${g.map(esc).join(", ")}</span>`).join("");
  const rows=S.mstRes.log.map((r,i)=>`<tr class="${r.ok?"":"dim"}"><td class="num">${i+1}</td>
    <td>${esc(G.loc.get(r.a).short)} — ${esc(G.loc.get(r.b).short)}</td><td class="num">${r.w} m</td>
    <td><span class="pill ${r.ok?"ok":"mut"}">${r.ok?"CORE":"NOT NEEDED"}</span></td></tr>`).join("");
  $("#kruskal").innerHTML=`<tr><th>#</th><th>Walkway</th><th>Length</th><th>Status</th></tr>${rows}`;
  const tot=S.mstRes.kept.reduce((s,e)=>s+e[2],0);
  $("#mst-result").innerHTML=`<span class="eyebrow">${S.mstRes.kept.length} walkways in the core network</span><span class="big mono">${fmt(tot)} m</span>
    ${list.length>1?'<span class="path"><span class="pill warn">SPLIT</span> Blocked walkways have separated the campus into areas.</span>':'<span class="path muted">The least walkway length that still links every building.</span>'}`;
  $("#kd-result").innerHTML=S.kd
    ?`<span class="eyebrow">Click at (${fmt(S.kd.x)}, ${fmt(S.kd.y)})</span><span class="big">${esc(name(S.kd.id))}</span>
      <span class="path mono">${fmt(S.kd.dist,2)} map units away in a straight line</span>`
    :`<span class="muted">Click empty ground on the map to find the nearest building.</span>`;
  $("#map-note").textContent=S.kd?`Nearest to (${fmt(S.kd.x)}, ${fmt(S.kd.y)}): ${name(S.kd.id)}, ${fmt(S.kd.dist,2)} units straight-line.`:"";
}
$("#sel-a").addEventListener("change",refresh);$("#sel-b").addEventListener("change",refresh);
$("#show-mst").addEventListener("change",e=>{S.showMst=e.target.checked;refresh()});

/* ---------- rooms tab ---------- */
function updateRooms(){
  const origin=$("#r-origin").value,type=$("#r-type").value,cap=Number($("#r-cap").value)||0;
  const proj=$("#r-proj").checked,comp=$("#r-comp").checked,av=$("#r-avail").checked;
  let list=ROOMS.filter(r=>(!type||r.type===type)&&r.cap>=cap&&(!proj||r.proj)&&(!comp||r.comp)&&(!av||isAvail(r)));
  list=list.map(r=>{const x=G.aStar(origin,r.b);return{r,path:x.path,dist:x.dist}})
    .sort((a,b)=>a.dist-b.dist);
  $("#rooms").innerHTML=list.length
    ?`<tr><th>Room</th><th>Type</th><th>Free</th><th>Gear</th><th>Walk</th></tr>`+list.map(({r,path,dist})=>`
      <tr class="${isAvail(r)?"":"dim"}"><td><b>${esc(r.id)}</b><br><span class="muted">${esc(r.name)} · ${esc(r.b)}</span></td>
      <td>${r.type}</td><td class="num">${free(r)}/${r.cap}</td>
      <td>${r.proj?"projector":""}${r.proj&&r.comp?", ":""}${r.comp?"computers":""}${!r.proj&&!r.comp?"–":""}</td>
      <td class="num">${path?fmt(dist)+" m":'<span class="pill crit">UNREACHABLE</span>'}</td></tr>`).join("")
    :`<tr><td>No rooms match these requirements.</td></tr>`;
}
for(const id of ["#r-origin","#r-type","#r-cap","#r-proj","#r-comp","#r-avail"])
  $(id).addEventListener("input",updateRooms);

/* ---------- energy tab ---------- */
function total(){return FW.prefix(FW.n)}
function buildEnergy(){
  const opts=ENERGY_ORDER.map((b,i)=>`<option value="${i+1}">${i+1} · ${b}</option>`).join("");
  $("#e-from").innerHTML=opts;$("#e-to").innerHTML=opts;$("#e-from").value=2;$("#e-to").value=4;
  $("#e-bars").innerHTML=ENERGY_ORDER.map((b,i)=>`<div class="bar" data-b="${b}">
    <span><b>${b}</b></span><div class="track"><div class="fill"></div></div>
    <span class="row" style="gap:6px;flex-wrap:nowrap"><input type="number" min="0" step="0.1" aria-label="${b} kWh" value="${ENERGY[b]}"><button type="button" class="btn sm ghost">Set</button></span></div>`).join("");
  $("#e-bars").addEventListener("click",e=>{
    const btn=e.target.closest("button");if(!btn)return;
    const row=btn.closest("[data-b]"),v=parseFloat(row.querySelector("input").value);
    if(!isFinite(v)||v<0){row.querySelector("input").value=ENERGY[row.dataset.b];return}
    const b=row.dataset.b;ENERGY[b]=v;FW.set(ENERGY_ORDER.indexOf(b)+1,v);refresh();
  });
  $("#e-from").addEventListener("change",updateEnergy);$("#e-to").addEventListener("change",updateEnergy);
}
function updateEnergy(){
  $("#e-total").textContent=fmt(total())+" kWh";
  const mx=Math.max(...ENERGY_ORDER.map(b=>ENERGY[b]),1);
  document.querySelectorAll("#e-bars .bar").forEach(row=>{
    row.querySelector(".fill").style.width=(ENERGY[row.dataset.b]/mx*100)+"%";
  });
  let l=Number($("#e-from").value),r=Number($("#e-to").value);
  if(r<l)[l,r]=[r,l];
  $("#e-range").innerHTML=`<span class="eyebrow">${ENERGY_ORDER.slice(l-1,r).join(", ")}</span>
    <span class="big mono">${fmt(FW.range(l,r))} kWh</span>`;
}

/* ---------- alerts tab ---------- */
function updateAlerts(){
  const q=ALERTS.view();
  $("#alerts").innerHTML=q.length?q.map(a=>`<div class="alert"><span class="pill ${a.p===1?"crit":a.p===2?"warn":"mut"}">P${a.p}</span><span>${esc(a.m)}</span></div>`).join("")
    :`<p class="empty">No pending alerts. Block a walkway or run a sensor update to raise one.</p>`;
  $("#pop").disabled=!q.length;
  $("#pop-out").textContent=S.lastPop;
  $("#sensors").innerHTML=`<tr><th>Room</th><th>Temp</th><th>Energy</th><th>Occupancy</th><th>On</th><th></th></tr>`+ROOMS.map(r=>`
    <tr data-r="${r.id}"><td><b>${esc(r.id)}</b></td><td class="num">${fmt(r.temp)} °C</td><td class="num">${fmt(r.kwh,2)} kWh</td>
    <td><input type="number" min="0" max="${r.cap}" value="${r.occ}" aria-label="${esc(r.id)} occupancy"> / ${r.cap}</td>
    <td><input type="checkbox" ${r.on?"checked":""} aria-label="${esc(r.id)} available"></td>
    <td><button type="button" class="btn sm ghost">Simulate</button></td></tr>`).join("");
}
$("#pop").addEventListener("click",()=>{
  const a=ALERTS.pop();S.lastPop=a?`Processed [P${a.p}] ${a.m}`:"";refresh();
});
$("#sensors").addEventListener("change",e=>{
  const tr=e.target.closest("[data-r]");if(!tr)return;
  const r=ROOMS.find(x=>x.id===tr.dataset.r);
  if(e.target.type==="checkbox"){r.on=e.target.checked;ALERTS.add(r.on?4:2,r.id+(r.on?" marked available.":" marked unavailable."))}
  else{
    const v=Math.round(Number(e.target.value));
    if(!isFinite(v)||v<0||v>r.cap){e.target.value=r.occ;return}
    r.occ=v;if(v>=r.cap)ALERTS.add(1,"Room "+r.id+" is at full capacity.");
  }
  refresh();
});
$("#sensors").addEventListener("click",e=>{
  const btn=e.target.closest("button"),tr=e.target.closest("[data-r]");if(!btn||!tr)return;
  const r=ROOMS.find(x=>x.id===tr.dataset.r);
  r.temp=Math.round((21+Math.random()*8)*10)/10;
  r.kwh=Math.round((r.kwh+0.1+Math.random()*1.9)*100)/100;
  r.occ=Math.floor(Math.random()*(r.cap+1));
  if(r.temp>=28)ALERTS.add(1,"High temperature in "+r.id+": "+fmt(r.temp)+" C");
  if(r.occ>=r.cap)ALERTS.add(1,"Room "+r.id+" is at full capacity.");
  refresh();
});

/* ---------- search tab ---------- */
const sAlgo={v:"kmp"};
function updateSearch(){
  const entries=[...G.loc.values()].map(l=>l.name).concat(ROOMS.map(r=>r.name),ROOMS.map(r=>r.id));
  const text=entries.join(" | ").toLowerCase();
  const pat=$("#s-q").value.trim().toLowerCase();
  if(!pat){$("#s-result").innerHTML=`<span class="muted">Type a building name or room code.</span>`;
    $("#s-entries").innerHTML=entries.map(e=>`<span class="chip">${esc(e)}</span>`).join("");return}
  let res,stat;
  if(sAlgo.v==="kmp"){res=kmp(text,pat);stat=`${res.cmp} character comparisons · LPS table [${res.lps.join(", ")}]`}
  else{res=rabinKarp(text,pat);stat=`${res.windows} windows hashed · ${res.verifs} full string checks`}
  const m=res.matches;
  $("#s-result").innerHTML=`<span class="eyebrow">Search results</span>
    <span class="big mono">${m.length} match${m.length===1?"":"es"}</span>
`;
  let off=0,html="";
  for(const e of entries){
    const lo=e.toLowerCase(),inside=m.filter(s=>s>=off&&s+pat.length<=off+lo.length).map(s=>s-off);
    let out="",last=0;
    for(const s of inside){out+=esc(e.slice(last,s))+"<mark>"+esc(e.slice(s,s+pat.length))+"</mark>";last=s+pat.length}
    out+=esc(e.slice(last));
    html+=`<span class="chip">${out}</span>`;off+=lo.length+3;
  }
  $("#s-entries").innerHTML=html;
}
$("#s-q").addEventListener("input",updateSearch);

/* ---------- header ---------- */
function updateStats(){
  const open=PATHS.length-G.blocked.size,av=ROOMS.filter(isAvail).length;
  $("#stats").innerHTML=[[G.loc.size,"Locations"],[open+"/"+PATHS.length,"Open walkways"],[av+"/"+ROOMS.length,"Rooms free"],[fmt(total())+" kWh","Energy today"]]
    .map(([v,l])=>`<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
}
/* ---------- main ---------- */
function refresh(){
  S.res={astar:G.aStar(S.start,S.goal),dijkstra:G.dijkstra(S.start,S.goal),bfs:G.bfs(S.start,S.goal)};
  S.mstRes=G.mst();
  renderMap();updateRoute();updateNet();updateRooms();updateEnergy();updateAlerts();updateStats();
}
buildTabs();showTab();fillSelects();buildEnergy();updateSearch();refresh();
})();
</script>

</body></html>
