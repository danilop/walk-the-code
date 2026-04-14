// @ts-check
window.WTCSite = (() => {
  /** @type {SiteConfig|null} */
  let cachedConfig = null;

  /** @param {SiteConfig} config @returns {string} */
  function siteTitle(config) {
    return config?.title || "walk-the-code";
  }

  function _injectAnalytics() {
    if (cachedConfig && cachedConfig.analytics_snippet) {
      const div = document.createElement('div');
      div.innerHTML = cachedConfig.analytics_snippet;
      div.querySelectorAll('script').forEach(s => {
        const ns = document.createElement('script');
        [...s.attributes].forEach(a => ns.setAttribute(a.name, a.value));
        ns.textContent = s.textContent;
        document.body.appendChild(ns);
      });
    }
  }

  function _injectCredits() {
    // Always add meta generator tag
    if (!document.querySelector('meta[name="generator"]')) {
      const meta = document.createElement('meta');
      meta.name = 'generator';
      meta.content = 'walk-the-code';
      document.head.appendChild(meta);
    }
    // Add visible footer unless show_credits is explicitly false
    if (cachedConfig && cachedConfig.show_credits === false) return;
    if (document.querySelector('.wtc-credits')) return;
    const footer = document.createElement('div');
    footer.className = 'wtc-credits';
    footer.innerHTML = 'Generated with <a href="https://github.com/danilop/walk-the-code" target="_blank" rel="noreferrer">walk-the-code</a>';
    document.body.appendChild(footer);
  }

  /** @returns {Promise<SiteConfig>} */
  async function loadConfig() {
    if (cachedConfig) return cachedConfig;
    try {
      const response = await fetch("/api/config");
      if (response.ok) {
        cachedConfig = await response.json();
        _injectCredits();
        return cachedConfig;
      }
    } catch (e) {}
    try {
      const response = await fetch("data/units.json");
      const bundle = await response.json();
      cachedConfig = bundle.config || {};
      _injectAnalytics();
      _injectCredits();
      return cachedConfig;
    } catch (e) {
      cachedConfig = {};
      _injectCredits();
      return cachedConfig;
    }
  }

  /** @param {SiteConfig} config */
  function renderGitHubCorner(config) {
    const repoUrl = config?.repo_url;
    const existing = document.getElementById("github-corner");
    if (!repoUrl) {
      if (existing) existing.remove();
      return;
    }
    if (existing) existing.remove();
    if (!/^https:\/\//i.test(repoUrl)) return;
    const link = document.createElement("a");
    link.id = "github-corner";
    link.className = "github-corner";
    link.href = repoUrl;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.setAttribute("aria-label", "View source on GitHub");
    link.innerHTML = `<svg width="80" height="80" viewBox="0 0 250 250" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"/><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin:130px 106px" class="octo-arm"/><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"/></svg>`;
    document.body.prepend(link);
  }

  /** @param {string} pageTitle @param {SiteConfig} config */
  function setDocumentTitle(pageTitle, config) {
    document.title = pageTitle ? `${pageTitle} — ${siteTitle(config)}` : siteTitle(config);
  }

  /** @param {Unit[]} units */
  function addProgressBadges(units) {
    const unitAnnotations = {};
    if (Array.isArray(units)) {
      units.forEach(l => { if (l.annotated_lines) unitAnnotations[l.id] = l.annotated_lines; });
    }
    document.querySelectorAll(".unit-item").forEach(li => {
      const a = li.querySelector("a");
      if (!a) return;
      const u = new URL(a.href, location.href);
      const unitId = u.searchParams.get("unit");
      if (!unitId) return;
      const visited = localStorage.getItem(`wtc-visited-${unitId}`);
      const exercises = localStorage.getItem(`wtc-exercises-${unitId}`);
      if (!visited && !exercises) return;
      let visitedCount = 0;
      if (visited) {
        try { const v = JSON.parse(visited); visitedCount = Array.isArray(v) ? v.length : Object.keys(v).length; } catch(e) {}
      }
      if (visitedCount === 0 && !exercises) return;
      const total = unitAnnotations[unitId] || 0;
      const pct = total > 0 ? Math.min(100, Math.round((visitedCount / total) * 100)) : 0;
      const parts = [];
      if (total > 0 && pct > 0) {
        parts.push(`<div class="unit-progress-bar"><div class="unit-progress-fill" style="width:${pct}%"></div></div><span>${pct}%</span>`);
      } else if (visitedCount > 0) {
        parts.push(`<span>In progress</span>`);
      }
      if (exercises) {
        try {
          const ex = JSON.parse(exercises);
          const done = Array.isArray(ex) ? ex.filter(Boolean).length : Object.values(ex).filter(Boolean).length;
          if (done > 0) parts.push(`<span>${done} exercise${done !== 1 ? "s" : ""} done</span>`);
        } catch(e) {}
      }
      if (parts.length === 0) return;
      const badge = document.createElement("div");
      badge.className = "unit-progress";
      badge.innerHTML = parts.join("");
      const div = a.querySelector("div");
      if (div) div.appendChild(badge);
    });
  }

  /** @param {string} str @returns {string} */
  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  /** @param {SiteConfig} config @returns {ResolvedTerminology} */
  function terminology(config) {
    const t = config?.terminology || {};
    const group = t.group || 'Group';
    const unit = t.unit || 'Unit';
    return {
      group,
      groupPlural: t.group_plural || group + 's',
      unit,
      unitPlural: t.unit_plural || unit + 's',
    };
  }

  return { loadConfig, renderGitHubCorner, setDocumentTitle, siteTitle, addProgressBadges, escapeHtml, terminology };
})();
