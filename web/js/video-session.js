import { readControls } from "./controls.js";
import { fileToBase64 } from "./encode.js";
import { clearDownloadFile, setArt, setDownloadFile } from "./export.js";
import { setBusy } from "./motion.js";
import { showArt } from "./preview.js";
import { sampleVideo } from "./sample-video.js";

const FRAME_BREAK = "\n\f\n";
const SMALL_FILE = 8 * 1024 * 1024;
const FIRST_MS = 60;
const QUIET_MS = 450;

export function startVideoSession(els) {
  let currentFile = null;
  let timer = 0;
  let playTimer = 0;
  let requestSerial = 0;
  let packet = null;
  let previewId = "";
  let renderedKey = "";
  let inflight = false;
  let again = false;
  let timerPending = false;
  let fullTicket = 0;
  let fullController = null;
  let renderId = "";
  let resultUrl = "";
  let limits = { fps: 8, maxFrames: 120, maxSeconds: 15, maxEdge: 480 };

  function configure(settings) {
    limits = {
      fps: Number(settings.video_fps) || limits.fps,
      maxFrames: Number(settings.video_max_frames) || limits.maxFrames,
      maxSeconds: Number(settings.video_max_seconds) || limits.maxSeconds,
      maxEdge: Number(settings.video_max_edge) || limits.maxEdge,
    };
  }

  function scheduleConvert() {
    dropFull();
    window.clearTimeout(timer);
    if (!currentFile) {
      timerPending = false;
      return;
    }
    timerPending = true;
    const wait = previewId ? QUIET_MS : FIRST_MS;
    timer = window.setTimeout(() => {
      timerPending = false;
      void convertCurrent();
    }, wait);
  }

  function onFile(file) {
    currentFile = file;
    packet = null;
    previewId = "";
    renderedKey = "";
    els.full.disabled = true;
    scheduleConvert();
  }

  function clear() {
    currentFile = null;
    packet = null;
    previewId = "";
    renderedKey = "";
    again = false;
    requestSerial += 1;
    window.clearTimeout(timer);
    timerPending = false;
    els.full.disabled = true;
    dropFull();
    stop();
  }

  function dropFull() {
    fullTicket += 1;
    if (fullController) {
      fullController.abort();
      fullController = null;
    }
    renderId = "";
    hideResult();
    clearDownloadFile(els);
  }

  function hideResult() {
    if (els.result) {
      els.result.pause();
      els.result.removeAttribute("src");
      els.result.load();
      els.result.hidden = true;
    }
    if (resultUrl) {
      URL.revokeObjectURL(resultUrl);
      resultUrl = "";
    }
    els.ascii.hidden = false;
  }

  function showResult(blob) {
    stop();
    hideResult();
    resultUrl = URL.createObjectURL(blob);
    els.result.src = resultUrl;
    els.result.hidden = false;
    els.ascii.hidden = true;
  }

  function stop() {
    window.clearInterval(playTimer);
    playTimer = 0;
  }

  function play(frames, fps, invert) {
    stop();
    let index = 0;
    const step = () => {
      showArt(els.ascii, frames[index], invert);
      index = (index + 1) % frames.length;
    };
    step();
    if (frames.length > 1) {
      playTimer = window.setInterval(step, 1000 / Math.max(fps, 1));
    }
  }

  async function ensurePacket(serial) {
    if (packet && packet.file === currentFile) {
      return packet;
    }
    els.status.textContent = "正在抽取画面…";
    try {
      const sampled = await sampleVideo(
        currentFile,
        limits,
        (done, total) => {
          if (serial === requestSerial) {
            els.status.textContent = `正在抽取画面 ${done}/${total}`;
          }
        },
        () => serial !== requestSerial,
      );
      if (serial !== requestSerial || !sampled) {
        return null;
      }
      packet = { file: currentFile, frames: sampled.frames, fps: sampled.fps, fallback: false };
      return packet;
    } catch (error) {
      if (serial !== requestSerial) {
        return null;
      }
      if (currentFile.size <= SMALL_FILE) {
        packet = { file: currentFile, fallback: true };
        return packet;
      }
      throw error;
    }
  }

  function optionKey(options) {
    return `${options.columns}\n${options.ramp}\n${options.invert ? 1 : 0}`;
  }

  async function postVideo(path, options, serial, allowRetry) {
    const body = {
      filename: currentFile.name,
      columns: options.columns,
      ramp: options.ramp,
      invert: options.invert,
    };
    if (previewId) {
      body.preview_id = previewId;
      body.fps = packet && packet.fps ? packet.fps : limits.fps;
    } else {
      const ready = await ensurePacket(serial);
      if (!ready) {
        return null;
      }
      if (ready.fallback) {
        body.video_base64 = await fileToBase64(currentFile);
      } else {
        body.frames_base64 = ready.frames;
        body.fps = ready.fps;
      }
    }
    const saving = path.endsWith("save-video");
    if (serial === requestSerial && (saving || !previewId)) {
      els.status.textContent = saving ? "正在保存…" : "正在转换…";
    }
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (serial !== requestSerial) {
      return { response, payload };
    }
    if (!response.ok && allowRetry && previewId && String(payload.error || "").includes("过期")) {
      previewId = "";
      return postVideo(path, options, serial, false);
    }
    if (response.ok && payload.preview_id) {
      previewId = payload.preview_id;
      if (packet) {
        packet.fps = payload.fps;
      }
    }
    return { response, payload };
  }

  async function convertCurrent() {
    if (!currentFile) {
      return;
    }
    if (inflight) {
      again = true;
      return;
    }
    const options = readControls(els);
    if (!options.ramp) {
      els.status.textContent = "字符坡道不能为空";
      return;
    }
    const key = optionKey(options);
    if (previewId && key === renderedKey) {
      return;
    }
    const serial = ++requestSerial;
    const firstLook = !previewId;
    inflight = true;
    if (firstLook) {
      els.save.disabled = true;
      setBusy(els.plate, true);
    }
    let posted;
    try {
      posted = await postVideo("/api/convert-video", options, serial, true);
      if (!posted || serial !== requestSerial || again || timerPending) {
        return;
      }
      const { response, payload } = posted;
      if (!response.ok) {
        if (firstLook) {
          stop();
          els.save.disabled = els.copy.disabled;
        }
        els.status.textContent = payload.error || "转换失败";
        return;
      }
      const frames = payload.frames || [];
      const joined = frames.map((frame) => frame.replace(/\n$/, "")).join(FRAME_BREAK);
      play(frames, payload.fps, options.invert);
      setArt(els, joined.length ? `${joined}\n` : "", currentFile.name, false);
      renderedKey = key;
      els.full.disabled = false;
      els.status.textContent = `${payload.columns} × ${payload.rows} 字符，${payload.frame_count} 帧预览`;
      els.status.title = "";
    } catch {
      if (serial !== requestSerial) {
        return;
      }
      els.status.textContent = "无法读取这段视频";
    } finally {
      if (firstLook && serial === requestSerial) {
        setBusy(els.plate, false);
      }
      inflight = false;
      if (again && !timerPending) {
        again = false;
        scheduleConvert();
      } else {
        again = false;
      }
    }
  }

  async function saveCurrent() {
    if (!currentFile || els.save.disabled) {
      return;
    }
    const serial = requestSerial;
    const options = readControls(els);
    const savedRender = renderId;
    els.save.disabled = true;
    setBusy(els.plate, true);
    let posted;
    try {
      posted = savedRender
        ? await postRender(options, savedRender)
        : await postVideo("/api/save-video", options, serial, true);
    } catch {
      if (!currentFile) {
        return;
      }
      setBusy(els.plate, false);
      els.save.disabled = false;
      els.status.textContent = "无法读取这段视频";
      return;
    }
    if (!currentFile) {
      return;
    }
    setBusy(els.plate, false);
    els.save.disabled = false;
    if (!posted) {
      return;
    }
    const { response, payload } = posted;
    if (!response.ok) {
      els.status.textContent = payload.error || "保存失败";
      return;
    }
    const detail = savedRender
      ? "完整视频，已保存"
      : `${payload.columns} × ${payload.rows} 字符，${payload.frame_count} 帧预览，已保存`;
    els.status.textContent = detail;
    els.status.title = payload.task_id;
  }

  async function postRender(options, token) {
    const response = await fetch("/api/save-video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFile.name,
        columns: options.columns,
        ramp: options.ramp,
        invert: options.invert,
        render_id: token,
      }),
    });
    const payload = await response.json();
    return { response, payload };
  }

  async function convertFull() {
    if (!currentFile || els.full.disabled) {
      return;
    }
    const options = readControls(els);
    if (!options.ramp) {
      els.status.textContent = "字符坡道不能为空";
      return;
    }
    const ticket = fullTicket;
    const controller = new AbortController();
    fullController = controller;
    els.full.disabled = true;
    els.status.textContent = "正在转换完整视频…";
    try {
      const response = await fetch("/api/full-video", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Ptasc-Filename": encodeURIComponent(currentFile.name),
          "X-Ptasc-Columns": String(options.columns),
          "X-Ptasc-Ramp": encodeURIComponent(options.ramp),
          "X-Ptasc-Invert": options.invert ? "true" : "false",
        },
        body: currentFile,
        signal: controller.signal,
      });
      if (ticket !== fullTicket) {
        return;
      }
      if (!response.ok) {
        let message = "完整转换失败";
        try {
          const payload = await response.json();
          message = payload.error || message;
        } catch {
          message = "完整转换失败";
        }
        els.status.textContent = message;
        return;
      }
      const blob = await response.blob();
      if (ticket !== fullTicket) {
        return;
      }
      renderId = response.headers.get("X-Render-Id") || "";
      const columns = response.headers.get("X-Columns") || options.columns;
      const rows = response.headers.get("X-Rows") || "";
      const audio = response.headers.get("X-Audio") === "1";
      showResult(blob);
      const stem = currentFile.name.replace(/\.[^.]+$/, "") || "ascii";
      setDownloadFile(els, blob, `${stem}.mp4`);
      els.status.textContent = `${columns} × ${rows} 字符，完整视频${audio ? "，含声音" : ""}`;
      els.status.title = "";
    } catch (error) {
      if (error.name === "AbortError" || ticket !== fullTicket) {
        return;
      }
      els.status.textContent = "完整转换失败";
    } finally {
      if (ticket === fullTicket) {
        fullController = null;
        els.full.disabled = !currentFile;
      }
    }
  }

  return { onFile, scheduleConvert, save: saveCurrent, convertFull, clear, configure };
}
