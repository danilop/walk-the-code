// @ts-check

/**
 * Search functionality for the lab viewer.
 */

import { state } from './lab-state.js';
import { selectLine } from './lab-render.js';

export function initSearch() {
  const searchInput = /** @type {HTMLInputElement} */ (document.getElementById("explain-search"));
  const searchResults = document.getElementById("search-results");
  /** @type {ReturnType<typeof setTimeout>|null} */
  let debounceTimer = null;

  /** @param {string} html @returns {string} */
  function stripHtml(html) {
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    return tmp.textContent || "";
  }

  /**
   * @param {string} text
   * @param {string} query
   * @returns {string}
   */
  function highlightMatch(text, query) {
    const esc = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${esc})`, 'gi'), '<mark>$1</mark>');
  }

  /** @param {string} query */
  function doSearch(query) {
    try {
      searchResults.innerHTML = "";
      if (!query.trim()) { return; }
      const q = query.toLowerCase();
      const matches = [];
      for (const [key, entry] of Object.entries(state.explanations)) {
        const text = typeof entry === "object" ? (entry.text || "") : entry;
        const plain = stripHtml(text);
        if (plain.toLowerCase().includes(q)) {
          const ln = parseInt(key);
          const idx = plain.toLowerCase().indexOf(q);
          const start = Math.max(0, idx - 30);
          const end = Math.min(plain.length, idx + query.length + 50);
          let snippet = (start > 0 ? "..." : "") + plain.slice(start, end) + (end < plain.length ? "..." : "");
          matches.push({ line: ln, snippet });
        }
      }
      if (matches.length === 0) {
        searchResults.innerHTML = '<div class="search-count">0 matches found</div>';
        return;
      }
      matches.sort((a, b) => a.line - b.line);
      searchResults.innerHTML = `<div class="search-count">${matches.length} match${matches.length > 1 ? "es" : ""} found</div>`;
      for (const m of matches) {
        const div = document.createElement("div");
        div.className = "search-result";
        div.innerHTML = `<span class="line-ref">Line ${m.line}:</span>${highlightMatch(m.snippet, query)}`;
        div.addEventListener("click", () => { selectLine(m.line); searchInput.value = ""; searchResults.innerHTML = ""; });
        searchResults.appendChild(div);
      }
    } catch (e) {
      searchResults.innerHTML = '<div class="search-count" style="color:#f85149">Search error: ' + e.message + '</div>';
      console.error("Search error:", e);
    }
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => doSearch(searchInput.value), 200);
  });

  document.getElementById("explain-panel").addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "f") { e.preventDefault(); e.stopPropagation(); searchInput.focus(); searchInput.select(); }
  });
}
