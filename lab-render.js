// @ts-check

/**
 * DOM rendering and interaction for the lab viewer.
 */

import { state, labId, COMMENT_RE } from './lab-state.js';

/** @param {string} line @returns {boolean} */
export function isComment(line) {
  return (COMMENT_RE[state.labLanguage] || COMMENT_RE.python).test(line);
}

export function buildAnnotatedLines() {
  state.annotatedLines = Object.keys(state.explanations).map(Number).sort((a, b) => a - b);
}

/** @param {number} lineNum @returns {number} */
export function ownerOf(lineNum) {
  if (state.annotatedLines.includes(lineNum)) return lineNum;
  const trimmed = (state.codeLines[lineNum - 1] || "").trim();
  if (trimmed && !isComment(trimmed)) return lineNum;
  for (const al of state.annotatedLines) if (al > lineNum) return al;
  for (let i = state.annotatedLines.length - 1; i >= 0; i--) if (state.annotatedLines[i] < lineNum) return state.annotatedLines[i];
  return state.annotatedLines[0] || 1;
}

/** @param {string} code */
export function renderCode(code) {
  const hl = hljs.highlight(code, { language: state.labLanguage, ignoreIllegals: true }).value;
  const table = document.getElementById("code-table");
  hl.split("\n").forEach((html, i) => {
    const ln = i + 1, tr = document.createElement("tr");
    tr.className = "code-line";
    if (state.staleLines.has(ln)) tr.classList.add("stale");
    tr.dataset.line = String(ln);
    tr.innerHTML = `<td class="line-num">${ln}</td><td class="line-content">${html || " "}</td>`;
    tr.addEventListener("click", () => selectLine(ownerOf(ln)));
    table.appendChild(tr);
  });
}

/** @param {number} lineNum */
export function highlightContext(lineNum) {
  let i = lineNum - 2;
  while (i >= 0) {
    const t = state.codeLines[i].trim();
    if (isComment(t) || t === "") {
      if (isComment(t)) {
        const r = document.querySelector(`.code-line[data-line="${i + 1}"]`);
        if (r) r.classList.add("context");
      }
      i--;
    } else break;
  }
}

/** @param {string} key @param {string} field @returns {*} */
export function getExp(key, field) {
  const e = state.explanations[key];
  if (!e) return null;
  return typeof e === "object" ? e[field] || null : (field === "text" ? e : null);
}

let diagramCounter = 0;

/**
 * @param {number} lineNum
 * @param {object} mermaidInstance - The mermaid module instance
 */
export async function showExplanation(lineNum, mermaidInstance) {
  try {
    document.getElementById("explain-overview").style.display = "none";
    document.getElementById("explain-line").style.display = "block";
    document.getElementById("explain-ref").textContent = `Line ${lineNum}`;
    const key = String(lineNum), text = document.getElementById("explain-text"), diagEl = document.getElementById("diagram-container");
    const expText = getExp(key, "text");
    if (expText) {
      let html = expText;
      if (state.staleLines.has(lineNum)) html += `<div class="stale-warning"><span class="stale-dot"></span>Code changed since this annotation was written</div>`;
      text.innerHTML = html;
    } else {
      const t = (state.codeLines[lineNum - 1] || "").trim();
      text.innerHTML = `<span style="color:var(--text-muted)">${!t ? "Empty line" : isComment(t) ? "Comment line" : "No annotation for this line."}</span>`;
    }
    const diagId = getExp(key, "diagram");
    if (diagId && state.diagrams[diagId]) {
      diagEl.classList.remove("hidden");
      let src = state.diagrams[diagId];
      const hl = getExp(key, "highlight");
      if (hl && hl.length) src += `\nclassDef wtcHighlight fill:#f96,stroke:#333,stroke-width:2px\nclass ${hl.join(",")} wtcHighlight`;
      const renderId = `wtc-d-${++diagramCounter}`;
      try {
        const { svg } = await mermaidInstance.render(renderId, src);
        diagEl.innerHTML = svg;
      } catch (e) {
        diagEl.innerHTML = `<span style="color:var(--text-muted)">Diagram error (${renderId}: ${diagId})</span>`;
      }
    } else {
      diagEl.classList.add("hidden");
      diagEl.innerHTML = "";
    }
  } catch (e) {
    const text = document.getElementById("explain-text");
    if (text) text.innerHTML = '<span style="color:#f85149">Error rendering explanation</span>';
    console.error("showExplanation error:", e);
  }
}

/** Updates the progress bar based on visited annotated lines */
export function updateProgress() {
  const total = state.annotatedLines.length;
  if (!total) return;
  const visited = state.annotatedLines.filter(l => state.visitedLines.has(l)).length;
  const pct = Math.round((visited / total) * 100);
  const fill = document.getElementById("progress-fill");
  const text = document.getElementById("progress-text");
  if (fill) fill.style.width = pct + "%";
  if (text) text.textContent = `${visited}/${total} lines explored`;
}

/** @type {object|null} */
let _mermaidRef = null;

/** @param {object} mermaidInstance */
export function setMermaidRef(mermaidInstance) {
  _mermaidRef = mermaidInstance;
}

/** @param {number} lineNum */
export function selectLine(lineNum) {
  document.querySelectorAll(".code-line.selected,.code-line.context").forEach(el => el.classList.remove("selected", "context"));
  state.selectedLine = lineNum;
  const row = document.querySelector(`.code-line[data-line="${lineNum}"]`);
  if (row) {
    row.classList.add("selected");
    highlightContext(lineNum);
    (document.querySelector(".code-line.context") || row).scrollIntoView({ block: "center", behavior: "smooth" });
  }
  if (state.annotatedLines.includes(lineNum)) {
    state.visitedLines.add(lineNum);
    try { localStorage.setItem(`wtc-visited-${labId}`, JSON.stringify([...state.visitedLines])); } catch (e) { /* ignore */ }
    if (row) row.classList.add("visited");
  }
  showExplanation(lineNum, _mermaidRef);
  updateProgress();
}

export function showOverview() {
  state.selectedLine = null;
  document.querySelectorAll(".code-line.selected,.code-line.context").forEach(el => el.classList.remove("selected", "context"));
  document.getElementById("explain-line").style.display = "none";
  const ov = document.getElementById("explain-overview");
  ov.style.display = "block";
  let ovHtml = '';
  if (state.labDescription) ovHtml += `<div class="lab-desc">${state.labDescription}</div>`;
  if (state.labObjectives.length) ovHtml += `<div class="learning-objectives"><h3>Learning Objectives</h3><ul>${state.labObjectives.map(o => `<li>${o}</li>`).join("")}</ul></div>`;
  if (state.labExercises.length) {
    ovHtml += `<div class="exercises"><h3>Exercises</h3><div class="exercise-count">${state.completedExercises.size}/${state.labExercises.length} completed</div>${state.labExercises.map((ex, i) => `<div class="exercise"><label class="exercise-label"><input type="checkbox" class="exercise-check" data-idx="${i}" ${state.completedExercises.has(i) ? 'checked' : ''}><span class="exercise-prompt">${ex.prompt}</span></label>${ex.hint ? `<div class="exercise-hint" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'">Show hint</div><div class="exercise-hint-text">${ex.hint}</div>` : ""}</div>`).join("")}</div>`;
  }
  if (ovHtml) {
    // Add reset progress link
    ovHtml += `<div class="reset-progress"><button class="reset-progress-btn" id="reset-progress-btn">Reset progress for this lab</button></div>`;
    ov.innerHTML = ovHtml;
    ov.querySelectorAll('.exercise-check').forEach(cb => {
      cb.addEventListener('change', e => {
        const idx = parseInt(/** @type {HTMLInputElement} */(e.target).dataset.idx);
        if (/** @type {HTMLInputElement} */(e.target).checked) state.completedExercises.add(idx); else state.completedExercises.delete(idx);
        try { localStorage.setItem(`wtc-exercises-${labId}`, JSON.stringify([...state.completedExercises])); } catch (ex) { /* ignore */ }
        const counter = ov.querySelector('.exercise-count');
        if (counter) counter.textContent = `${state.completedExercises.size}/${state.labExercises.length} completed`;
      });
    });
    const resetBtn = document.getElementById("reset-progress-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        state.visitedLines = new Set();
        state.completedExercises = new Set();
        try { localStorage.removeItem(`wtc-visited-${labId}`); } catch (e) { /* ignore */ }
        try { localStorage.removeItem(`wtc-exercises-${labId}`); } catch (e) { /* ignore */ }
        document.querySelectorAll(".code-line.visited").forEach(el => el.classList.remove("visited"));
        updateProgress();
        showOverview(); // Re-render to uncheck exercise boxes
      });
    }
  } else {
    ov.innerHTML = '<div style="color:var(--text-muted);margin-top:40px;text-align:center">Click a line to see its explanation</div>';
  }
}

export function buildNav() {
  const nav = document.getElementById("nav-footer"), idx = state.allLabs.findIndex(l => l.id === labId);
  if (idx < 0) return;
  const ch = state.allChapters.find(c => (c.labs || []).includes(labId));
  if (ch) nav.innerHTML += `<a class="nav-link chapter" href="chapter.html?chapter=${ch.id}">${ch.title}</a>`;
  if (idx > 0) nav.innerHTML += `<a class="nav-link" href="lab.html?lab=${state.allLabs[idx - 1].id}">&larr; ${state.allLabs[idx - 1].title}</a>`;
  if (idx < state.allLabs.length - 1) nav.innerHTML += `<a class="nav-link" href="lab.html?lab=${state.allLabs[idx + 1].id}">${state.allLabs[idx + 1].title} &rarr;</a>`;
}
