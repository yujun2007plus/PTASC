import { PRESETS } from "./controls.js";

export function bindCharsetMenu(els) {
  const select = els.charset;
  const root = select.closest(".charset-picker");
  const button = root.querySelector("#charset-button");
  const list = root.querySelector("#charset-list");
  const nameEl = button.querySelector("[data-charset-name]");
  const sampleEl = button.querySelector("[data-charset-sample]");
  const options = [...select.options].map((option) => {
    const item = document.createElement("li");
    item.setAttribute("role", "option");
    item.tabIndex = -1;
    item.dataset.value = option.value;
    const name = document.createElement("span");
    name.textContent = option.textContent;
    const sample = document.createElement("span");
    sample.className = "charset-sample";
    item.append(name, sample);
    item.addEventListener("click", () => choose(option.value));
    list.append(item);
    return item;
  });

  function sampleFor(value) {
    if (value === "custom") {
      return els.ramp.value;
    }
    return PRESETS[value] || "";
  }

  function paint() {
    const value = select.value;
    const selected = select.selectedOptions[0];
    nameEl.textContent = selected ? selected.textContent : "";
    sampleEl.textContent = sampleFor(value);
    for (const item of options) {
      const on = item.dataset.value === value;
      item.setAttribute("aria-selected", on ? "true" : "false");
      item.querySelector(".charset-sample").textContent = sampleFor(item.dataset.value);
    }
  }

  function choose(value) {
    select.value = value;
    select.dispatchEvent(new Event("change"));
    close();
    button.focus();
  }

  function open() {
    paint();
    list.hidden = false;
    button.setAttribute("aria-expanded", "true");
  }

  function close() {
    list.hidden = true;
    button.setAttribute("aria-expanded", "false");
  }

  button.addEventListener("click", () => {
    if (list.hidden) {
      open();
    } else {
      close();
    }
  });
  button.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
      return;
    }
    event.preventDefault();
    open();
    focusValue(select.value);
  });
  list.addEventListener("keydown", (event) => {
    const index = options.findIndex((item) => item === document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      button.focus();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = event.key === "ArrowDown" ? index + 1 : index - 1;
      options[Math.min(options.length - 1, Math.max(0, next))]?.focus();
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (options[index]) {
        choose(options[index].dataset.value);
      }
    }
  });
  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) {
      close();
    }
  });
  select.addEventListener("change", paint);
  select.addEventListener("charset-sync", paint);
  paint();

  function focusValue(value) {
    (options.find((item) => item.dataset.value === value) || options[0]).focus();
  }
}
