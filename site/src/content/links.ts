/** The public repository. */
export const REPO_URL = "https://github.com/soneeee22000/faultline-noc";

/** The author's GitHub profile. */
export const AUTHOR_URL = "https://github.com/soneeee22000";

/** OWASP's page on prompt injection (checked for a 200 response on 2026-09-15). */
export const OWASP_PROMPT_INJECTION_URL =
  "https://genai.owasp.org/llmrisk/llm01-prompt-injection/";

/** A file on the repository's main branch. */
export function repoFile(path: string): string {
  return `${REPO_URL}/blob/main/${path}`;
}

/** A directory on the repository's main branch. */
export function repoTree(path: string): string {
  return `${REPO_URL}/tree/main/${path}`;
}
