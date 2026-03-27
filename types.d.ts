/**
 * Type declarations for walk-the-code frontend.
 * Used with @ts-check in .js files for editor type checking without a build step.
 */

/** Lab metadata as returned by /api/labs or from labs.json */
interface Lab {
  id: string;
  title: string;
  tagline?: string;
  description?: string;
  file: string;
  language?: string;
  learning_objectives?: string[];
  exercises?: Exercise[];
  run_command?: string[];
  annotated_lines?: number;
  // Static mode only
  code?: string;
  explanations?: Record<string, Explanation | string>;
}

/** Exercise prompt with optional hint */
interface Exercise {
  prompt: string;
  hint?: string;
}

/** Line-level explanation entry in comment JSON */
interface Explanation {
  text: string;
  hash?: string;
  diagram?: string;
  highlight?: string[];
}

/** Knowledge check question for chapter quizzes */
interface KnowledgeCheck {
  question: string;
  options: string[];
  correct: number;
  explanation: string;
}

/** Chapter definition from config */
interface Chapter {
  id: string;
  title: string;
  description?: string;
  diagram?: string;
  comparison_diagram?: string;
  labs?: string[];
  knowledge_checks?: KnowledgeCheck[];
}

/** Site config (top-level fields from config.json) */
interface SiteConfig {
  title?: string;
  tagline?: string;
  repo_url?: string;
}

/** Static bundle from data/labs.json */
interface LabsBundle {
  config?: SiteConfig;
  labs: Lab[];
  chapters?: Chapter[];
  diagrams?: Record<string, string>;
}

/** Code response from /api/code/{labId} */
interface CodeResponse {
  code: string;
  filename: string;
  language?: string;
}

/** SSE status event data */
interface StatusEvent {
  state: "running" | "done";
  cmd?: string;
  exit_code?: number;
}

/** SSE output event data */
interface OutputEvent {
  text: string;
}

/** WTCSite module exposed on window */
interface WTCSiteModule {
  loadConfig(): Promise<SiteConfig>;
  renderGitHubCorner(config: SiteConfig): void;
  setDocumentTitle(pageTitle: string, config: SiteConfig): void;
  siteTitle(config: SiteConfig): string;
  addProgressBadges(labs: Lab[]): void;
  escapeHtml(str: string): string;
}

interface Window {
  WTCSite: WTCSiteModule;
  showOverview: () => void;
}

/** highlight.js global */
declare const hljs: {
  highlight(code: string, options: { language: string; ignoreIllegals?: boolean }): { value: string };
};

/** Mermaid global (chapter.js uses it as a global, not ESM import) */
declare const mermaid: {
  initialize(config: Record<string, unknown>): void;
  render(id: string, source: string): Promise<{ svg: string }>;
};
