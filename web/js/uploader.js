export function bindUploader(els, onFile) {
  const zone = els.dropzone;
  let thumbUrl = "";

  function accept(file) {
    if (!file.type.startsWith("image/")) {
      els.status.textContent = "请选择图片文件";
      return;
    }
    if (thumbUrl) {
      URL.revokeObjectURL(thumbUrl);
    }
    thumbUrl = URL.createObjectURL(file);
    els.thumb.src = thumbUrl;
    els.thumb.hidden = false;
    els.dropLabel.textContent = file.name;
    onFile(file);
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
    const response = await fetch("/samples/sample.png");
    if (!response.ok) {
      els.status.textContent = "示例图片加载失败";
      return;
    }
    const blob = await response.blob();
    accept(new File([blob], "sample.png", { type: blob.type || "image/png" }));
  });
}
