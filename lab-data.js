// @ts-check

/**
 * Data loading functions for the lab viewer.
 */

import { state, labId } from './lab-state.js';

/** @param {Lab} lab */
function storeLabFiles(lab) {
  if (lab.files && lab.files.length) {
    state.labFiles = lab.files.map(f => ({ path: f.path, language: f.language || lab.language || 'python', role: f.role || 'supporting' }));
  } else {
    state.labFiles = [{ path: lab.file || '', language: lab.language || 'python', role: 'primary' }];
  }
  const primary = state.labFiles.find(f => f.role === 'primary') || state.labFiles[0];
  state.currentFile = primary.path;
}

/** @returns {Promise<{labMeta: Lab, codeText: string, expData: Record<string, Explanation|string>}|null>} */
export async function loadServerData() {
  const [r, config] = await Promise.all([fetch("/api/labs"), window.WTCSite.loadConfig()]);
  if (!r.ok) return null;
  state.serverMode = true;
  window.WTCSite.renderGitHubCorner(config);
  state.allLabs = await r.json();
  const labMeta = state.allLabs.find(l => l.id === labId);
  if (labMeta) storeLabFiles(labMeta);
  const fileParam = state.currentFile ? `?file=${encodeURIComponent(state.currentFile)}` : '';
  const [expData, codeRes] = await Promise.all([
    fetch(`/api/explanations/${labId}${fileParam}`).then(r => r.json()),
    fetch(`/api/code/${labId}${fileParam}`).then(r => r.json()),
  ]);
  state.labLanguage = codeRes.language || labMeta?.language || "python";
  state.labDescription = labMeta?.description || "";
  state.labObjectives = labMeta?.learning_objectives || [];
  state.labExercises = labMeta?.exercises || [];
  const dIds = new Set(Object.values(expData).map(e => typeof e === "object" ? e.diagram : null).filter(Boolean));
  await Promise.all([...dIds].map(async id => {
    try { const r = await fetch(`/api/diagrams/${id}`); if (r.ok) { state.diagrams[id] = (await r.json()).source; } } catch (e) { /* ignore */ }
  }));
  try { const cr = await fetch("/api/chapters"); if (cr.ok) state.allChapters = await cr.json(); } catch (e) { /* ignore */ }
  return { labMeta, codeText: codeRes.code, expData };
}

/** @returns {Promise<{labMeta: Lab, codeText: string, expData: Record<string, Explanation|string>}|null>} */
export async function loadStaticData() {
  const d = await (await fetch("data/labs.json")).json();
  window.WTCSite.renderGitHubCorner(d.config || {});
  state.allLabs = d.labs || d;
  state.allChapters = d.chapters || [];
  const lab = state.allLabs.find(l => l.id === labId);
  if (!lab) return null;
  storeLabFiles(lab);
  state.labLanguage = lab.language || "python";
  state.labDescription = lab.description || "";
  state.labObjectives = lab.learning_objectives || [];
  state.labExercises = lab.exercises || [];
  if (d.diagrams) state.diagrams = d.diagrams;
  document.getElementById("back-link").href = "index.html";
  // For static mode with multi-file, load primary file data
  if (lab.files && lab.files.length) {
    const primary = lab.files.find(f => f.role === 'primary') || lab.files[0];
    return { labMeta: lab, codeText: primary.code, expData: primary.explanations };
  }
  return { labMeta: lab, codeText: lab.code, expData: lab.explanations };
}

/** @param {string} filename @returns {Promise<{codeText: string, expData: Record<string, Explanation|string>}>} */
export async function switchFile(filename) {
  state.currentFile = filename;
  const fileEntry = state.labFiles.find(f => f.path === filename);
  let codeText, expData;
  if (state.serverMode) {
    const fileParam = `?file=${encodeURIComponent(filename)}`;
    const [codeRes, exp] = await Promise.all([
      fetch(`/api/code/${labId}${fileParam}`).then(r => r.json()),
      fetch(`/api/explanations/${labId}${fileParam}`).then(r => r.json()),
    ]);
    codeText = codeRes.code;
    expData = exp;
    state.labLanguage = codeRes.language || fileEntry?.language || state.labLanguage;
  } else {
    // Static mode: find file data in bundle
    const lab = state.allLabs.find(l => l.id === labId);
    const f = lab?.files?.find(f => f.path === filename);
    codeText = f?.code || '';
    expData = f?.explanations || {};
    state.labLanguage = f?.language || fileEntry?.language || state.labLanguage;
  }
  state.explanations = expData;
  state.codeLines = codeText.split("\n");
  state.staleLines = new Set();
  state.annotatedLines = [];
  state.visitedLines = new Set();
  // Restore visited lines for this file
  try { const saved = localStorage.getItem(`wtc-visited-${labId}-${filename}`); if (saved) state.visitedLines = new Set(JSON.parse(saved)); } catch (e) { /* ignore */ }
  return { codeText, expData };
}
