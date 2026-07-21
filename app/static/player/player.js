const POLL_INTERVAL_MS = 1500;
const MAX_NAME_LENGTH = 20;
const STORAGE_CODE_KEY = "pc_player_join_code";
const STORAGE_TOKEN_KEY = "pc_player_token";
const STORAGE_NAME_KEY = "pc_player_name";

function getStoredIdentity() {
  const code = localStorage.getItem(STORAGE_CODE_KEY);
  const token = localStorage.getItem(STORAGE_TOKEN_KEY);
  const name = localStorage.getItem(STORAGE_NAME_KEY);
  if (!code || !token || !name) return null;
  return { code, token, name };
}

function storeIdentity(code, token, name) {
  localStorage.setItem(STORAGE_CODE_KEY, code);
  localStorage.setItem(STORAGE_TOKEN_KEY, token);
  localStorage.setItem(STORAGE_NAME_KEY, name);
}

function clearIdentity() {
  localStorage.removeItem(STORAGE_CODE_KEY);
  localStorage.removeItem(STORAGE_TOKEN_KEY);
  localStorage.removeItem(STORAGE_NAME_KEY);
}

async function joinRoom(code, name) {
  const res = await fetch(`/api/rooms/${code}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return res.json();
}

async function leaveRoomRequest(code, token) {
  await fetch(`/api/rooms/${code}/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}

async function fetchState(code) {
  const res = await fetch(`/api/rooms/${code}`);
  if (!res.ok) return null;
  return res.json();
}

async function submitArgumentRequest(code, token, text) {
  const res = await fetch(`/api/rooms/${code}/argument`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, text }),
  });
  return res.json();
}

function showView(view) {
  document.querySelectorAll("[data-view]").forEach((section) => {
    section.hidden = section.dataset.view !== view;
  });
}

function ordinal(n) {
  const j = n % 10;
  const k = n % 100;
  if (j === 1 && k !== 11) return `${n}st`;
  if (j === 2 && k !== 12) return `${n}nd`;
  if (j === 3 && k !== 13) return `${n}rd`;
  return `${n}th`;
}

let currentState = null;
let argumentSubmittedForRound = null;

function isLitigant(state, myName) {
  return state.plaintiff?.name === myName || state.defendant?.name === myName;
}

function determineView(state, myName) {
  const phase = state.phase;
  if (phase === "lobby") return "lobby";
  if (phase === "case_reveal") return isLitigant(state, myName) ? "summoned" : "jury-wait";
  if (phase === "arguments") return isLitigant(state, myName) ? "write-argument" : "jury-wait";
  if (phase === "verdict") return "all-rise";
  if (phase === "jury_vote") return isLitigant(state, myName) ? "on-trial" : "jury-vote";
  if (phase === "scoreboard") return "score";
  if (phase === "finale") return "adjourned";
  return "connecting";
}

function renderSummoned(state, myName) {
  document.querySelector("[data-case-number]").textContent = state.round;
  document.querySelector("[data-prompt]").textContent = state.prompt || "—";
  const role = state.plaintiff?.name === myName ? "PLAINTIFF" : "DEFENDANT";
  document.querySelectorAll("[data-my-role]").forEach((el) => (el.textContent = `YOU ARE THE ${role}`));
}

function renderWriteArgument(state, myName) {
  document.querySelector("[data-prompt]").textContent = state.prompt || "—";
  const role = state.plaintiff?.name === myName ? "PLAINTIFF" : "DEFENDANT";
  document.querySelectorAll("[data-my-role]").forEach((el) => (el.textContent = role));

  const alreadySubmitted = argumentSubmittedForRound === state.round;
  const textarea = document.querySelector("[data-argument-text]");
  const button = document.querySelector('[data-action="submit-argument"]');
  textarea.readOnly = alreadySubmitted;
  button.disabled = alreadySubmitted;
  button.textContent = alreadySubmitted ? "Filed with the court ✓" : "Submit to the Court";
}

function renderJuryVote(state) {
  renderAvatar(document.querySelector("[data-plaintiff-avatar]"), state.plaintiff?.name);
  renderAvatar(document.querySelector("[data-defendant-avatar]"), state.defendant?.name);
  document.querySelector("[data-plaintiff-name]").textContent = state.plaintiff?.name || "—";
  document.querySelector("[data-defendant-name]").textContent = state.defendant?.name || "—";
}

function renderScore(state, myName) {
  const rows = state.score_rows || [];
  const myIndex = rows.findIndex((row) => row.name === myName);
  document.querySelector("[data-my-rank]").textContent = myIndex >= 0 ? ordinal(myIndex + 1) : "—";
  document.querySelector("[data-my-pts]").textContent = myIndex >= 0 ? rows[myIndex].pts : 0;
}

function render(state, myName) {
  currentState = state;
  document.querySelectorAll("[data-my-name]").forEach((el) => (el.textContent = myName));
  document.querySelectorAll("[data-my-avatar]").forEach((el) => renderAvatar(el, myName));

  const view = determineView(state, myName);
  showView(view);

  if (view === "summoned") renderSummoned(state, myName);
  if (view === "write-argument") renderWriteArgument(state, myName);
  if (view === "jury-vote") renderJuryVote(state);
  if (view === "score") renderScore(state, myName);
}

function startApp(code, name) {
  showView("connecting");
  document.querySelector('[data-action="leave-room"]').hidden = false;

  async function poll() {
    const state = await fetchState(code);
    if (state && state.success !== false) render(state, name);
    setTimeout(poll, POLL_INTERVAL_MS);
  }
  poll();
}

function setupJoinForm() {
  const form = document.querySelector("[data-join-form]");
  const errorEl = document.querySelector("[data-join-error]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorEl.hidden = true;

    const code = form.querySelector('input[name="code"]').value.trim().toUpperCase();
    const name = form.querySelector('input[name="name"]').value.trim().slice(0, MAX_NAME_LENGTH);
    if (!code || !name) return;

    const data = await joinRoom(code, name);
    if (!data.success) {
      errorEl.textContent = data.error || "Could not join that room.";
      errorEl.hidden = false;
      return;
    }

    storeIdentity(data.join_code, data.player_token, name);
    startApp(data.join_code, name);
  });
}

function setupArgumentForm() {
  const button = document.querySelector('[data-action="submit-argument"]');
  const errorEl = document.querySelector("[data-argument-error]");

  button.addEventListener("click", async () => {
    errorEl.hidden = true;

    const identity = getStoredIdentity();
    const text = document.querySelector("[data-argument-text]").value.trim();
    if (!identity || !currentState || !text) return;

    const data = await submitArgumentRequest(identity.code, identity.token, text);
    if (!data.success) {
      errorEl.textContent = data.error || "Could not submit your argument.";
      errorEl.hidden = false;
      return;
    }

    argumentSubmittedForRound = currentState.round;
    renderWriteArgument(currentState, identity.name);
  });
}

function setupLeaveButton() {
  document.querySelector('[data-action="leave-room"]').addEventListener("click", async () => {
    const identity = getStoredIdentity();
    if (identity) await leaveRoomRequest(identity.code, identity.token);
    clearIdentity();
    window.location.reload();
  });
}

function main() {
  setupJoinForm();
  setupLeaveButton();
  setupArgumentForm();

  const identity = getStoredIdentity();
  if (identity) startApp(identity.code, identity.name);
}

main();
