const AVATAR_COLORS = ["#F0B429", "#CE3F36", "#3FB8AF", "#F2705B", "#9B6BD3", "#7BB661"];

function avatarColorFor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function renderAvatar(el, name) {
  if (!el) return;
  const label = (name || "?").trim().charAt(0).toUpperCase() || "?";
  el.textContent = label;
  el.style.background = avatarColorFor(name || "?");
}
