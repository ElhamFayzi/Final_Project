const POLL_INTERVAL_MS = 1500;
const STORAGE_CODE_KEY = "pc_host_join_code";
const STORAGE_TOKEN_KEY = "pc_host_token";

async function createRoom() {
  const res = await fetch("/api/rooms", { method: "POST" });
  const data = await res.json();
  localStorage.setItem(STORAGE_CODE_KEY, data.join_code);
  localStorage.setItem(STORAGE_TOKEN_KEY, data.host_token);
  return data.join_code;
}

async function fetchState(joinCode) {
  const res = await fetch(`/api/rooms/${joinCode}`);
  if (!res.ok) return null;
  return res.json();
}

async function postHostAction(joinCode, action, extra = {}) {
  const hostToken = localStorage.getItem(STORAGE_TOKEN_KEY);
  await fetch(`/api/rooms/${joinCode}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host_token: hostToken, ...extra }),
  });
}

function showPhase(phase) {
  document.querySelectorAll("[data-phase]").forEach((section) => {
    section.hidden = section.dataset.phase !== phase;
  });
}

function renderJoinCode(joinCode) {
  document.querySelectorAll("[data-join-code]").forEach((el) => {
    el.textContent = joinCode;
  });
}

function renderLobby(state) {
  const seatsEl = document.querySelector("[data-lobby-seats]");
  seatsEl.innerHTML = "";
  state.players.forEach((player) => {
    const seat = document.createElement("div");
    seat.className = "lobby-seat";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    renderAvatar(avatar, player.name);

    const name = document.createElement("div");
    name.className = "lobby-seat__name";
    name.textContent = player.name;

    seat.append(avatar, name);
    seatsEl.append(seat);
  });

  document.querySelector("[data-player-count]").textContent = state.players.length;

  const startBtn = document.querySelector('[data-phase="lobby"] [data-action="start-court"]');
  const canStart = state.players.length >= 2;
  startBtn.disabled = !canStart;
  document.querySelector("[data-need-more]").hidden = canStart;

  const targetTurnsInput = document.querySelector("[data-target-turns-input]");
  if (document.activeElement !== targetTurnsInput) {
    targetTurnsInput.value = state.target_turns;
  }
}

function renderLitigants(state) {
  document
    .querySelectorAll("[data-plaintiff-avatar]")
    .forEach((el) => renderAvatar(el, state.plaintiff?.name));
  document
    .querySelectorAll("[data-defendant-avatar]")
    .forEach((el) => renderAvatar(el, state.defendant?.name));

  const plaintiffNameEls = document.querySelectorAll("[data-plaintiff-name]");
  const defendantNameEls = document.querySelectorAll("[data-defendant-name]");
  plaintiffNameEls.forEach((el) => (el.textContent = state.plaintiff?.name || "—"));
  defendantNameEls.forEach((el) => (el.textContent = state.defendant?.name || "—"));

  document.querySelectorAll("[data-case-number]").forEach((el) => {
    el.textContent = state.round;
  });
  document.querySelectorAll("[data-prompt]").forEach((el) => {
    el.textContent = state.prompt || "—";
  });
}

function renderVerdict(state) {
  document.querySelector("[data-ruling]").textContent = state.ruling || "—";
  document.querySelector("[data-reasoning]").textContent = state.reasoning || "—";

  const plaintiffWins = state.winner === "plaintiff";
  document.querySelector("[data-plaintiff-ribbon]").hidden = !plaintiffWins;
  document.querySelector("[data-defendant-ribbon]").hidden = plaintiffWins;

  const winnerName = plaintiffWins ? state.plaintiff?.name : state.defendant?.name;
  document.querySelector("[data-damages-stamp]").textContent =
    `${(winnerName || "").toUpperCase()} AWARDED ${state.damages ?? 0} PETTY POINTS`;
}

function renderJuryVote(state) {
  const votes = state.votes || { plaintiff: 0, defendant: 0 };
  const total = Math.max(1, votes.plaintiff + votes.defendant);
  const jurorCount = Math.max(0, state.players.length - 2);
  const votedCount = votes.plaintiff + votes.defendant;

  document.querySelector("[data-plaintiff-votes]").textContent = votes.plaintiff;
  document.querySelector("[data-defendant-votes]").textContent = votes.defendant;
  document.querySelector("[data-plaintiff-bar]").style.width = `${Math.round((votes.plaintiff / total) * 100)}%`;
  document.querySelector("[data-defendant-bar]").style.width = `${Math.round((votes.defendant / total) * 100)}%`;
  document.querySelector("[data-vote-status]").textContent = `${votedCount} / ${jurorCount} jurors have voted…`;
}

function renderScoreRows(container, rows) {
  container.innerHTML = "";
  rows.forEach((row, index) => {
    const rowEl = document.createElement("div");
    rowEl.className = "score-row" + (index === 0 ? " score-row--leader" : "");

    const rank = document.createElement("div");
    rank.className = "score-row__rank";
    rank.textContent = `${index + 1}.`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    renderAvatar(avatar, row.name);

    const name = document.createElement("div");
    name.className = "score-row__name";
    name.textContent = row.name;

    const pts = document.createElement("div");
    pts.className = "score-row__pts";
    pts.textContent = `${row.pts} pts`;

    rowEl.append(rank, avatar, name, pts);
    container.append(rowEl);
  });
}

function renderScoreboard(state) {
  renderScoreRows(document.querySelector("[data-score-rows]"), state.score_rows || []);
}

function renderFinale(state) {
  renderAvatar(document.querySelector("[data-champ-avatar]"), state.champ_name);
  document.querySelector("[data-champ-name]").textContent = state.champ_name || "—";
  document.querySelector("[data-champ-pts]").textContent = state.champ_pts ?? 0;
  renderScoreRows(document.querySelector("[data-final-score-rows]"), state.score_rows || []);
}

function render(state) {
  renderJoinCode(state.join_code);
  showPhase(state.phase);

  document.querySelector('[data-action="end-game"]').hidden =
    state.phase === "lobby" || state.phase === "finale";

  if (state.phase === "lobby") renderLobby(state);
  if (["case_reveal", "arguments", "verdict", "jury_vote"].includes(state.phase)) renderLitigants(state);
  if (state.phase === "verdict") renderVerdict(state);
  if (state.phase === "jury_vote") renderJuryVote(state);
  if (state.phase === "scoreboard") renderScoreboard(state);
  if (state.phase === "finale") renderFinale(state);
}

function newSession() {
  localStorage.removeItem(STORAGE_CODE_KEY);
  localStorage.removeItem(STORAGE_TOKEN_KEY);
  window.location.reload();
}

async function main() {
  let joinCode = localStorage.getItem(STORAGE_CODE_KEY);
  if (!joinCode) {
    joinCode = await createRoom();
  }

  document.querySelectorAll('[data-action="new-session"]').forEach((btn) => btn.addEventListener("click", newSession));
  document
    .querySelector('[data-action="start-court"]')
    .addEventListener("click", () => postHostAction(joinCode, "start"));

  document
    .querySelector('[data-phase="case_reveal"] [data-action="advance"]')
    .addEventListener("click", () => postHostAction(joinCode, "argue"));

  document
    .querySelector('[data-phase="arguments"] [data-action="advance"]')
    .addEventListener("click", () => postHostAction(joinCode, "verdict"));

  document
    .querySelector('[data-phase="verdict"] [data-action="advance"]')
    .addEventListener("click", () => postHostAction(joinCode, "deliberate"));

  document
    .querySelector('[data-phase="jury_vote"] [data-action="advance"]')
    .addEventListener("click", () => postHostAction(joinCode, "tally"));

  document
    .querySelector('[data-phase="scoreboard"] [data-action="advance"]')
    .addEventListener("click", () => postHostAction(joinCode, "next-case"));

  document.querySelector('[data-action="end-game"]').addEventListener("click", () => {
    if (confirm("End the game now and show final standings?")) {
      postHostAction(joinCode, "end");
    }
  });

  document.querySelector("[data-target-turns-input]").addEventListener("change", (event) => {
    postHostAction(joinCode, "settings", { target_turns: Number(event.target.value) });
  });

  async function poll() {
    const state = await fetchState(joinCode);
    if (state) render(state);
    setTimeout(poll, POLL_INTERVAL_MS);
  }
  poll();
}

main();
