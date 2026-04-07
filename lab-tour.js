// @ts-check
import { state } from './lab-state.js';
import { selectLine, showOverview, updateProgress } from './lab-render.js';

export function startTour() {
  state.tourActive = true;
  state.tourIndex = -1;
  showTourBar();
  advanceTour(1);
}

export function stopTour() {
  state.tourActive = false;
  state.tourIndex = -1;
  hideTourBar();
  showOverview();
}

export function advanceTour(direction) {
  state.tourIndex += direction;
  if (state.tourIndex < 0) { state.tourIndex = 0; return; }
  if (state.tourIndex >= state.annotatedLines.length) { showTourComplete(); return; }
  selectLine(state.annotatedLines[state.tourIndex]);
  updateTourBar();
}

function showTourBar() {
  let bar = document.getElementById('tour-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'tour-bar';
    bar.className = 'tour-bar';
    bar.innerHTML = `
      <button class="tour-btn" id="tour-prev">← Previous</button>
      <span class="tour-progress" id="tour-progress"></span>
      <button class="tour-btn" id="tour-next">Next →</button>
      <button class="tour-exit" id="tour-exit">✕ Exit Tour</button>
    `;
    document.body.appendChild(bar);
    document.getElementById('tour-prev').onclick = () => advanceTour(-1);
    document.getElementById('tour-next').onclick = () => advanceTour(1);
    document.getElementById('tour-exit').onclick = stopTour;
  }
  bar.classList.add('visible');
  updateTourBar();
}

function hideTourBar() {
  const bar = document.getElementById('tour-bar');
  if (bar) bar.classList.remove('visible');
}

function updateTourBar() {
  const prog = document.getElementById('tour-progress');
  const prev = document.getElementById('tour-prev');
  if (prog) prog.textContent = `${state.tourIndex + 1} / ${state.annotatedLines.length}`;
  if (prev) prev.disabled = state.tourIndex <= 0;
}

function showTourComplete() {
  state.tourActive = false;
  const bar = document.getElementById('tour-bar');
  if (bar) bar.innerHTML = `
    <span class="tour-complete">🎉 Tour complete! You explored all ${state.annotatedLines.length} annotated lines.</span>
    <button class="tour-btn" id="tour-restart">↺ Restart</button>
    <button class="tour-exit" id="tour-done">Done</button>
  `;
  document.getElementById('tour-restart')?.addEventListener('click', () => { startTour(); });
  document.getElementById('tour-done')?.addEventListener('click', () => { hideTourBar(); showOverview(); });
}
