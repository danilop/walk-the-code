// @ts-check
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
import { state, labId, params } from './lab-state.js';
import { loadStaticData, switchFile } from './lab-data.js';
import {
  renderCode, buildAnnotatedLines, selectLine, showOverview,
  updateProgress, setMermaidRef, selectAdjacentAnnotatedLine, renderFileTabs,
  setTourStartCallback,
} from './lab-render.js';
import { startTour, stopTour, advanceTour } from './lab-tour.js';

mermaid.initialize({ startOnLoad: false, theme: 'base', themeVariables: {
  primaryColor:'#1f3c5e',primaryBorderColor:'#58a6ff',primaryTextColor:'#e6edf3',
  secondaryColor:'#1e3a3e',secondaryBorderColor:'#4d9375',secondaryTextColor:'#e6edf3',
  tertiaryColor:'#2d233c',tertiaryBorderColor:'#a371c4',tertiaryTextColor:'#e6edf3',
  lineColor:'#8b949e',background:'#161b22',mainBkg:'#1f3c5e',
  nodeBorder:'#58a6ff',clusterBkg:'#161b22',clusterBorder:'#30363d',
  edgeLabelBackground:'#161b22',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif',fontSize:'14px'
}});
setMermaidRef(mermaid);

window.showOverview = showOverview;
document.getElementById("prev-line-btn").onclick = () => selectAdjacentAnnotatedLine(-1);
document.getElementById("next-line-btn").onclick = () => selectAdjacentAnnotatedLine(1);

// Keyboard nav
document.addEventListener("keydown", e => {
  const tag = /** @type {HTMLElement} */ (e.target).tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  if (!state.annotatedLines.length) return;
  if (e.key === "Escape") { e.preventDefault(); if (state.tourActive) stopTour(); else showOverview(); return; }
  if (state.tourActive) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); advanceTour(1); return; }
    if (e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); advanceTour(-1); return; }
  }
  if (state.selectedLine === null && (e.key === "ArrowDown" || e.key === "j")) { e.preventDefault(); selectAdjacentAnnotatedLine(1); return; }
  if (state.selectedLine === null) return;
  if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); selectAdjacentAnnotatedLine(1); }
  else if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); selectAdjacentAnnotatedLine(-1); }
});

// Resize handle
(function () {
  const h = document.getElementById("h-resize"), ep = document.getElementById("explain-panel"), main = document.querySelector(".lab-main");
  let startX, startW;
  h.addEventListener("mousedown", e => { e.preventDefault(); startX = e.clientX; startW = ep.offsetWidth; h.classList.add("dragging"); document.addEventListener("mousemove", drag); document.addEventListener("mouseup", up); });
  function drag(e) { ep.style.width = Math.max(200, Math.min(main.offsetWidth * 0.7, startW - (e.clientX - startX))) + "px"; }
  function up() { h.classList.remove("dragging"); document.removeEventListener("mousemove", drag); document.removeEventListener("mouseup", up); }
})();

// postMessage API
window.addEventListener("message", e => {
  if (!e.data || typeof e.data !== "object") return;
  if (e.data.type === "wtc:selectLine" && typeof e.data.line === "number") selectLine(e.data.line);
  if (e.data.type === "wtc:selectFile" && typeof e.data.file === "string") handleFileSwitch(e.data.file);
});

const handleFileSwitch = async (filename) => {
  const { codeText } = await switchFile(filename);
  renderCode(codeText);
  buildAnnotatedLines();
  showOverview();
  updateProgress();
  renderFileTabs(handleFileSwitch);
};

// Notify parent on line selection (override selectLine behavior via MutationObserver on explain-ref)
new MutationObserver(() => {
  if (state.selectedLine !== null && window.parent !== window) {
    window.parent.postMessage({ type: 'wtc:lineSelected', line: state.selectedLine, lab: labId }, '*');
  }
}).observe(document.getElementById("explain-ref"), { childList: true, characterData: true, subtree: true });

// Init
(async () => {
  let data;
  try { data = await loadStaticData(); } catch (e) { /* ignore */ }
  if (!data) {
    document.body.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">Lab not found.</div>';
    return;
  }
  const { codeText } = data;
  state.explanations = data.expData || {};
  state.codeLines = codeText.split("\n");
  renderCode(codeText);
  buildAnnotatedLines();
  renderFileTabs(handleFileSwitch);
  updateProgress();
  showOverview();
  setTourStartCallback(() => startTour());

  const lineParam = params.get('line');
  if (lineParam) selectLine(parseInt(lineParam, 10));
  if (params.get('tour') === 'true') startTour();
})();
