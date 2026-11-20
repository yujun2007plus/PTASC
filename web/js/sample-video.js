function waitFor(video, eventName) {
  if (eventName === "loadedmetadata" && video.readyState >= 1) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => finish(new Error("无法读取视频")), 8000);
    function finish(error) {
      window.clearTimeout(timer);
      video.removeEventListener(eventName, onReady);
      video.removeEventListener("error", onError);
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    }
    function onReady() {
      finish();
    }
    function onError() {
      finish(new Error("无法读取视频"));
    }
    video.addEventListener(eventName, onReady);
    video.addEventListener("error", onError);
  });
}

function seekTo(video, time) {
  const duration = Number.isFinite(video.duration) ? video.duration : time;
  const target = Math.min(Math.max(time, 0), Math.max(0, duration - 0.04));
  if (Math.abs(video.currentTime - target) < 0.03) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => finish(), 1500);
    function finish(error) {
      window.clearTimeout(timer);
      video.removeEventListener("seeked", onSeeked);
      video.removeEventListener("error", onError);
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    }
    function onSeeked() {
      finish();
    }
    function onError() {
      finish(new Error("无法读取视频画面"));
    }
    video.addEventListener("seeked", onSeeked);
    video.addEventListener("error", onError);
    video.currentTime = target;
  });
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

export async function sampleVideo(file, limits, onProgress, cancelled) {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";
  video.src = url;
  try {
    await waitFor(video, "loadedmetadata");
    const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : limits.maxSeconds;
    const span = Math.min(duration, limits.maxSeconds);
    const times = [];
    for (let time = 0; time < span && times.length < limits.maxFrames; time += 1 / limits.fps) {
      times.push(time);
    }
    if (!times.length) {
      times.push(0);
    }
    const width = video.videoWidth || limits.maxEdge;
    const height = video.videoHeight || limits.maxEdge;
    const scale = Math.min(1, limits.maxEdge / Math.max(width, height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(2, Math.round(width * scale));
    canvas.height = Math.max(2, Math.round(height * scale));
    const context = canvas.getContext("2d", { alpha: false });
    const frames = [];
    for (let index = 0; index < times.length; index += 1) {
      if (cancelled()) {
        return null;
      }
      await seekTo(video, times[index]);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.72));
      if (!blob) {
        throw new Error("无法读取视频画面");
      }
      frames.push(await blobToBase64(blob));
      onProgress(index + 1, times.length);
    }
    return { frames, fps: Math.min(limits.fps, frames.length / Math.max(span, 1 / limits.fps)) };
  } finally {
    URL.revokeObjectURL(url);
    video.removeAttribute("src");
    video.load();
  }
}
