// @ts-check
// @ts-ignore — CDN ESM import has no type declarations
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
import { initTerminal } from './terminal.js';

import { state, unitId, lineHash } from './unit-state.js';
import { loadServerData, loadStaticData, switchFile } from './unit-data.js';
import {
  renderCode, buildAnnotatedLines, buildNav, selectLine,
  showOverview, updateProgress, setMermaidRef, selectAdjacentAnnotatedLine,
  dismissCodeCoach, showCodeCoach, renderFileTabs, clearCode, setTourStartCallback,
} from './unit-render.js';
import { initSearch } from './unit-search.js';
import { initEditMode, showEditControls, getEditorCode } from './unit-edit.js';
import { startTour, stopTour, advanceTour } from './unit-tour.js';

// --- Global error handlers ---
/** @param {string} msg */
function showErrorBanner(msg) {
  let banner = document.querySelector('.error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.className = 'error-banner';
    document.body.appendChild(banner);
  }
  banner.innerHTML = `<span>\u26a0 ${msg}</span><button onclick="this.parentElement.remove()">Dismiss</button>`;
}
window.addEventListener('error', (e) => {
  showErrorBanner(`Unexpected error: ${e.message || 'Unknown error'}`);
});
window.addEventListener('unhandledrejection', (e) => {
  showErrorBanner(`Unhandled promise error: ${e.reason?.message || e.reason || 'Unknown error'}`);
});

// --- Mermaid initialization ---
mermaid.initialize({ startOnLoad: false, theme: 'base', themeVariables: {
  primaryColor:'#1f3c5e',primaryBorderColor:'#58a6ff',primaryTextColor:'#e6edf3',
  secondaryColor:'#1e3a3e',secondaryBorderColor:'#4d9375',secondaryTextColor:'#e6edf3',
  tertiaryColor:'#2d233c',tertiaryBorderColor:'#a371c4',tertiaryTextColor:'#e6edf3',
  lineColor:'#8b949e',background:'#161b22',mainBkg:'#1f3c5e',
  nodeBorder:'#58a6ff',clusterBkg:'#161b22',clusterBorder:'#30363d',
  edgeLabelBackground:'#161b22',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif',fontSize:'14px'
}});

// Pass mermaid reference to the render module for showExplanation
setMermaidRef(mermaid);

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

// --- showOverview on window (used by HTML onclick) ---
window.showOverview = showOverview;
document.getElementById("overview-btn").onclick = showOverview;
document.getElementById("prev-line-btn").onclick = () => selectAdjacentAnnotatedLine(-1);
document.getElementById("next-line-btn").onclick = () => selectAdjacentAnnotatedLine(1);
document.getElementById("code-coach-close").onclick = () => dismissCodeCoach();
document.getElementById("tips-btn").onclick = () => showCodeCoach();

// --- Search ---
initSearch();

// --- Keyboard nav ---
document.addEventListener("keydown", e => {
  // Don't intercept keys when typing in an input, textarea, or contenteditable
  const tag = /** @type {HTMLElement} */ (e.target).tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || /** @type {HTMLElement} */ (e.target).isContentEditable) return;
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); const btn = document.getElementById("play-btn"); if (btn && btn.style.display !== "none") btn.click(); return; }
  if (!state.annotatedLines.length) return;
  if (e.key === "Escape") { e.preventDefault(); if (state.tourActive) { stopTour(); } else { showOverview(); } return; }
  if (state.tourActive) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); advanceTour(1); return; }
    if (e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); advanceTour(-1); return; }
  }
  if (state.selectedLine === null && (e.key === "ArrowDown" || e.key === "j")) { e.preventDefault(); selectAdjacentAnnotatedLine(1); return; }
  if (state.selectedLine === null) return;
  if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); selectAdjacentAnnotatedLine(1); }
  else if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); selectAdjacentAnnotatedLine(-1); }
});

// --- Resize handles ---
(function () {
  const h = document.getElementById("h-resize"), ep = document.getElementById("explain-panel"), main = document.querySelector(".unit-main");
  let startX, startW;
  h.addEventListener("mousedown", e => { e.preventDefault(); startX = e.clientX; startW = ep.offsetWidth; h.classList.add("dragging"); document.addEventListener("mousemove", drag); document.addEventListener("mouseup", up); });
  function drag(e) { ep.style.width = Math.max(200, Math.min(main.offsetWidth * 0.7, startW - (e.clientX - startX))) + "px"; }
  function up() { h.classList.remove("dragging"); document.removeEventListener("mousemove", drag); document.removeEventListener("mouseup", up); }
})();

// --- Init ---
(async () => {
  let data, serverError = null, staticError = null;
  try { data = await loadServerData(); } catch (e) { serverError = e; }
  if (!data) { try { data = await loadStaticData(); } catch (e) { staticError = e; } }
  if (!data) {
    const isNetwork = serverError && (serverError.message?.includes('fetch') || serverError.message?.includes('network') || serverError instanceof TypeError);
    const msg = isNetwork
      ? 'Unable to connect to the server. Please check your network connection and try again.'
      : (serverError || staticError)
        ? `Failed to load unit data: ${(staticError || serverError).message || 'Unknown error'}`
        : 'Unit not found. The requested unit does not exist.';
    document.body.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-muted)"><h2 style="margin-bottom:12px;color:var(--text)">${isNetwork ? 'Connection Error' : 'Unit Not Found'}</h2><p>${msg}</p><a href="${state.serverMode ? '/' : 'index.html'}" style="display:inline-block;margin-top:16px;color:var(--accent)">Back to units</a></div>`;
    return;
  }

  const { unitMeta, codeText, expData } = data;
  if (state.serverMode) {
    document.getElementById("play-btn").style.display = "inline-flex";
    showEditControls();
  } else {
    const hint = document.getElementById("run-hint"); if (hint) hint.style.display = "inline-flex";
  }
  if (unitMeta) {
    document.getElementById("unit-title").textContent = unitMeta.title;
    document.getElementById("unit-tagline").textContent = unitMeta.tagline || "";
    const cfg = await window.WTCSite.loadConfig();
    window.WTCSite.setDocumentTitle(unitMeta.title, cfg);
    const terms = window.WTCSite.terminology(cfg);
    document.getElementById("back-link").textContent = `\u2190 ${terms.unitPlural}`;
  }
  state.explanations = expData || {};
  state.codeLines = codeText.split("\n");
  for (const [ln, entry] of Object.entries(state.explanations)) {
    if (typeof entry === "object" && entry.hash) {
      const i = parseInt(ln) - 1;
      if (i >= 0 && i < state.codeLines.length && (await lineHash(state.codeLines[i])) !== entry.hash) state.staleLines.add(parseInt(ln));
    }
  }
  renderCode(codeText);
  buildAnnotatedLines();
  buildNav();
  try { const savedEx = localStorage.getItem(`wtc-exercises-${unitId}`); if (savedEx) state.completedExercises = new Set(JSON.parse(savedEx)); } catch (e) { /* ignore */ }
  try { const saved = localStorage.getItem(`wtc-visited-${unitId}`); if (saved) { state.visitedLines = new Set(JSON.parse(saved)); state.visitedLines.forEach(ln => { const r = document.querySelector(`.code-line[data-line="${ln}"]`); if (r) r.classList.add("visited"); }); } } catch (e) { /* ignore */ }
  updateProgress();
  document.getElementById("code-panel").scrollTop = 0;
  showOverview();
  setTourStartCallback(() => startTour());
  const { params } = await import('./unit-state.js');
  if (params.get('tour') === 'true') startTour();
  const handleFileSwitch = async (filename) => {
    const { codeText } = await switchFile(filename);
    renderCode(codeText);
    buildAnnotatedLines();
    showOverview();
    updateProgress();
    renderFileTabs(handleFileSwitch);
  };
  renderFileTabs(handleFileSwitch);
  if (state.staleLines.size > 0) { const t = document.createElement("span"); t.className = "stale-warning"; t.innerHTML = `<span class="stale-dot"></span>${state.staleLines.size} annotation${state.staleLines.size > 1 ? "s" : ""} may be outdated`; document.querySelector(".unit-header").appendChild(t); }
  initEditMode(codeText, () => showOverview());
  initTerminal(unitId, state.serverMode, { getModifiedCode: getEditorCode });
  const expToggle = document.getElementById("explain-toggle");
  if (expToggle) expToggle.onclick = () => { document.getElementById("explain-panel").classList.toggle("mobile-hidden"); expToggle.classList.toggle("collapsed"); };
})();
