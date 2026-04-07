// @ts-check

/**
 * Shared state and constants for the lab viewer.
 * State is exported as a mutable object so mutations are visible across modules.
 */

const params = new URLSearchParams(location.search);
const labId = params.get("lab");

/** @type {{ explanations: Record<string, Explanation|string>, codeLines: string[], selectedLine: number|null, staleLines: Set<number>, serverMode: boolean, labLanguage: string, annotatedLines: number[], diagrams: Record<string, string>, visitedLines: Set<number>, completedExercises: Set<number>, allLabs: Lab[], allChapters: Chapter[], labDescription: string, labObjectives: string[], labExercises: Exercise[], labFiles: {path:string, language:string, role:string}[], currentFile: string|null }} */
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
  labFiles: [],
  currentFile: null,
  tourActive: false,
  tourIndex: -1,
};

export { labId, params };

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
