// @ts-check

/**
 * Edit mode: toggle between read-only annotated view and editable textarea.
 */

import { state, labId } from './lab-state.js';

/** @type {string} */
let originalCode = "";
/** @type {boolean} */
let editMode = false;

/**
 * Initialize edit mode controls.
 * @param {string} code - The original source code
 * @param {function} onReset - Callback to restore the annotated view
 */
export function initEditMode(code, onReset) {
  originalCode = code;
  const editBtn = document.getElementById("edit-btn");
  const resetBtn = document.getElementById("reset-btn");
  if (!editBtn || !resetBtn) return;

  editBtn.addEventListener("click", () => {
    if (editMode) return;
    enterEditMode();
  });

  resetBtn.addEventListener("click", () => {
    if (!editMode) return;
    exitEditMode(onReset);
  });
}

/** Show edit mode controls (only in server mode with run_command) */
export function showEditControls() {
  const editBtn = document.getElementById("edit-btn");
  if (editBtn) editBtn.style.display = "inline-flex";
}

function enterEditMode() {
  editMode = true;
  const codePanel = document.getElementById("code-panel");
  const codeTable = document.getElementById("code-table");
  const editBtn = document.getElementById("edit-btn");
  const resetBtn = document.getElementById("reset-btn");
  const playBtn = document.getElementById("play-btn");

  // Get current code (may already be modified from a previous edit session)
  const currentCode = getEditorCode() || originalCode;

  // Hide the table, show textarea
  codeTable.style.display = "none";

  let editor = /** @type {HTMLTextAreaElement} */ (document.getElementById("code-editor"));
  if (!editor) {
    editor = document.createElement("textarea");
    editor.id = "code-editor";
    editor.className = "code-editor";
    editor.spellcheck = false;
    editor.setAttribute("autocomplete", "off");
    editor.setAttribute("autocorrect", "off");
    editor.setAttribute("autocapitalize", "off");
    // Handle tab key for indentation
    editor.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + "    " + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
      }
    });
    codePanel.appendChild(editor);
  }

  editor.value = currentCode;
  editor.style.display = "block";
  editor.focus();

  // Update buttons
  editBtn.style.display = "none";
  resetBtn.style.display = "inline-flex";
  if (playBtn) {
    playBtn.setAttribute("data-modified", "true");
  }
}

/** @param {function} onReset */
function exitEditMode(onReset) {
  editMode = false;
  const codeTable = document.getElementById("code-table");
  const editor = document.getElementById("code-editor");
  const editBtn = document.getElementById("edit-btn");
  const resetBtn = document.getElementById("reset-btn");
  const playBtn = document.getElementById("play-btn");

  if (editor) editor.style.display = "none";
  codeTable.style.display = "";

  editBtn.style.display = "inline-flex";
  resetBtn.style.display = "none";
  if (playBtn) {
    playBtn.removeAttribute("data-modified");
  }

  onReset();
}

/** @returns {string|null} Get the current editor code, or null if not in edit mode */
export function getEditorCode() {
  if (!editMode) return null;
  const editor = /** @type {HTMLTextAreaElement} */ (document.getElementById("code-editor"));
  return editor ? editor.value : null;
}

/** @returns {boolean} */
export function isEditMode() {
  return editMode;
}
