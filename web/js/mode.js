const COPY = {
  image: {
    title: "图片转字符画",
    label: "拖入图片，或点击选择",
    hint: "也可以直接粘贴截图",
    sample: "使用示例图片",
    accept: ".png,.jpg,.jpeg,.gif,.webp,.bmp,.tif,.tiff",
    status: "先放入一张图片",
  },
  video: {
    title: "视频转字符画",
    label: "拖入视频，或点击选择",
    hint: "先预览前面一段，再转换完整视频",
    sample: "使用示例视频",
    accept: ".mp4,.webm,.mov,.mkv,.avi,.m4v,.gif",
    status: "先放入一个视频",
  },
};

export function bindMode(els, onChange) {
  let mode = "image";

  function apply(next) {
    mode = next;
    const copy = COPY[mode];
    els.modeImage.setAttribute("aria-pressed", mode === "image" ? "true" : "false");
    els.modeVideo.setAttribute("aria-pressed", mode === "video" ? "true" : "false");
    els.pageTitle.textContent = copy.title;
    document.title = copy.title;
    els.dropLabel.textContent = copy.label;
    els.dropHint.textContent = copy.hint;
    els.sample.textContent = copy.sample;
    els.download.textContent = mode === "video" ? "下载 MP4" : "下载 TXT";
    els.full.hidden = mode !== "video";
    els.fileInput.accept = copy.accept;
    els.fileInput.value = "";
    onChange(mode, copy.status);
  }

  els.modeImage.addEventListener("click", () => {
    if (mode !== "image") {
      apply("image");
    }
  });
  els.modeVideo.addEventListener("click", () => {
    if (mode !== "video") {
      apply("video");
    }
  });

  function select(next) {
    if (next === "image" || next === "video") {
      apply(next);
    }
  }

  return { mode: () => mode, select };
}
