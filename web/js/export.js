let art = "";
let downloadName = "ascii.txt";
let videoBlob = null;
let videoUrl = "";

function revokeVideo() {
  if (videoUrl) {
    URL.revokeObjectURL(videoUrl);
    videoUrl = "";
  }
  videoBlob = null;
}

export function bindExport(els) {
  els.copy.addEventListener("click", async () => {
    if (!art) {
      return;
    }
    try {
      await navigator.clipboard.writeText(art);
      els.status.textContent = "已复制";
    } catch {
      els.status.textContent = "复制失败，请从预览里手动选择";
    }
  });
  els.download.addEventListener("click", () => {
    if (videoBlob && videoUrl) {
      const link = document.createElement("a");
      link.href = videoUrl;
      link.download = downloadName;
      link.click();
      return;
    }
    if (!art) {
      return;
    }
    const blob = new Blob([art], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = downloadName;
    link.click();
    URL.revokeObjectURL(link.href);
  });
}

export function clearArt(els) {
  art = "";
  downloadName = "ascii.txt";
  revokeVideo();
  els.copy.disabled = true;
  els.download.disabled = true;
  els.save.disabled = true;
}

export function clearDownloadFile(els) {
  revokeVideo();
  els.download.disabled = true;
}

export function setDownloadFile(els, blob, filename) {
  revokeVideo();
  videoBlob = blob;
  videoUrl = URL.createObjectURL(blob);
  downloadName = filename;
  els.download.disabled = false;
}

export function setArt(els, text, filename, enableDownload = true) {
  art = text;
  const ready = text.length > 0;
  if (enableDownload) {
    const stem = filename.replace(/\.[^.]+$/, "") || "ascii";
    downloadName = `${stem}.txt`;
    els.download.disabled = !ready;
  }
  els.copy.disabled = !ready;
  els.save.disabled = !ready;
}
