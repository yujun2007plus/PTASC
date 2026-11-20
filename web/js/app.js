import { bindCharsetMenu } from "./charset-menu.js";
import { bindControls, syncRange } from "./controls.js";
import { bindExport, clearArt } from "./export.js";
import { loadMedia, loadMode, saveMedia, saveMode } from "./media-cache.js";
import { bindMode } from "./mode.js";
import { setBusy } from "./motion.js";
import { setFontSize, showPlaceholder } from "./preview.js";
import { startSession } from "./session.js";
import { bindUploader } from "./uploader.js";
import { startVideoSession } from "./video-session.js";

const els = {
  pageTitle: document.querySelector("#page-title"),
  modeImage: document.querySelector("#mode-image"),
  modeVideo: document.querySelector("#mode-video"),
  dropzone: document.querySelector("#dropzone"),
  dropLabel: document.querySelector("#drop-label"),
  dropHint: document.querySelector("#drop-hint"),
  fileInput: document.querySelector("#file-input"),
  thumb: document.querySelector("#thumb"),
  clip: document.querySelector("#clip"),
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
  full: document.querySelector("#full"),
  save: document.querySelector("#save"),
  result: document.querySelector("#result"),
  form: document.querySelector("#controls"),
  fontSizeValue: document.querySelector("#font-size-value"),
  plate: document.querySelector(".plate"),
};

const session = startSession(els);
const videoSession = startVideoSession(els);
const remembered = { image: null, video: null };
const modes = bindMode(els, switchMode);
bindCharsetMenu(els);
bindExport(els);
showPlaceholder(els.ascii);
applyFontSize();
els.fontSize.addEventListener("input", applyFontSize);
els.full.addEventListener("click", () => {
  if (modes.mode() === "video") {
    void videoSession.convertFull();
  }
});
els.save.addEventListener("click", () => {
  if (modes.mode() === "video") {
    void videoSession.save();
  } else {
    void session.save();
  }
});

const settingsResponse = await fetch("/api/settings");
const cachedMedia = Promise.all([loadMedia("image"), loadMedia("video")]);
if (!settingsResponse.ok) {
  els.status.textContent = "读不到默认参数";
} else {
  const settings = await settingsResponse.json();
  videoSession.configure(settings);
  bindControls(els, settings, () => {
    if (modes.mode() === "video") {
      videoSession.scheduleConvert();
    } else {
      session.scheduleConvert();
    }
  });
}

const uploader = bindUploader(els, {
  mode: () => modes.mode(),
  onFile(file) {
    const mode = modes.mode();
    remembered[mode] = file;
    void saveMedia(mode, file);
    if (mode === "video") {
      session.clear();
      videoSession.onFile(file);
    } else {
      videoSession.clear();
      session.onFile(file);
    }
  },
});

const [cachedImage, cachedVideo] = await cachedMedia;
remembered.image = cachedImage;
remembered.video = cachedVideo;
modes.select(loadMode());

function switchMode(mode, status) {
  saveMode(mode);
  session.clear();
  videoSession.clear();
  clearArt(els);
  showPlaceholder(els.ascii);
  setBusy(els.plate, false);
  const file = remembered[mode];
  if (file) {
    uploader.present(file);
    return;
  }
  uploader.reset();
  els.status.textContent = status;
  els.status.title = "";
}

function applyFontSize() {
  setFontSize(els.ascii, els.fontSize.value);
  els.fontSizeValue.textContent = els.fontSize.value;
  syncRange(els.fontSize);
}
