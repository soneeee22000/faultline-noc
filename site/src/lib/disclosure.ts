import { closestTarget } from "./dom";

const DISCLOSE_SELECTOR = "[data-disclose]";

/** Toggle one disclosure button and the region it controls. */
function toggle(button: HTMLElement): void {
  const region = document.getElementById(
    button.getAttribute("aria-controls") ?? "",
  );
  if (region === null) return;
  const expanded = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", String(expanded));
  region.hidden = !expanded;
  const label = expanded
    ? button.dataset.labelOpen
    : button.dataset.labelClosed;
  const text = button.querySelector("[data-disclose-text]");
  if (label !== undefined && text !== null) text.textContent = label;
}

/** Wire every `[data-disclose]` button under a root to show and hide its controlled region. */
export function bindDisclosures(root: HTMLElement): void {
  root.addEventListener("click", (event) => {
    const button = closestTarget(event, DISCLOSE_SELECTOR);
    if (button !== null) toggle(button);
  });
}

/** Markup for a disclosure button whose label flips between two texts. */
export function disclosureButton(
  controls: string,
  closedLabel: string,
  openLabel: string,
): string {
  return `<button type="button" class="button button--quiet" data-disclose aria-expanded="false" aria-controls="${controls}" data-label-closed="${closedLabel}" data-label-open="${openLabel}"><span data-disclose-text>${closedLabel}</span></button>`;
}
