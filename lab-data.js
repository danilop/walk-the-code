// @ts-check

/**
 * Data loading functions for the lab viewer.
 */

import { state, labId } from './lab-state.js';

/** @returns {Promise<{labMeta: Lab, codeText: string, expData: Record<string, Explanation|string>}|null>} */
export async function loadServerData() {
  const [r, config] = await Promise.all([fetch("/api/labs"), window.WTCSite.loadConfig()]);
  if (!r.ok) return null;
  state.serverMode = true;
  window.WTCSite.renderGitHubCorner(config);
  state.allLabs = await r.json();
  const labMeta = state.allLabs.find(l => l.id === labId);
  const [expData, codeRes] = await Promise.all([
    fetch(`/api/explanations/${labId}`).then(r => r.json()),
    fetch(`/api/code/${labId}`).then(r => r.json()),
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
  state.labLanguage = lab.language || "python";
  state.labDescription = lab.description || "";
  state.labObjectives = lab.learning_objectives || [];
  state.labExercises = lab.exercises || [];
  if (d.diagrams) state.diagrams = d.diagrams;
  document.getElementById("back-link").href = "index.html";
  return { labMeta: lab, codeText: lab.code, expData: lab.explanations };
}
