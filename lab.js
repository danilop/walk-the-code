import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
import { initTerminal } from './terminal.js';

mermaid.initialize({ startOnLoad: false, theme: 'base', themeVariables: {
  primaryColor:'#1f3c5e',primaryBorderColor:'#58a6ff',primaryTextColor:'#e6edf3',
  secondaryColor:'#1e3a3e',secondaryBorderColor:'#4d9375',secondaryTextColor:'#e6edf3',
  tertiaryColor:'#2d233c',tertiaryBorderColor:'#a371c4',tertiaryTextColor:'#e6edf3',
  lineColor:'#8b949e',background:'#161b22',mainBkg:'#1f3c5e',
  nodeBorder:'#58a6ff',clusterBkg:'#161b22',clusterBorder:'#30363d',
  edgeLabelBackground:'#161b22',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif',fontSize:'14px'
}});

const labId = new URLSearchParams(location.search).get("lab");
let explanations={}, codeLines=[], selectedLine=null, staleLines=new Set();
let serverMode=false, labLanguage="python", annotatedLines=[], diagrams={};
let allLabs=[], allChapters=[], labDescription="";

const COMMENT_RE = {
  python:/^\s*#/,javascript:/^\s*\/\//,typescript:/^\s*\/\//,
  c:/^\s*\/\//,cpp:/^\s*\/\//,rust:/^\s*\/\//,go:/^\s*\/\//,java:/^\s*\/\//,
};

async function lineHash(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text.trim()));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,"0")).join("").slice(0,8);
}

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

// --- Data loading ---
async function loadServerData() {
  const r = await fetch("/api/labs");
  if (!r.ok) return null;
  serverMode = true;
  allLabs = await r.json();
  const labMeta = allLabs.find(l=>l.id===labId);
  const [expData, codeRes] = await Promise.all([
    fetch(`/api/explanations/${labId}`).then(r=>r.json()),
    fetch(`/api/code/${labId}`).then(r=>r.json()),
  ]);
  labLanguage = codeRes.language || labMeta?.language || "python";
  labDescription = labMeta?.description || "";
  const dIds = new Set(Object.values(expData).map(e=>typeof e==="object"?e.diagram:null).filter(Boolean));
  await Promise.all([...dIds].map(async id=>{
    try{const r=await fetch(`/api/diagrams/${id}`);if(r.ok){diagrams[id]=(await r.json()).source;}}catch(e){}
  }));
  try{const cr=await fetch("/api/chapters");if(cr.ok)allChapters=await cr.json();}catch(e){}
  return {labMeta, codeText:codeRes.code, expData};
}

async function loadStaticData() {
  const d = await (await fetch("data/labs.json")).json();
  allLabs = d.labs||d; allChapters = d.chapters||[];
  const lab = allLabs.find(l=>l.id===labId);
  if (!lab) return null;
  labLanguage = lab.language||"python";
  labDescription = lab.description||"";
  if (d.diagrams) diagrams = d.diagrams;
  document.getElementById("back-link").href = "index.html";
  return {labMeta:lab, codeText:lab.code, expData:lab.explanations};
}

// --- Rendering ---
function isComment(line) { return (COMMENT_RE[labLanguage]||COMMENT_RE.python).test(line); }

function buildAnnotatedLines() { annotatedLines = Object.keys(explanations).map(Number).sort((a,b)=>a-b); }

function ownerOf(lineNum) {
  if (annotatedLines.includes(lineNum)) return lineNum;
  const trimmed = (codeLines[lineNum-1]||"").trim();
  if (trimmed && !isComment(trimmed)) return lineNum;
  for (const al of annotatedLines) if (al>lineNum) return al;
  for (let i=annotatedLines.length-1;i>=0;i--) if (annotatedLines[i]<lineNum) return annotatedLines[i];
  return annotatedLines[0]||1;
}

function renderCode(code) {
  const hl = hljs.highlight(code,{language:labLanguage,ignoreIllegals:true}).value;
  const table = document.getElementById("code-table");
  hl.split("\n").forEach((html,i)=>{
    const ln=i+1, tr=document.createElement("tr"); tr.className="code-line";
    if(staleLines.has(ln)) tr.classList.add("stale");
    tr.dataset.line=ln;
    tr.innerHTML=`<td class="line-num">${ln}</td><td class="line-content">${html||" "}</td>`;
    tr.addEventListener("click",()=>selectLine(ownerOf(ln)));
    table.appendChild(tr);
  });
}

function highlightContext(lineNum) {
  let i=lineNum-2;
  while(i>=0){
    const t=codeLines[i].trim();
    if(isComment(t)||t===""){if(isComment(t)){const r=document.querySelector(`.code-line[data-line="${i+1}"]`);if(r)r.classList.add("context");}i--;}else break;
  }
}

function getExp(key,field) { const e=explanations[key]; if(!e)return null; return typeof e==="object"?e[field]||null:(field==="text"?e:null); }

let diagramCounter=0;
async function showExplanation(lineNum) {
  document.getElementById("explain-overview").style.display="none";
  document.getElementById("explain-line").style.display="block";
  document.getElementById("explain-ref").textContent=`Line ${lineNum}`;
  const key=String(lineNum), text=document.getElementById("explain-text"), diagEl=document.getElementById("diagram-container");
  const expText=getExp(key,"text");
  if(expText){
    let html=expText;
    if(staleLines.has(lineNum)) html+=`<div class="stale-warning"><span class="stale-dot"></span>Code changed since this annotation was written</div>`;
    text.innerHTML=html;
  } else {
    const t=(codeLines[lineNum-1]||"").trim();
    text.innerHTML=`<span style="color:var(--text-muted)">${!t?"Empty line":isComment(t)?"Comment line":"No annotation for this line."}</span>`;
  }
  const diagId=getExp(key,"diagram");
  if(diagId&&diagrams[diagId]){
    diagEl.classList.remove("hidden");
    let src=diagrams[diagId];
    const hl=getExp(key,"highlight");
    if(hl&&hl.length) src+=`\nclassDef wtcHighlight fill:#f96,stroke:#333,stroke-width:2px\nclass ${hl.join(",")} wtcHighlight`;
    try{const{svg}=await mermaid.render(`wtc-d-${++diagramCounter}`,src);diagEl.innerHTML=svg;}
    catch(e){diagEl.innerHTML='<span style="color:var(--text-muted)">Diagram error</span>';}
  } else { diagEl.classList.add("hidden"); diagEl.innerHTML=""; }
}

function selectLine(lineNum) {
  document.querySelectorAll(".code-line.selected,.code-line.context").forEach(el=>el.classList.remove("selected","context"));
  selectedLine=lineNum;
  const row=document.querySelector(`.code-line[data-line="${lineNum}"]`);
  if(row){row.classList.add("selected");highlightContext(lineNum);(document.querySelector(".code-line.context")||row).scrollIntoView({block:"center",behavior:"smooth"});}
  showExplanation(lineNum);
}

window.showOverview = function() {
  selectedLine=null;
  document.querySelectorAll(".code-line.selected,.code-line.context").forEach(el=>el.classList.remove("selected","context"));
  document.getElementById("explain-line").style.display="none";
  const ov=document.getElementById("explain-overview"); ov.style.display="block";
  if(labDescription) ov.innerHTML=`<div class="lab-desc">${labDescription}</div>`;
  else ov.innerHTML='<div style="color:var(--text-muted);margin-top:40px;text-align:center">Click a line to see its explanation</div>';
};
document.getElementById("overview-btn").onclick = window.showOverview;

function buildNav() {
  const nav=document.getElementById("nav-footer"), idx=allLabs.findIndex(l=>l.id===labId);
  if(idx<0) return;
  // Find chapter for this lab
  const ch=allChapters.find(c=>(c.labs||[]).includes(labId));
  if(ch) nav.innerHTML+=`<a class="nav-link chapter" href="chapter.html?chapter=${ch.id}">${ch.title}</a>`;
  if(idx>0) nav.innerHTML+=`<a class="nav-link" href="lab.html?lab=${allLabs[idx-1].id}">&larr; ${allLabs[idx-1].title}</a>`;
  if(idx<allLabs.length-1) nav.innerHTML+=`<a class="nav-link" href="lab.html?lab=${allLabs[idx+1].id}">${allLabs[idx+1].title} &rarr;</a>`;
}

// --- Keyboard nav ---
document.addEventListener("keydown",e=>{
  if(!annotatedLines.length) return;
  if(e.key==="Escape"){ e.preventDefault(); window.showOverview(); return; }
  if(selectedLine===null && (e.key==="ArrowDown"||e.key==="j")){ e.preventDefault(); selectLine(annotatedLines[0]); return; }
  if(selectedLine===null) return;
  const idx=annotatedLines.indexOf(selectedLine);
  if(e.key==="ArrowDown"||e.key==="j"){e.preventDefault();const n=idx>=0?idx+1:annotatedLines.findIndex(l=>l>selectedLine);if(n>=0&&n<annotatedLines.length)selectLine(annotatedLines[n]);}
  else if(e.key==="ArrowUp"||e.key==="k"){e.preventDefault();const p=idx>0?idx-1:annotatedLines.filter(l=>l<selectedLine).length-1;if(p>=0)selectLine(annotatedLines[p]);}
});

// --- Resize handles ---
(function(){
  const h=document.getElementById("h-resize"),ep=document.getElementById("explain-panel"),main=document.querySelector(".lab-main");
  let startX,startW;
  h.addEventListener("mousedown",e=>{e.preventDefault();startX=e.clientX;startW=ep.offsetWidth;h.classList.add("dragging");document.addEventListener("mousemove",drag);document.addEventListener("mouseup",up);});
  function drag(e){ep.style.width=Math.max(200,Math.min(main.offsetWidth*0.7,startW-(e.clientX-startX)))+"px";}
  function up(){h.classList.remove("dragging");document.removeEventListener("mousemove",drag);document.removeEventListener("mouseup",up);}
})();

// --- Init ---
(async()=>{
  let data;
  try { data = await loadServerData(); } catch(e) {}
  if (!data) data = await loadStaticData();
  if (!data) { document.body.textContent="Lab not found"; return; }

  const {labMeta, codeText, expData} = data;
  if(serverMode) document.getElementById("play-btn").style.display="inline-flex";
  if(labMeta){
    document.getElementById("lab-title").textContent=labMeta.title;
    document.getElementById("lab-tagline").textContent=labMeta.tagline||"";
    document.title=`${labMeta.title} — walk-the-code`;
  }
  explanations=expData||{}; codeLines=codeText.split("\n");
  for(const[ln,entry]of Object.entries(explanations)){
    if(typeof entry==="object"&&entry.hash){const i=parseInt(ln)-1;if(i>=0&&i<codeLines.length&&(await lineHash(codeLines[i]))!==entry.hash)staleLines.add(parseInt(ln));}
  }
  renderCode(codeText); buildAnnotatedLines(); buildNav();
  document.getElementById("code-panel").scrollTop=0;
  window.showOverview();
  if(staleLines.size>0){const t=document.createElement("span");t.className="stale-warning";t.innerHTML=`<span class="stale-dot"></span>${staleLines.size} annotation${staleLines.size>1?"s":""} may be outdated`;document.querySelector(".lab-header").appendChild(t);}
  initTerminal(labId, serverMode);
})();
