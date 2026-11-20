import { bindCharsetMenu } from "./charset-menu.js";
import { bindControls, syncRange } from "./controls.js";
import { bindExport } from "./export.js";
import { setFontSize, showPlaceholder } from "./preview.js";
import { startSession } from "./session.js";
import { bindUploader } from "./uploader.js";

const els = {
  dropzone: document.querySelector("#dropzone"),
  dropLabel: document.querySelector("#drop-label"),
  fileInput: document.querySelector("#file-input"),
  thumb: document.querySelector("#thumb"),
  sample: document.querySelector("#sample"),
  columns: document.querySelector("#columns"),
  columnsValue: document.querySelector("#columns-value"),
  charset: document.querySelector("#charset"),
  ramp: document.querySelector("#ramp"),
  invert: document.querySelector("#invert"),
  fontSize: document.querySelector("#font-size"),
  ascii: document.querySelector("#ascii"),
  status: document.querySelector("#status"),
  copy: document.querySelector("#copy"),
  download: document.querySelector("#download"),
  save: document.querySelector("#save"),
  form: document.querySelector("#controls"),
  fontSizeValue: document.querySelector("#font-size-value"),
  plate: document.querySelector(".plate"),
};

const session = startSession(els);
bindCharsetMenu(els);
bindExport(els);
showPlaceholder(els.ascii);
applyFontSize();
els.fontSize.addEventListener("input", applyFontSize);

const settingsResponse = await fetch("/api/settings");
if (!settingsResponse.ok) {
  els.status.textContent = "读不到默认参数";
} else {
  bindControls(els, await settingsResponse.json(), session.scheduleConvert);
}

bindUploader(els, session.onFile);

function applyFontSize() {
  setFontSize(els.ascii, els.fontSize.value);
  els.fontSizeValue.textContent = els.fontSize.value;
  syncRange(els.fontSize);
}
