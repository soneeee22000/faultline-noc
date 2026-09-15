import { AUTHOR_URL, REPO_URL } from "../content/links";
import { payload } from "../data/payload";
import { code, mount } from "../lib/dom";

/** The footer: author, repository, licence and the data honesty line. */
export function renderFooter(): void {
  mount(
    "footer",
    `<div class="container site-footer__inner">
      <p>Built by <a href="${AUTHOR_URL}">Pyae Sone (Seon)</a>.</p>
      <p>Source: <a href="${REPO_URL}">github.com/soneeee22000/faultline-noc</a>, MIT License.</p>
      <p class="muted">Project page. Figures come from a committed run of ${code(payload.meta.command)}; this page does not run the harness.</p>
    </div>`,
  );
}
