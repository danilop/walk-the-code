// @ts-check

/**
 * Data loading functions for the unit viewer.
 */

import { state, unitId } from './unit-state.js';

/** @param {Unit} u */
function storeUnitFiles(u) {
  if (u.files && u.files.length) {
    state.unitFiles = u.files.map(f => ({ path: f.path, language: f.language || u.language || 'python', role: f.role || 'supporting' }));
  } else {
    state.unitFiles = [{ path: u.file || '', language: u.language || 'python', role: 'primary' }];
  }
  const primary = state.unitFiles.find(f => f.role === 'primary') || state.unitFiles[0];
  state.currentFile = primary.path;
}

/** @returns {Promise<{unitMeta: Unit, codeText: string, expData: Record<string, Explanation|string>}|null>} */
export async function loadServerData() {
  const [r, config] = await Promise.all([fetch("/api/units"), window.WTCSite.loadConfig()]);
  if (!r.ok) return null;
  state.serverMode = true;
  window.WTCSite.renderGitHubCorner(config);
  state.allUnits = await r.json();
  const unitMeta = state.allUnits.find(l => l.id === unitId);
  if (unitMeta) storeUnitFiles(unitMeta);
  const fileParam = state.currentFile ? `?file=${encodeURIComponent(state.currentFile)}` : '';
  const [expData, codeRes] = await Promise.all([
    fetch(`/api/explanations/${unitId}${fileParam}`).then(r => r.json()),
    fetch(`/api/code/${unitId}${fileParam}`).then(r => r.json()),
  ]);
  state.unitLanguage = codeRes.language || unitMeta?.language || "python";
  state.unitDescription = unitMeta?.description || "";
  state.unitObjectives = unitMeta?.learning_objectives || [];
  state.unitExercises = unitMeta?.exercises || [];
  const dIds = new Set(Object.values(expData).map(e => typeof e === "object" ? e.diagram : null).filter(Boolean));
  await Promise.all([...dIds].map(async id => {
    try { const r = await fetch(`/api/diagrams/${id}`); if (r.ok) { state.diagrams[id] = (await r.json()).source; } } catch (e) { /* ignore */ }
  }));
  try { const cr = await fetch("/api/groups"); if (cr.ok) state.allGroups = await cr.json(); } catch (e) { /* ignore */ }
  return { unitMeta, codeText: codeRes.code, expData };
}

/** @returns {Promise<{unitMeta: Unit, codeText: string, expData: Record<string, Explanation|string>}|null>} */
export async function loadStaticData() {
  const d = await (await fetch("data/units.json")).json();
  window.WTCSite.renderGitHubCorner(d.config || {});
  state.allUnits = d.units || d;
  state.allGroups = d.groups || [];
  const u = state.allUnits.find(l => l.id === unitId);
  if (!u) return null;
  storeUnitFiles(u);
  state.unitLanguage = u.language || "python";
  state.unitDescription = u.description || "";
  state.unitObjectives = u.learning_objectives || [];
  state.unitExercises = u.exercises || [];
  if (d.diagrams) state.diagrams = d.diagrams;
  document.getElementById("back-link").href = "index.html";
  // For static mode with multi-file, load primary file data
  if (u.files && u.files.length) {
    const primary = u.files.find(f => f.role === 'primary') || u.files[0];
    return { unitMeta: u, codeText: primary.code, expData: primary.explanations };
  }
  return { unitMeta: u, codeText: u.code, expData: u.explanations };
}

/** @param {string} filename @returns {Promise<{codeText: string, expData: Record<string, Explanation|string>}>} */
export async function switchFile(filename) {
  state.currentFile = filename;
  const fileEntry = state.unitFiles.find(f => f.path === filename);
  let codeText, expData;
  if (state.serverMode) {
    const fileParam = `?file=${encodeURIComponent(filename)}`;
    const [codeRes, exp] = await Promise.all([
      fetch(`/api/code/${unitId}${fileParam}`).then(r => r.json()),
      fetch(`/api/explanations/${unitId}${fileParam}`).then(r => r.json()),
    ]);
    codeText = codeRes.code;
    expData = exp;
    state.unitLanguage = codeRes.language || fileEntry?.language || state.unitLanguage;
  } else {
    // Static mode: find file data in bundle
    const u = state.allUnits.find(l => l.id === unitId);
    const f = u?.files?.find(f => f.path === filename);
    codeText = f?.code || '';
    expData = f?.explanations || {};
    state.unitLanguage = f?.language || fileEntry?.language || state.unitLanguage;
  }
  state.explanations = expData;
  state.codeLines = codeText.split("\n");
  state.staleLines = new Set();
  state.annotatedLines = [];
  state.visitedLines = new Set();
  // Restore visited lines for this file
  try { const saved = localStorage.getItem(`wtc-visited-${unitId}-${filename}`); if (saved) state.visitedLines = new Set(JSON.parse(saved)); } catch (e) { /* ignore */ }
  return { codeText, expData };
}
