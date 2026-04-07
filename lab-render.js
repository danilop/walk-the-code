// @ts-check

/**
 * DOM rendering and interaction for the lab viewer.
 */

import { state, labId, COMMENT_RE } from './lab-state.js';

const CODE_COACH_KEY = "wtc-code-coach-dismissed";

let _onTourStart = null;
/** @param {function():void} fn */
export function setTourStartCallback(fn) { _onTourStart = fn; }

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

export function clearCode() {
  const table = document.getElementById("code-table");
  while (table.firstChild) table.removeChild(table.firstChild);
}

/** @param {function(string):void} onSwitch */
export function renderFileTabs(onSwitch) {
  if (state.labFiles.length <= 1) return;
  const existing = document.querySelector('.file-tabs');
  if (existing) existing.remove();
  const bar = document.createElement('div');
  bar.className = 'file-tabs';
  state.labFiles.forEach(f => {
    const tab = document.createElement('button');
    tab.className = 'file-tab' + (f.path === state.currentFile ? ' active' : '');
    tab.textContent = f.path.split('/').pop();
    tab.title = f.path;
    tab.onclick = () => { if (f.path !== state.currentFile) onSwitch(f.path); };
    bar.appendChild(tab);
  });
  const codePanel = document.getElementById('code-panel');
  codePanel.insertBefore(bar, codePanel.firstChild);
}

/** @param {string} code */
export function renderCode(code) {
  clearCode();
  const hl = hljs.highlight(code, { language: state.labLanguage, ignoreIllegals: true }).value;
  const table = document.getElementById("code-table");
  hl.split("\n").forEach((html, i) => {
    const ln = i + 1, tr = document.createElement("tr");
    tr.className = "code-line";
    if (state.staleLines.has(ln)) tr.classList.add("stale");
    tr.dataset.line = String(ln);
    const key = String(ln);
    let gutterCls = "line-num";
    const exp = state.explanations[key];
    if (exp) {
      if (getExp(key, "diagram")) gutterCls += " has-diagram";
      else if (typeof exp === "object" && exp.important) gutterCls += " has-important";
      else gutterCls += " has-annotation";
    }
    tr.innerHTML = `<td class="${gutterCls}">${ln}</td><td class="line-content">${html || " "}</td>`;
    tr.addEventListener("click", () => selectLine(ownerOf(ln)));
    table.appendChild(tr);
  });
}

function coachDismissed() {
  try { return localStorage.getItem(CODE_COACH_KEY) === "1"; } catch (e) { return false; }
}

/** @param {boolean} persist */
export function dismissCodeCoach(persist = true) {
  const coach = document.getElementById("code-coach");
  if (coach) coach.classList.add("hidden");
  if (!persist) return;
  try { localStorage.setItem(CODE_COACH_KEY, "1"); } catch (e) { /* ignore */ }
}

export function showCodeCoach() {
  const coach = document.getElementById("code-coach");
  if (coach) coach.classList.remove("hidden");
  try { localStorage.removeItem(CODE_COACH_KEY); } catch (e) { /* ignore */ }
}

export function updateCodeCoach() {
  const coach = document.getElementById("code-coach");
  if (!coach) return;
  const shouldShow = state.selectedLine === null && state.annotatedLines.length > 0 && !coachDismissed();
  coach.classList.toggle("hidden", !shouldShow);
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

/**
 * @param {*} highlight
 * @returns {{nodes: string[], links: number[]}}
 */
function normalizeDiagramHighlight(highlight) {
  const spec = { nodes: [], links: [] };
  if (Array.isArray(highlight)) {
    spec.nodes = highlight.filter(id => typeof id === "string" && id);
    return spec;
  }
  if (!highlight || typeof highlight !== "object") return spec;
  if (Array.isArray(highlight.nodes)) {
    spec.nodes = highlight.nodes.filter(id => typeof id === "string" && id);
  }
  if (Array.isArray(highlight.links)) {
    spec.links = highlight.links.filter(idx => Number.isInteger(idx) && idx >= 0);
  }
  return spec;
}

/**
 * @param {{nodes: string[], links: number[]}} highlight
 * @returns {string}
 */
function buildDiagramHighlightStyles(highlight) {
  const parts = [];
  if (highlight.nodes.length) {
    parts.push("classDef wtcHighlight fill:#f96,stroke:#333,stroke-width:2px,color:#111");
    parts.push(`class ${highlight.nodes.join(",")} wtcHighlight`);
  }
  if (highlight.links.length) {
    parts.push(`linkStyle ${highlight.links.join(",")} stroke:#f96,stroke-width:4px`);
  }
  return parts.length ? `\n${parts.join("\n")}` : "";
}

let diagramCounter = 0;

/**
 * @param {number} direction
 * @param {number|null} [fromLine]
 * @returns {number|null}
 */
export function getAdjacentAnnotatedLine(direction, fromLine = state.selectedLine) {
  if (!state.annotatedLines.length) return null;
  if (fromLine === null) return direction > 0 ? state.annotatedLines[0] : state.annotatedLines[state.annotatedLines.length - 1];
  const idx = state.annotatedLines.indexOf(fromLine);
  if (direction > 0) {
    if (idx >= 0) return state.annotatedLines[idx + 1] ?? null;
    return state.annotatedLines.find(l => l > fromLine) ?? null;
  }
  if (idx > 0) return state.annotatedLines[idx - 1];
  const prev = state.annotatedLines.filter(l => l < fromLine);
  return prev.length ? prev[prev.length - 1] : null;
}

export function updateLineNavControls() {
  const nav = document.getElementById("line-nav");
  const prevBtn = /** @type {HTMLButtonElement|null} */ (document.getElementById("prev-line-btn"));
  const nextBtn = /** @type {HTMLButtonElement|null} */ (document.getElementById("next-line-btn"));
  if (!nav || !prevBtn || !nextBtn) return;
  const visible = state.selectedLine !== null && state.annotatedLines.length > 0;
  nav.classList.toggle("hidden", !visible);
  if (!visible) return;
  prevBtn.disabled = getAdjacentAnnotatedLine(-1) === null;
  nextBtn.disabled = getAdjacentAnnotatedLine(1) === null;
}

/** @param {number} direction */
export function selectAdjacentAnnotatedLine(direction) {
  const target = getAdjacentAnnotatedLine(direction);
  if (target !== null) selectLine(target);
}

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
      const highlight = normalizeDiagramHighlight(getExp(key, "highlight"));
      src += buildDiagramHighlightStyles(highlight);
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
  dismissCodeCoach();
  showExplanation(lineNum, _mermaidRef);
  updateProgress();
  updateLineNavControls();
}

export function showOverview() {
  state.selectedLine = null;
  document.querySelectorAll(".code-line.selected,.code-line.context").forEach(el => el.classList.remove("selected", "context"));
  document.getElementById("explain-line").style.display = "none";
  const ov = document.getElementById("explain-overview");
  ov.style.display = "block";
  let ovHtml = '';
  if (state.labDescription) ovHtml += `<div class="lab-desc">${state.labDescription}</div>`;
  if (state.labObjectives.length) ovHtml += `<div class="learning-objectives"><h3>Learning Objectives</h3><ul>${state.labObjectives.map(o => `<li>${window.WTCSite.escapeHtml(o)}</li>`).join("")}</ul></div>`;
  if (state.labExercises.length) {
    ovHtml += `<div class="exercises"><h3>Exercises</h3><div class="exercise-count">${state.completedExercises.size}/${state.labExercises.length} completed</div>${state.labExercises.map((ex, i) => `<div class="exercise"><label class="exercise-label"><input type="checkbox" class="exercise-check" data-idx="${i}" ${state.completedExercises.has(i) ? 'checked' : ''}><span class="exercise-prompt">${window.WTCSite.escapeHtml(ex.prompt)}</span></label>${ex.hint ? `<div class="exercise-hint" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'">Show hint</div><div class="exercise-hint-text">${window.WTCSite.escapeHtml(ex.hint)}</div>` : ""}</div>`).join("")}</div>`;
  }
  if (ovHtml) {
    // Add reset progress link
    ovHtml += `<button class="tour-start-btn" id="tour-start-btn">▶ Start Guided Tour</button>`;
    ovHtml += `<div class="reset-progress"><button class="reset-progress-btn" id="reset-progress-btn">Reset progress for this lab</button><button class="reset-progress-btn" id="show-tips-btn">Show tips again</button></div>`;
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
    const showTipsBtn = document.getElementById("show-tips-btn");
    if (showTipsBtn) showTipsBtn.addEventListener("click", () => showCodeCoach());
    const tourBtn = document.getElementById("tour-start-btn");
    if (tourBtn) tourBtn.addEventListener("click", () => { if (_onTourStart) _onTourStart(); });
  } else {
    ov.innerHTML = '<div style="color:var(--text-muted);margin-top:40px;text-align:center">Click a line to see its explanation</div>';
  }
  updateLineNavControls();
  updateCodeCoach();
}

export function buildNav() {
  const nav = document.getElementById("nav-footer"), idx = state.allLabs.findIndex(l => l.id === labId);
  if (idx < 0) return;
  function findChapter(chapters) {
    for (const c of chapters) {
      if ((c.labs || []).includes(labId)) return c;
      if (c.chapters) { const found = findChapter(c.chapters); if (found) return found; }
    }
    return null;
  }
  const ch = findChapter(state.allChapters);
  if (ch) nav.innerHTML += `<a class="nav-link chapter" href="chapter.html?chapter=${ch.id}">${window.WTCSite.escapeHtml(ch.title)}</a>`;
  if (idx > 0) nav.innerHTML += `<a class="nav-link" href="lab.html?lab=${state.allLabs[idx - 1].id}">&larr; ${window.WTCSite.escapeHtml(state.allLabs[idx - 1].title)}</a>`;
  if (idx < state.allLabs.length - 1) nav.innerHTML += `<a class="nav-link" href="lab.html?lab=${state.allLabs[idx + 1].id}">${window.WTCSite.escapeHtml(state.allLabs[idx + 1].title)} &rarr;</a>`;
}
