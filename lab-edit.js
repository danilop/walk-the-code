// @ts-check

/**
 * Edit mode: toggle between read-only annotated view and an editable
 * code editor with syntax highlighting (overlay technique: transparent
 * textarea over a highlight.js-rendered <pre>) and line numbers.
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

/** Sync highlighted <pre> content with the textarea value */
function syncHighlight(editor, highlight) {
  const code = editor.value;
  const rendered = hljs.highlight(code + "\n", { language: state.labLanguage, ignoreIllegals: true }).value;
  highlight.innerHTML = rendered;
}

/** Update line number gutter to match current line count */
function syncLineNumbers(editor, gutter) {
  const lineCount = editor.value.split("\n").length;
  const nums = [];
  for (let i = 1; i <= lineCount; i++) nums.push(i);
  gutter.textContent = nums.join("\n");
}

function enterEditMode() {
  editMode = true;
  const codePanel = document.getElementById("code-panel");
  const codeTable = document.getElementById("code-table");
  const editBtn = document.getElementById("edit-btn");
  const resetBtn = document.getElementById("reset-btn");

  const currentCode = getEditorCode() || originalCode;

  // Hide the annotated table
  codeTable.style.display = "none";

  // Visual hint: edit mode border
  codePanel.classList.add("edit-mode");

  // Create or show the editor wrapper
  let wrapper = document.getElementById("editor-wrapper");
  if (!wrapper) {
    wrapper = document.createElement("div");
    wrapper.id = "editor-wrapper";
    wrapper.className = "editor-wrapper";

    // Line number gutter
    const gutter = document.createElement("div");
    gutter.id = "editor-gutter";
    gutter.className = "editor-gutter";

    // Container for the code area (highlight + textarea overlay)
    const codeArea = document.createElement("div");
    codeArea.className = "editor-code-area";

    // Highlighted backdrop
    const highlight = document.createElement("pre");
    highlight.id = "editor-highlight";
    highlight.className = "editor-highlight";

    // Transparent textarea on top
    const editor = document.createElement("textarea");
    editor.id = "code-editor";
    editor.className = "code-editor";
    editor.spellcheck = false;
    editor.setAttribute("autocomplete", "off");
    editor.setAttribute("autocorrect", "off");
    editor.setAttribute("autocapitalize", "off");

    // Sync highlight and line numbers on input
    editor.addEventListener("input", () => {
      syncHighlight(editor, highlight);
      syncLineNumbers(editor, gutter);
    });

    // Sync scroll positions (textarea -> highlight + gutter)
    editor.addEventListener("scroll", () => {
      highlight.scrollTop = editor.scrollTop;
      highlight.scrollLeft = editor.scrollLeft;
      gutter.scrollTop = editor.scrollTop;
    });

    // Tab key for indentation
    editor.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + "    " + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
        syncHighlight(editor, highlight);
      }
    });

    codeArea.appendChild(highlight);
    codeArea.appendChild(editor);
    wrapper.appendChild(gutter);
    wrapper.appendChild(codeArea);
    codePanel.appendChild(wrapper);
  }

  const editor = /** @type {HTMLTextAreaElement} */ (document.getElementById("code-editor"));
  const highlight = document.getElementById("editor-highlight");
  const gutter = document.getElementById("editor-gutter");

  wrapper.style.display = "flex";
  editor.value = currentCode;
  syncHighlight(editor, highlight);
  syncLineNumbers(editor, gutter);
  editor.focus();

  // Update buttons
  editBtn.style.display = "none";
  resetBtn.style.display = "inline-flex";
}

/** @param {function} onReset */
function exitEditMode(onReset) {
  editMode = false;
  const codePanel = document.getElementById("code-panel");
  const codeTable = document.getElementById("code-table");
  const wrapper = document.getElementById("editor-wrapper");
  const editBtn = document.getElementById("edit-btn");
  const resetBtn = document.getElementById("reset-btn");

  if (wrapper) wrapper.style.display = "none";
  codeTable.style.display = "";
  codePanel.classList.remove("edit-mode");

  editBtn.style.display = "inline-flex";
  resetBtn.style.display = "none";

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
