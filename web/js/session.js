import { readControls } from "./controls.js";
import { fileToBase64 } from "./encode.js";
import { setArt } from "./export.js";
import { setBusy } from "./motion.js";
import { revealPreview } from "./preview.js";

export function startSession(els) {
  let currentFile = null;
  let timer = 0;
  let requestSerial = 0;

  els.save.addEventListener("click", () => {
    void saveCurrent();
  });
  els.form.addEventListener("submit", (event) => event.preventDefault());

  function scheduleConvert() {
    window.clearTimeout(timer);
    if (!currentFile) {
      return;
    }
    timer = window.setTimeout(() => {
      void convertCurrent();
    }, 200);
  }

  function onFile(file) {
    currentFile = file;
    scheduleConvert();
  }

  async function postImage(path, options) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFile.name,
        image_base64: await fileToBase64(currentFile),
        columns: options.columns,
        ramp: options.ramp,
        invert: options.invert,
      }),
    });
    const payload = await response.json();
    return { response, payload };
  }

  async function convertCurrent() {
    if (!currentFile) {
      return;
    }
    const serial = ++requestSerial;
    const options = readControls(els);
    if (!options.ramp) {
      els.status.textContent = "字符坡道不能为空";
      return;
    }
    els.status.textContent = "正在转换…";
    els.save.disabled = true;
    setBusy(els.plate, true);
    const { response, payload } = await postImage("/api/convert", options);
    if (serial !== requestSerial) {
      return;
    }
    setBusy(els.plate, false);
    if (!response.ok) {
      els.status.textContent = payload.error || "转换失败";
      els.save.disabled = els.copy.disabled;
      return;
    }
    revealPreview(els.ascii, payload.ascii, options.invert);
    setArt(els, payload.ascii, currentFile.name);
    els.status.textContent = `${payload.columns} × ${payload.rows} 字符`;
    els.status.title = "";
  }

  async function saveCurrent() {
    if (!currentFile || els.save.disabled) {
      return;
    }
    const serial = requestSerial;
    const options = readControls(els);
    els.save.disabled = true;
    setBusy(els.plate, true);
    els.status.textContent = "正在保存…";
    const { response, payload } = await postImage("/api/save", options);
    if (serial !== requestSerial) {
      return;
    }
    setBusy(els.plate, false);
    els.save.disabled = false;
    if (!response.ok) {
      els.status.textContent = payload.error || "保存失败";
      return;
    }
    els.status.textContent = `${payload.columns} × ${payload.rows} 字符，已保存`;
    els.status.title = payload.task_id;
  }

  return { onFile, scheduleConvert };
}
