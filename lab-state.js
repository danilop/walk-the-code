// @ts-check

/**
 * Shared state and constants for the lab viewer.
 * State is exported as a mutable object so mutations are visible across modules.
 */

const labId = new URLSearchParams(location.search).get("lab");

/** @type {{ explanations: Record<string, Explanation|string>, codeLines: string[], selectedLine: number|null, staleLines: Set<number>, serverMode: boolean, labLanguage: string, annotatedLines: number[], diagrams: Record<string, string>, visitedLines: Set<number>, completedExercises: Set<number>, allLabs: Lab[], allChapters: Chapter[], labDescription: string, labObjectives: string[], labExercises: Exercise[] }} */
export const state = {
  explanations: {},
  codeLines: [],
  selectedLine: null,
  staleLines: new Set(),
  serverMode: false,
  labLanguage: "python",
  annotatedLines: [],
  diagrams: {},
  visitedLines: new Set(),
  completedExercises: new Set(),
  allLabs: [],
  allChapters: [],
  labDescription: "",
  labObjectives: [],
  labExercises: [],
};

export { labId };

/** @type {Record<string, RegExp>} */
export const COMMENT_RE = {
  python: /^\s*(#|"""|''')/,
  javascript: /^\s*\/\//,
  typescript: /^\s*\/\//,
  c: /^\s*\/\//,
  cpp: /^\s*\/\//,
  rust: /^\s*\/\//,
  go: /^\s*\/\//,
  java: /^\s*\/\//,
};

/** @param {string} text @returns {Promise<string>} */
export async function lineHash(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text.trim()));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 8);
}
