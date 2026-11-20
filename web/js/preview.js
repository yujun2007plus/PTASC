function applyTheme(asciiNode, invert) {
  asciiNode.classList.toggle("light", !invert);
  asciiNode.classList.toggle("dark", invert);
}

export function revealPreview(asciiNode, art, invert) {
  applyTheme(asciiNode, invert);
  const lines = art.endsWith("\n") ? art.slice(0, -1).split("\n") : art.split("\n");
  asciiNode.replaceChildren();
  lines.forEach((line, index) => {
    const row = document.createElement("span");
    row.className = "ascii-row";
    row.textContent = line;
    row.style.animationDelay = `${index * 16}ms`;
    asciiNode.append(row);
  });
}

export function setFontSize(asciiNode, size) {
  asciiNode.style.fontSize = `${size}px`;
}

export function showPlaceholder(asciiNode) {
  asciiNode.replaceChildren();
  asciiNode.textContent = "字符画会显示在这里";
  asciiNode.classList.add("light");
  asciiNode.classList.remove("dark");
}
