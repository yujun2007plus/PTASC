export const PRESETS = {
  simple: " .:-=+#",
  standard: " .:-=+*#%@",
  detailed: " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
  blocks: " ░▒▓█",
  steps: " ▁▂▃▄▅▆▇█",
  braille: " ⠁⠈⠠⠃⠉⠌⠔⠢⠨⡂⡐⢁⢈⣀⠋⠓⠙⠜⠦⠬⠲⡃⡉⡌⡔⡢⡰⢅⢊⢒⢘⢤⣁⣄⣠⠛⠞⠭⠵⠹⡇⡎⡕⡚⡥⡩⡱⡸⢋⢓⢙⢜⢦⢬⢲⣃⣉⣌⣔⣢⣨⠯⠽⡏⡝⡫⡮⡶⡼⢗⢞⢭⢵⢹⣇⣎⣕⣚⣥⣩⣱⣸⡟⡻⢟⢷⢾⣛⣞⣭⣵⣹⡿⣯⣻⣿",
};

export function syncRange(input) {
  input.style.setProperty("--attr-min", input.min || "0");
  input.style.setProperty("--attr-max", input.max || "100");
  input.style.setProperty("--control-value", input.value);
  if (input.dataset.unit) {
    input.setAttribute("aria-valuetext", `${input.value} ${input.dataset.unit}`);
  }
}

export function bindControls(els, settings, onChange) {
  const match = Object.entries(PRESETS).find(([, ramp]) => ramp === settings.ramp);
  setCharset(els, match ? match[0] : "custom");
  els.ramp.value = settings.ramp;
  els.columns.value = String(clampColumns(settings.columns));
  els.columnsValue.textContent = els.columns.value;
  syncRange(els.columns);
  els.invert.checked = settings.invert;

  els.columns.addEventListener("input", () => {
    els.columnsValue.textContent = els.columns.value;
    syncRange(els.columns);
    onChange();
  });
  els.charset.addEventListener("change", () => {
    if (els.charset.value !== "custom") {
      els.ramp.value = PRESETS[els.charset.value];
    }
    onChange();
  });
  els.ramp.addEventListener("input", () => {
    const found = Object.entries(PRESETS).find(([, ramp]) => ramp === els.ramp.value);
    setCharset(els, found ? found[0] : "custom");
    onChange();
  });
  els.invert.addEventListener("change", onChange);
}

export function readControls(els) {
  return {
    columns: Number(els.columns.value),
    ramp: els.ramp.value,
    invert: els.invert.checked,
  };
}

function setCharset(els, value) {
  els.charset.value = value;
  els.charset.dispatchEvent(new Event("charset-sync"));
}

function clampColumns(value) {
  return Math.min(200, Math.max(20, Number(value) || 80));
}
