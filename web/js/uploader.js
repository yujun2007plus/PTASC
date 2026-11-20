const IMAGE_NAME = /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i;
const VIDEO_NAME = /\.(mp4|webm|mov|mkv|avi|m4v|gif)$/i;

export function bindUploader(els, handlers) {
  const zone = els.dropzone;
  let thumbUrl = "";
  let clipUrl = "";

  function isGif(file) {
    return file.type === "image/gif" || /\.gif$/i.test(file.name);
  }

  function isImage(file) {
    return file.type.startsWith("image/") || IMAGE_NAME.test(file.name);
  }

  function isVideo(file) {
    return file.type.startsWith("video/") || VIDEO_NAME.test(file.name);
  }

  function revoke(url) {
    if (url) {
      URL.revokeObjectURL(url);
    }
  }

  function reset() {
    revoke(thumbUrl);
    revoke(clipUrl);
    thumbUrl = "";
    clipUrl = "";
    els.clip.pause();
    els.thumb.removeAttribute("src");
    els.clip.removeAttribute("src");
    els.thumb.hidden = true;
    els.clip.hidden = true;
  }

  function showStill(file) {
    reset();
    thumbUrl = URL.createObjectURL(file);
    els.thumb.hidden = false;
    els.thumb.src = thumbUrl;
  }

  function showClip(file) {
    reset();
    clipUrl = URL.createObjectURL(file);
    els.clip.hidden = false;
    els.clip.src = clipUrl;
    void els.clip.play().catch(() => {});
  }

  function accept(file) {
    const videoMode = handlers.mode() === "video";
    if (videoMode && !isVideo(file)) {
      els.status.textContent = "请选择视频文件";
      return;
    }
    if (!videoMode && !isImage(file)) {
      els.status.textContent = "请选择图片文件";
      return;
    }
    if (!videoMode || isGif(file)) {
      showStill(file);
    } else {
      showClip(file);
    }
    els.dropLabel.textContent = file.name || (videoMode ? "未命名视频" : "未命名图片");
    handlers.onFile(file);
  }

  els.fileInput.addEventListener("change", () => {
    const file = els.fileInput.files && els.fileInput.files[0];
    if (file) {
      accept(file);
    }
  });
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (file) {
      accept(file);
    }
  });
  window.addEventListener("paste", (event) => {
    const file = event.clipboardData && event.clipboardData.files[0];
    if (file) {
      accept(file);
    }
  });
  els.sample.addEventListener("click", async () => {
    const videoMode = handlers.mode() === "video";
    const path = videoMode ? "/samples/sample.gif" : "/samples/sample.png";
    const response = await fetch(path);
    if (!response.ok) {
      els.status.textContent = videoMode ? "示例视频加载失败" : "示例图片加载失败";
      return;
    }
    const blob = await response.blob();
    const name = videoMode ? "sample.gif" : "sample.png";
    const type = blob.type || (videoMode ? "image/gif" : "image/png");
    accept(new File([blob], name, { type }));
  });

  return {
    reset,
    present(file) {
      accept(file);
    },
  };
}
