export const $ = (sel, root = document) => root.querySelector(sel);
export const byId = (id) => document.getElementById(id);

export function setText(el, text) {
  if (el) el.textContent = text;
}

export function show(el) {
  if (el) el.classList.remove("hidden");
}

export function hide(el) {
  if (el) el.classList.add("hidden");
}