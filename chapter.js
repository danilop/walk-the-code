mermaid.initialize({ startOnLoad:false, theme:'base', themeVariables:{
  primaryColor:'#1f3c5e',primaryBorderColor:'#58a6ff',primaryTextColor:'#e6edf3',
  lineColor:'#8b949e',background:'#161b22',mainBkg:'#1f3c5e',
  nodeBorder:'#58a6ff',clusterBkg:'#161b22',clusterBorder:'#30363d',
  edgeLabelBackground:'#161b22',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif',fontSize:'14px'
}});

const chapterId = new URLSearchParams(location.search).get("chapter");

(async () => {
  let chapters, labs, config, diagrams={}, serverMode=false;
  try {
    const r = await fetch("/api/chapters");
    if (r.ok) {
      chapters = await r.json();
      labs = await (await fetch("/api/labs")).json();
      config = await window.WTCSite.loadConfig();
      serverMode = true;
    }
  } catch(e) {}
  if (!chapters) {
    const d = await (await fetch("data/labs.json")).json();
    chapters = d.chapters||[]; labs = d.labs||d;
    config = d.config || {};
    diagrams = d.diagrams || {};
    document.getElementById("back-link").href = "index.html";
  }

  window.WTCSite.renderGitHubCorner(config);

  const labMap = {}; labs.forEach((l,i) => labMap[l.id] = {...l, idx:i});
  const ci = chapters.findIndex(c => c.id === chapterId);
  const ch = chapters[ci];
  if (!ch) { document.body.textContent = "Chapter not found"; return; }

  document.getElementById("ch-num").textContent = `Chapter ${ci+1}`;
  document.getElementById("ch-title").textContent = ch.title;
  window.WTCSite.setDocumentTitle(ch.title, config);
  document.getElementById("ch-desc").innerHTML = ch.description || "";

  if (ch.diagram) {
    const box = document.getElementById("diagram-box"); box.style.display = "block";
    try { const {svg} = await mermaid.render("ch-diag", ch.diagram); box.innerHTML = svg; }
    catch(e) { box.innerHTML = '<span style="color:var(--text-muted)">Diagram error</span>'; }
  }

  if (ch.comparison_diagram) {
    let src = diagrams[ch.comparison_diagram];
    if (!src && serverMode) {
      try { const r = await fetch(`/api/diagrams/${ch.comparison_diagram}`); if (r.ok) src = (await r.json()).source; } catch(e) {}
    }
    if (src) {
      const wrap = document.createElement("div");
      wrap.innerHTML = `<h2 style="font-size:1.1rem;font-weight:600;margin-bottom:10px;color:var(--text-muted)">How the labs compare</h2><div class="diagram-box" id="compare-box"></div>`;
      document.getElementById("diagram-box").after(wrap);
      try { const {svg} = await mermaid.render("ch-comp", src); wrap.querySelector("#compare-box").innerHTML = svg; }
      catch(e) { wrap.querySelector("#compare-box").innerHTML = '<span style="color:var(--text-muted)">Diagram error</span>'; }
    }
  }

  const ul = document.getElementById("labs");
  (ch.labs||[]).forEach(id => {
    const l = labMap[id]; if (!l) return;
    ul.innerHTML += `<li class="lab-item"><a href="lab.html?lab=${l.id}"><span class="lab-num">${String(l.idx+1).padStart(2,"0")}</span><div><div class="lab-title-text">${WTCSite.escapeHtml(l.title)}</div><div class="lab-tagline">${WTCSite.escapeHtml(l.tagline||"")}</div></div></a></li>`;
  });

  window.WTCSite.addProgressBadges(labs);

  // --- Knowledge Checks ---
  if (ch.knowledge_checks && ch.knowledge_checks.length > 0) {
    const storageKey = `wtc-quiz-${chapterId}`;
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch(e) {}

    const container = document.getElementById("knowledge-checks");
    const section = document.createElement("div");
    section.className = "knowledge-checks";
    section.innerHTML = `<h2>Knowledge Check</h2>`;

    ch.knowledge_checks.forEach((check, qi) => {
      const card = document.createElement("div");
      card.className = "quiz-card";
      const qKey = `q${qi}`;
      const answered = saved[qKey] !== undefined;

      let optionsHtml = "";
      check.options.forEach((opt, oi) => {
        let cls = "quiz-option";
        if (answered) {
          cls += " answered";
          if (oi === check.correct) cls += " correct";
          if (oi === saved[qKey] && oi !== check.correct) cls += " incorrect";
          if (oi === saved[qKey]) cls += " selected";
        }
        optionsHtml += `<li class="${cls}" data-qi="${qi}" data-oi="${oi}"><input type="radio" name="quiz-${qi}" ${answered ? "disabled" : ""} ${answered && oi === saved[qKey] ? "checked" : ""}><span>${WTCSite.escapeHtml(opt)}</span></li>`;
      });

      card.innerHTML = `
        <div class="quiz-question">${qi + 1}. ${WTCSite.escapeHtml(check.question)}</div>
        <ul class="quiz-options">${optionsHtml}</ul>
        <div class="quiz-explanation${answered ? " visible" : ""}">${WTCSite.escapeHtml(check.explanation)}</div>
      `;
      section.appendChild(card);
    });

    // Score display
    const scoreDiv = document.createElement("div");
    scoreDiv.className = "quiz-score";
    const updateScore = () => {
      const total = ch.knowledge_checks.length;
      const answeredCount = Object.keys(saved).length;
      const correctCount = Object.values(saved).filter((v, i) => {
        const idx = parseInt(Object.keys(saved).find(k => saved[k] === v && k === `q${i}`) || "-1");
        return false;
      }).length;
      let correct = 0;
      for (const [k, v] of Object.entries(saved)) {
        const qi = parseInt(k.replace("q", ""));
        if (ch.knowledge_checks[qi] && v === ch.knowledge_checks[qi].correct) correct++;
      }
      if (answeredCount > 0) {
        scoreDiv.textContent = `${correct}/${answeredCount} correct${answeredCount < total ? ` (${total - answeredCount} remaining)` : ""}`;
      }
    };
    updateScore();
    section.appendChild(scoreDiv);

    // Click handler for options
    section.addEventListener("click", (e) => {
      const option = e.target.closest(".quiz-option");
      if (!option || option.classList.contains("answered")) return;
      const qi = parseInt(option.dataset.qi);
      const oi = parseInt(option.dataset.oi);
      const check = ch.knowledge_checks[qi];
      const qKey = `q${qi}`;

      // Save answer
      saved[qKey] = oi;
      try { localStorage.setItem(storageKey, JSON.stringify(saved)); } catch(e) {}

      // Update all options in this question
      const card = option.closest(".quiz-card");
      card.querySelectorAll(".quiz-option").forEach((opt) => {
        const optOi = parseInt(opt.dataset.oi);
        opt.classList.add("answered");
        if (optOi === check.correct) opt.classList.add("correct");
        if (optOi === oi && optOi !== check.correct) opt.classList.add("incorrect");
        if (optOi === oi) opt.classList.add("selected");
        opt.querySelector("input").disabled = true;
        if (optOi === oi) opt.querySelector("input").checked = true;
      });

      // Show explanation
      card.querySelector(".quiz-explanation").classList.add("visible");
      updateScore();
    });

    container.appendChild(section);
  }

  const nav = document.getElementById("nav-row");
  if (ci > 0) nav.innerHTML += `<a class="nav-btn" href="chapter.html?chapter=${chapters[ci-1].id}">&larr; ${WTCSite.escapeHtml(chapters[ci-1].title)}</a>`;
  if (ci < chapters.length-1) nav.innerHTML += `<a class="nav-btn" href="chapter.html?chapter=${chapters[ci+1].id}">${WTCSite.escapeHtml(chapters[ci+1].title)} &rarr;</a>`;
})();
