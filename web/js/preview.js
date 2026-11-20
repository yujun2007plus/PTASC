function applyTheme(asciiNode, invert) {
  asciiNode.classList.toggle("light", !invert);
  asciiNode.classList.toggle("dark", invert);
}

function placeArt(asciiNode) {
  asciiNode.classList.remove("is-placeholder");
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
  placeArt(asciiNode);
}

export function showArt(asciiNode, art, invert) {
  applyTheme(asciiNode, invert);
  asciiNode.replaceChildren();
  asciiNode.textContent = art.endsWith("\n") ? art.slice(0, -1) : art;
  placeArt(asciiNode);
}

export function setFontSize(asciiNode, size) {
  asciiNode.style.fontSize = `${size}px`;
}

export function showPlaceholder(asciiNode) {
  const size = asciiNode.style.fontSize;
  asciiNode.replaceChildren();
  asciiNode.textContent = "字符画会显示在这里";
  asciiNode.classList.add("light", "is-placeholder");
  asciiNode.classList.remove("dark");
  if (size) {
    asciiNode.style.fontSize = size;
  }
}
