let art = "";
let downloadName = "ascii.txt";

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

export function setArt(els, text, filename) {
  art = text;
  const stem = filename.replace(/\.[^.]+$/, "") || "ascii";
  downloadName = `${stem}.txt`;
  const ready = text.length > 0;
  els.copy.disabled = !ready;
  els.download.disabled = !ready;
  els.save.disabled = !ready;
}
