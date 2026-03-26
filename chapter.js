mermaid.initialize({ startOnLoad:false, theme:'base', themeVariables:{
  primaryColor:'#1f3c5e',primaryBorderColor:'#58a6ff',primaryTextColor:'#e6edf3',
  lineColor:'#8b949e',background:'#161b22',mainBkg:'#1f3c5e',
  nodeBorder:'#58a6ff',clusterBkg:'#161b22',clusterBorder:'#30363d',
  edgeLabelBackground:'#161b22',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif',fontSize:'14px'
}});

const chapterId = new URLSearchParams(location.search).get("chapter");

(async () => {
  let chapters, labs;
  try {
    const r = await fetch("/api/chapters");
    if (r.ok) { chapters = await r.json(); labs = await (await fetch("/api/labs")).json(); }
  } catch(e) {}
  if (!chapters) {
    const d = await (await fetch("data/labs.json")).json();
    chapters = d.chapters||[]; labs = d.labs||d;
    document.getElementById("back-link").href = "index.html";
  }

  const labMap = {}; labs.forEach((l,i) => labMap[l.id] = {...l, idx:i});
  const ci = chapters.findIndex(c => c.id === chapterId);
  const ch = chapters[ci];
  if (!ch) { document.body.textContent = "Chapter not found"; return; }

  document.getElementById("ch-num").textContent = `Chapter ${ci+1}`;
  document.getElementById("ch-title").textContent = ch.title;
  document.title = `${ch.title} — walk-the-code`;
  document.getElementById("ch-desc").innerHTML = ch.description || "";

  if (ch.diagram) {
    const box = document.getElementById("diagram-box"); box.style.display = "block";
    try { const {svg} = await mermaid.render("ch-diag", ch.diagram); box.innerHTML = svg; }
    catch(e) { box.innerHTML = '<span style="color:var(--text-muted)">Diagram error</span>'; }
  }

  const ul = document.getElementById("labs");
  (ch.labs||[]).forEach(id => {
    const l = labMap[id]; if (!l) return;
    ul.innerHTML += `<li class="lab-item"><a href="lab.html?lab=${l.id}"><span class="lab-num">${String(l.idx+1).padStart(2,"0")}</span><div><div class="lab-title-text">${l.title}</div><div class="lab-tagline">${l.tagline||""}</div></div></a></li>`;
  });

  const nav = document.getElementById("nav-row");
  if (ci > 0) nav.innerHTML += `<a class="nav-btn" href="chapter.html?chapter=${chapters[ci-1].id}">&larr; ${chapters[ci-1].title}</a>`;
  if (ci < chapters.length-1) nav.innerHTML += `<a class="nav-btn" href="chapter.html?chapter=${chapters[ci+1].id}">${chapters[ci+1].title} &rarr;</a>`;
})();
