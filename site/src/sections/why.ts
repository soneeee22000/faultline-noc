import { WHY_BLOCKS } from "../content/why";
import { mount, richText } from "../lib/dom";

/** Section 3: the business context in four fixed blocks. */
export function renderWhy(): void {
  const blocks = WHY_BLOCKS.map(
    (block) =>
      `<div class="why__block"><h3>${block.heading}</h3>${block.paragraphs.map((paragraph) => `<p>${richText(paragraph)}</p>`).join("")}</div>`,
  ).join("");
  mount(
    "why",
    `<div class="container why">
      <div class="why__head"><h2 id="why-title">Why it matters</h2></div>
      <div class="why__blocks">${blocks}</div>
    </div>`,
  );
}
