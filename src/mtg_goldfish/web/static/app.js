"use strict";

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  Object.assign(n, props);
  for (const k of kids) n.append(k?.nodeType ? k : document.createTextNode(k ?? ""));
  return n;
};

const state = {
  meta: null,
  session: null,   // full session object
  cards: [],       // card_view rows
  props: [],       // property specs (client-side working copy)
  ws: null,
  currentResultId: null,
};

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

// ---------------------------------------------------------------- init
async function init() {
  state.meta = await api("/api/meta");
  const pill = $("llm-pill");
  pill.textContent = "LLM: " + state.meta.llm_provider + (state.meta.llm_is_real ? "" : " (offline stub)");
  if (!state.meta.llm_is_real) pill.classList.add("warn");

  const fs = $("format-select");
  fs.replaceChildren(...state.meta.formats.map((f) => el("option", { value: f.id, textContent: f.name })));

  $("home-btn").onclick = showHome;
  $("create-btn").onclick = doCreate;
  $("add-prop").onclick = () => { addProperty(); renderProps(); };
  $("save-props").onclick = saveProps;
  $("compile-props").onclick = compileProps;
  $("run-btn").onclick = runSim;
  $("stop-btn").onclick = () => api(`/api/sessions/${state.session.id}/simulate/stop`, { method: "POST" });
  $("delete-session").onclick = deleteSession;
  $("sort-select").onchange = renderDeck;

  await loadSessionList();
  showHome();
}

function showHome() {
  closeWs();
  $("home-view").classList.remove("hidden");
  $("session-view").classList.add("hidden");
  loadSessionList();
}

// ---------------------------------------------------------------- home
async function loadSessionList() {
  const box = $("session-list");
  try {
    const { sessions } = await api("/api/sessions");
    if (!sessions.length) { box.textContent = "No sessions yet."; return; }
    box.replaceChildren(...sessions.map((s) => {
      const open = el("button", { textContent: "Open", onclick: () => openSession(s.id) });
      return el("div", { className: "session-list-item" },
        el("b", { textContent: s.name }),
        el("span", { className: "muted", textContent:
          `${s.commanders.join(", ") || "no commander"} · ${s.num_properties} props · ${s.num_results} runs` }),
        el("span", { className: "grow" }), open);
    }));
  } catch (e) { box.textContent = "Error: " + e.message; }
}

function homeStatus(msg, isErr) {
  const s = $("home-status");
  s.textContent = msg;
  s.className = isErr ? "err" : "muted";
}

async function doCreate() {
  const body = JSON.stringify({ url: $("deck-url").value, name: $("deck-name").value, format_id: $("format-select").value });
  homeStatus("Creating session…");
  try {
    const payload = await api("/api/sessions", { method: "POST", body });
    enterSession(payload);
  } catch (e) { homeStatus(e.message, true); }
}

// ---------------------------------------------------------------- session
async function openSession(id) {
  const payload = await api(`/api/sessions/${id}`);
  enterSession(payload);
}

function enterSession(payload) {
  state.session = payload.session;
  state.cards = payload.cards;
  state.props = (payload.session.properties || []).map((p) => ({ ...p }));
  $("home-view").classList.add("hidden");
  $("session-view").classList.remove("hidden");
  $("s-name").textContent = state.session.name;
  $("s-commanders").textContent = "⚔ " + (state.cards.filter((c) => c.board === "commander").map((c) => c.name).join(", ") || "none");
  $("s-format").textContent = state.session.format_id;
  $("s-warnings").textContent = (payload.warnings || []).join("  •  ");
  $("mulligans").value = state.session.mulligans || 0;
  renderDeck();
  if (!state.props.length) addProperty();
  renderProps();
  $("sim-stats").innerHTML = "";
  $("viz-box").classList.add("hidden");
  openWs();
}

// ---- decklist
const GROUP_ORDER = ["Commander", "Companion", "Creature", "Planeswalker", "Battle",
  "Instant", "Sorcery", "Artifact", "Enchantment", "Land", "Other", "Sideboard"];

function primaryType(typeLine) {
  const t = (typeLine || "").toLowerCase();
  if (t.includes("creature")) return "Creature";
  if (t.includes("planeswalker")) return "Planeswalker";
  if (t.includes("battle")) return "Battle";
  if (t.includes("instant")) return "Instant";
  if (t.includes("sorcery")) return "Sorcery";
  if (t.includes("artifact")) return "Artifact";
  if (t.includes("enchantment")) return "Enchantment";
  if (t.includes("land")) return "Land";
  return "Other";
}

function groupLabel(c) {
  if (c.board === "commander") return "Commander";
  if (c.board === "companion") return "Companion";
  if (c.board === "sideboard") return "Sideboard";
  return primaryType(c.type_line); // mainboard grouped by type
}

function renderDeck() {
  const sort = $("sort-select").value;
  const cmp = {
    name: (a, b) => a.name.localeCompare(b.name),
    cmc: (a, b) => a.cmc - b.cmc || a.name.localeCompare(b.name),
    color: (a, b) => (a.colors.join("") || "Z").localeCompare(b.colors.join("") || "Z") || a.name.localeCompare(b.name),
  }[sort];

  const groups = {};
  for (const c of state.cards) (groups[groupLabel(c)] ||= []).push(c);

  const container = $("deck-cards");
  container.replaceChildren();
  const total = state.cards.reduce((n, c) => n + c.quantity, 0);
  const impl = state.cards.filter((c) => c.implemented).length;
  $("deck-summary").textContent = `${total} cards · ${impl}/${state.cards.length} distinct implemented`;

  const order = Object.keys(groups).sort((a, b) => {
    const ia = GROUP_ORDER.indexOf(a), ib = GROUP_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
  order.forEach((label) => {
    const n = groups[label].reduce((s, c) => s + c.quantity, 0);
    container.append(el("div", { className: "card-group-title", textContent: `${label} (${n})` }));
    groups[label].sort(cmp).forEach((c) => container.append(cardRow(c)));
  });
}

function cardRow(c) {
  const row = el("div", { className: "card-row" + (c.implemented ? "" : " unimpl") });
  row.append(el("span", { className: "qty", textContent: c.quantity + "×" }));
  row.append(el("span", { className: "cname", textContent: c.name }));
  if (Number.isFinite(c.cmc) && !c.is_land) row.append(el("span", { className: "cmc", textContent: "{" + c.cmc + "}" }));
  if (!c.implemented) {
    const w = el("span", { className: "wrench", title: "Ask a model to code this card", textContent: "🔧" });
    w.onclick = (e) => { e.stopPropagation(); askImplement(c.name); };
    row.append(w);
  }
  if (c.image) {
    row.onmouseenter = () => showHover(c.image);
    row.onmousemove = moveHover;
    row.onmouseleave = hideHover;
  }
  return row;
}

async function askImplement(name) {
  try {
    await api(`/api/cards/${encodeURIComponent(name)}/implement`, { method: "POST" });
  } catch (e) {
    alert(`${name}: ${e.message}`);
  }
}

const hover = $("hover-img");
function showHover(src) { hover.querySelector("img").src = src; hover.style.display = "block"; }
function moveHover(e) {
  const x = Math.min(e.clientX + 18, window.innerWidth - 260);
  const y = Math.min(e.clientY + 18, window.innerHeight - 360);
  hover.style.left = x + "px"; hover.style.top = y + "px";
}
function hideHover() { hover.style.display = "none"; }

// ---- properties
let propCounter = 0;
function addProperty(p) {
  propCounter += 1;
  state.props.push(p || {
    id: "p" + Date.now() + "_" + propCounter,
    timing: "at",
    phase: "precombat_main",
    turn: 1,
    english: "",
    code: null,
    enabled: true,
  });
}

function renderProps() {
  const list = $("prop-list");
  list.replaceChildren(...state.props.map((p, i) => propRow(p, i)));
}

function propRow(p, i) {
  const wrap = el("div", { className: "prop" });
  const timing = el("select", {}, ...["before", "at"].map((t) =>
    el("option", { value: t, textContent: t, selected: p.timing === t })));
  timing.onchange = () => (p.timing = timing.value);

  const phase = el("select", {}, ...state.meta.phases.map((ph) =>
    el("option", { value: ph.value, textContent: ph.label, selected: p.phase === ph.value })));
  phase.onchange = () => (p.phase = phase.value);

  const turn = el("input", { type: "number", min: 1, value: p.turn, style: "width:4rem" });
  turn.onchange = () => (p.turn = parseInt(turn.value) || 1);

  const del = el("button", { className: "danger del", textContent: "✕" });
  del.onclick = () => { state.props.splice(i, 1); renderProps(); };

  const trigger = el("div", { className: "row trigger" }, timing, phase, "of turn", turn, del);

  const ta = el("textarea", { rows: 2, placeholder: "e.g. the commander is in play and 4 non-creature spells have been cast this turn", value: p.english });
  ta.oninput = () => { p.english = ta.value; p.code = null; };

  wrap.append(trigger, ta);
  if (p.code) wrap.append(el("pre", { textContent: p.code }));
  return wrap;
}

async function saveProps() {
  const body = JSON.stringify({ properties: state.props, mulligans: parseInt($("mulligans").value) || 0 });
  await api(`/api/sessions/${state.session.id}/properties`, { method: "PUT", body });
}

async function compileProps() {
  await saveProps();
  const btn = $("compile-props");
  btn.disabled = true; btn.textContent = "Compiling…";
  try {
    const r = await api(`/api/sessions/${state.session.id}/properties/compile`, { method: "POST" });
    state.props = r.properties.map((p) => ({ ...p }));
    renderProps();
  } catch (e) { alert("Compile failed: " + e.message); }
  finally { btn.disabled = false; btn.textContent = "Compile → review code"; }
}

// ---- simulation + websocket
function openWs() {
  closeWs();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/${state.session.id}`);
  ws.onmessage = (ev) => onSimEvent(JSON.parse(ev.data));
  state.ws = ws;
}
function closeWs() { if (state.ws) { try { state.ws.close(); } catch {} state.ws = null; } }

async function runSim() {
  await compileProps();
  const body = JSON.stringify({
    num_games: parseInt($("num-games").value) || 100,
    timeout_per_game_s: parseFloat($("timeout").value) || 5,
    mulligans: parseInt($("mulligans").value) || 0,
  });
  try {
    const r = await api(`/api/sessions/${state.session.id}/simulate`, { method: "POST", body });
    state.currentResultId = r.result_id;
    $("run-btn").disabled = true; $("stop-btn").disabled = false;
    $("viz-box").classList.add("hidden");
    renderStats({ total_games: parseInt($("num-games").value) || 100, games_run: 0, successes: 0, timeouts: 0, success_rate: 0, per_property: {} });
  } catch (e) { alert("Cannot start: " + e.message); }
}

function onSimEvent(msg) {
  if (msg.type === "progress") renderStats(msg.stats);
  else if (msg.type === "done") {
    $("run-btn").disabled = false; $("stop-btn").disabled = true;
    renderStats(msg.result.stats);
    renderViz(msg.result);
  }
}

function renderStats(stats) {
  const box = $("sim-stats");
  const pct = (stats.success_rate * 100).toFixed(1);
  const progress = stats.total_games ? (stats.games_run / stats.total_games) * 100 : 0;
  const propNames = {};
  state.props.forEach((p) => (propNames[p.id] = p.english || p.id));

  box.replaceChildren(
    el("div", { className: "bar" }, el("div", { style: `width:${progress}%` })),
    el("div", { className: "muted", style: "font-size:12px;margin:.3rem 0", textContent:
      `${stats.games_run}/${stats.total_games} games` }),
    el("div", { className: "stat-grid" },
      stat("Success rate", pct + "%"),
      stat("Successes", stats.successes),
      stat("Games run", stats.games_run),
      stat("Timeouts", stats.timeouts)),
    el("div", { style: "margin-top:.7rem" },
      el("div", { className: "muted", style: "font-size:11px;text-transform:uppercase", textContent: "Per property (any line)" }),
      ...Object.entries(stats.per_property || {}).map(([id, n]) =>
        el("div", { className: "prop-stat" },
          el("span", { textContent: propNames[id] || id }),
          el("b", { textContent: `${n} / ${stats.games_run}` })))),
  );
}

function stat(k, v) {
  return el("div", { className: "stat" }, el("div", { className: "v", textContent: v }), el("div", { className: "k", textContent: k }));
}

function renderViz(result) {
  const logs = result.sample_success_logs || [];
  const box = $("viz-box");
  const list = $("viz-list");
  const logView = $("viz-log");
  logView.classList.add("hidden");
  if (!logs.length) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  list.replaceChildren(...logs.map((log, i) => {
    const b = el("button", { textContent: `Game #${i + 1} (${log.length} steps)`, style: "margin:.2rem" });
    b.onclick = () => { logView.textContent = log.join("\n"); logView.classList.remove("hidden"); };
    return b;
  }));
}

async function deleteSession() {
  if (!confirm(`Delete session "${state.session.name}"?`)) return;
  await api(`/api/sessions/${state.session.id}`, { method: "DELETE" });
  showHome();
}

init().catch((e) => alert("Init failed: " + e.message));
