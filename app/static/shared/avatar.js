const AVATAR_COLORS = ["#F0745B", "#3FB8AF", "#9B6BD3", "#7BB661", "#E08A34", "#E0699B"];
const AVATAR_SHAPES = ["circle", "squircle", "blob"];

const AVATAR_FACES = {
  happy: `
    <svg viewBox="0 0 100 100" class="avatar__face" aria-hidden="true">
      <ellipse cx="35" cy="42" rx="6" ry="8" fill="#1c1410"/>
      <ellipse cx="65" cy="42" rx="6" ry="8" fill="#1c1410"/>
      <path d="M32 60 Q50 76 68 60" stroke="#1c1410" stroke-width="6" fill="none" stroke-linecap="round"/>
    </svg>
  `,
  worried: `
    <svg viewBox="0 0 100 100" class="avatar__face" aria-hidden="true">
      <line x1="23" y1="30" x2="39" y2="36" stroke="#1c1410" stroke-width="5" stroke-linecap="round"/>
      <line x1="77" y1="30" x2="61" y2="36" stroke="#1c1410" stroke-width="5" stroke-linecap="round"/>
      <circle cx="35" cy="49" r="9" fill="#fff" stroke="#1c1410" stroke-width="3"/>
      <circle cx="65" cy="49" r="9" fill="#fff" stroke="#1c1410" stroke-width="3"/>
      <circle cx="35" cy="49" r="3.5" fill="#1c1410"/>
      <circle cx="65" cy="49" r="3.5" fill="#1c1410"/>
      <path d="M30 68 Q38 62 46 68 T62 68 T70 68" stroke="#1c1410" stroke-width="5" fill="none" stroke-linecap="round"/>
    </svg>
  `,
};

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = (hash * 31 + str.charCodeAt(i)) >>> 0;
  return hash;
}

function avatarColorFor(name) {
  return AVATAR_COLORS[hashString(name) % AVATAR_COLORS.length];
}

function avatarShapeFor(name) {
  return AVATAR_SHAPES[hashString(`${name}::shape`) % AVATAR_SHAPES.length];
}

function renderAvatar(el, name, mood = "happy") {
  if (!el) return;
  const safeName = (name || "?").trim() || "?";

  AVATAR_SHAPES.forEach((shape) => el.classList.remove(`avatar--${shape}`));
  el.classList.add(`avatar--${avatarShapeFor(safeName)}`);
  el.style.background = avatarColorFor(safeName);
  el.innerHTML = AVATAR_FACES[mood] || AVATAR_FACES.happy;
}
