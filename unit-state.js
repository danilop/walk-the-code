// @ts-check

/**
 * Shared state and constants for the unit viewer.
 * State is exported as a mutable object so mutations are visible across modules.
 */

const params = new URLSearchParams(location.search);
const unitId = params.get("unit");

/** @type {{ explanations: Record<string, Explanation|string>, codeLines: string[], selectedLine: number|null, staleLines: Set<number>, serverMode: boolean, unitLanguage: string, annotatedLines: number[], diagrams: Record<string, string>, visitedLines: Set<number>, completedExercises: Set<number>, allUnits: Unit[], allGroups: Group[], unitDescription: string, unitObjectives: string[], unitExercises: Exercise[], unitFiles: {path:string, language:string, role:string}[], currentFile: string|null }} */
export const state = {
  explanations: {},
  codeLines: [],
  selectedLine: null,
  staleLines: new Set(),
  serverMode: false,
  unitLanguage: "python",
  annotatedLines: [],
  diagrams: {},
  visitedLines: new Set(),
  completedExercises: new Set(),
  allUnits: [],
  allGroups: [],
  unitDescription: "",
  unitObjectives: [],
  unitExercises: [],
  unitFiles: [],
  currentFile: null,
  tourActive: false,
  tourIndex: -1,
};

export { unitId, params };

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
