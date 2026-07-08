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
  imageMap: {},    // card/face name -> Scryfall image
  vizGames: [],    // successful games (each a list of board frames)
  vizIdx: 0,
  vizStep: 0,
};

const PIP_COLORS = { W: 0, U: 1, B: 2, R: 3, G: 4 };

// Render a mana-cost string like "{2}{W}{U}" into official Scryfall symbols.
function manaCostEl(cost) {
  const span = el("span", { className: "mana" });
  for (const s of (cost || "").match(/\{[^}]+\}/g) || []) {
    const code = s.slice(1, -1).toUpperCase().replace(/\//g, "");
    span.append(el("img", {
      className: "ms", alt: s, loading: "lazy",
      src: `https://svgs.scryfall.io/card-symbols/${code}.svg`,
    }));
  }
  return span;
}

// Mana cost shown at the end of a decklist line — includes the back face's cost
// for double-faced cards that have one.
function costEnd(c) {
  const wrap = el("span", { className: "cost-end" });
  const front = c.mana_cost || (c.faces[0] && c.faces[0].mana_cost) || "";
  if (front) wrap.append(manaCostEl(front));
  if (c.faces && c.faces.length === 2 && c.faces[1].mana_cost) {
    wrap.append(el("span", { className: "muted", textContent: " // " }));
    wrap.append(manaCostEl(c.faces[1].mana_cost));
  }
  return wrap;
}

// WUBRG, then multicolor, colorless, lands.
function colorRank(c) {
  if (c.is_land) return 7;
  const cols = c.colors || [];
  if (cols.length === 0) return 6;
  if (cols.length > 1) return 5;
  return PIP_COLORS[cols[0]] ?? 6;
}

// For multicolor cards: lexical key over WUBRG letter order.
function colorKey(c) {
  return (c.colors || [])
    .map((x) => PIP_COLORS[x])
    .filter((n) => n != null)
    .sort((a, b) => a - b)
    .join("");
}

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
  $("compile-props").onclick = compileProps;
  $("run-btn").onclick = runSim;
  $("play-draw-toggle").onclick = (e) => {
    const b = e.currentTarget;
    const on = b.dataset.play === "1";
    b.dataset.play = on ? "0" : "1";
    b.textContent = on ? "On the draw" : "On the play";
  };
  $("stop-btn").onclick = () => api(`/api/sessions/${state.session.id}/simulate/stop`, { method: "POST" });
  $("delete-session").onclick = deleteSession;
  $("load-run-btn").onclick = openRunsModal;
  $("run-modal-close").onclick = closeRunsModal;
  $("run-modal").onclick = (e) => { if (e.target.id === "run-modal") closeRunsModal(); };
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
          `${s.commanders.join(", ") || "no commander"} · ${s.num_results} runs` }),
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
  state.imageMap = {};
  for (const c of state.cards) {
    if (c.image) state.imageMap[c.name] = c.image;
    for (const f of c.faces || []) if (f.image) state.imageMap[f.name] = f.image;
  }
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
  $("sim-seed").textContent = "";
  $("viz-box").classList.add("hidden");
  $("load-run-btn").disabled = !(state.session.results || []).length;
  openWs();
}

// ---- previous-runs modal ----
const fmtDate = (s) => (s || "").slice(0, 19).replace("T", " ");

function propText(p) {
  return p.description || `${p.timing} ${p.phase} of turn ${p.turn}: ${p.english}`;
}

function openRunsModal() {
  const results = state.session.results || [];
  const body = $("run-modal-body");
  if (!results.length) {
    body.replaceChildren(el("div", { className: "muted", textContent: "No runs yet." }));
  } else {
    const thead = el("thead", {}, el("tr", {},
      ...["Date", "Properties", "Success", "Games", "Mulligans", "Start", "Seed"].map((h) => el("th", { textContent: h }))));
    const tbody = el("tbody");
    results.slice().reverse().forEach((r) => {
      const st = r.stats || {}, cfg = r.config || {}, gr = st.games_run || 0;
      const propCells = (r.properties || []).map((p) => {
        const cnt = (st.per_property || {})[p.id] ?? 0;
        const rate = gr ? (100 * cnt / gr).toFixed(0) : "0";
        return el("div", {},
          el("div", { className: "prop-line", textContent: propText(p) }),
          el("div", { className: "pp", textContent: `↳ ${cnt}/${gr} (${rate}%)` }));
      });
      const tr = el("tr", {},
        el("td", { textContent: fmtDate(r.created_at) }),
        el("td", {}, ...(propCells.length ? propCells : [el("span", { className: "muted", textContent: "—" })])),
        el("td", {},
          el("span", { className: "big", textContent: `${((st.success_rate || 0) * 100).toFixed(1)}%` }),
          el("div", { className: "pp", textContent: `${st.successes || 0}/${gr}` })),
        el("td", { textContent: String(cfg.num_games ?? "") }),
        el("td", { textContent: String(cfg.mulligans ?? 0) }),
        el("td", { textContent: cfg.on_the_play === false ? "draw" : "play" }),
        el("td", { textContent: String(cfg.base_seed ?? "") }));
      tr.onclick = () => loadRun(r);
      tbody.append(tr);
    });
    body.replaceChildren(el("table", { className: "runs" }, thead, tbody));
  }
  $("run-modal").classList.remove("hidden");
}

function closeRunsModal() { $("run-modal").classList.add("hidden"); }

function loadRun(r) {
  closeRunsModal();
  const cfg = r.config || {};
  $("num-games").value = cfg.num_games ?? 100;
  $("mulligans").value = cfg.mulligans ?? 0;
  $("timeout").value = cfg.timeout_per_game_s ?? 5;
  $("seed").value = cfg.base_seed ?? "";
  const b = $("play-draw-toggle"), on = cfg.on_the_play !== false;
  b.dataset.play = on ? "1" : "0";
  b.textContent = on ? "On the play" : "On the draw";
  if (r.properties && r.properties.length) {
    state.props = r.properties.map((p) => ({ ...p }));
    renderProps();
  }
  $("sim-seed").textContent = `seed: ${cfg.base_seed}`;
  renderStats(r.stats || {});
  renderViz(r); // offers to visualize the games (shows the board viewer)
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
    color: (a, b) => colorRank(a) - colorRank(b) || colorKey(a).localeCompare(colorKey(b)) || a.cmc - b.cmc || a.name.localeCompare(b.name),
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

function hoverable(node, img) {
  if (!img) return node;
  node.onmouseenter = () => showHover(img);
  node.onmousemove = moveHover;
  node.onmouseleave = hideHover;
  return node;
}

function cardRow(c) {
  const row = el("div", { className: "card-row" + (c.implemented ? "" : " unimpl") });
  row.append(el("span", { className: "qty", textContent: c.quantity + "×" }));

  const nameWrap = el("span", { className: "cname" });
  if (c.faces && c.faces.length === 2) {
    // Each face name hovers its own image (front // back).
    c.faces.forEach((f, i) => {
      if (i) nameWrap.append(document.createTextNode(" // "));
      nameWrap.append(hoverable(el("span", { textContent: f.name || `face ${i + 1}` }), f.image || c.image));
    });
  } else {
    nameWrap.textContent = c.name;
    hoverable(nameWrap, c.image);
  }
  row.append(nameWrap);

  if (!c.implemented) {
    const w = el("span", { className: "wrench", title: "Ask a model to code this card", textContent: "🔧" });
    w.onclick = (e) => { e.stopPropagation(); askImplement(c.name); };
    row.append(w);
  }
  row.append(costEnd(c)); // mana cost at the far right
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
  if (p.code) {
    wrap.append(el("label", { textContent: "generated code" }));
    wrap.append(el("pre", { textContent: p.code }));
  }
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
  const seedField = $("seed").value.trim();
  const body = JSON.stringify({
    num_games: parseInt($("num-games").value) || 100,
    timeout_per_game_s: parseFloat($("timeout").value) || 5,
    mulligans: parseInt($("mulligans").value) || 0,
    on_the_play: $("play-draw-toggle").dataset.play === "1",
    base_seed: seedField === "" ? null : parseInt(seedField),
  });
  try {
    const r = await api(`/api/sessions/${state.session.id}/simulate`, { method: "POST", body });
    state.currentResultId = r.result_id;
    $("sim-seed").textContent = `seed: ${r.seed}` + (seedField === "" ? " (random)" : "");
    $("run-btn").disabled = true; $("stop-btn").disabled = false;
    $("viz-box").classList.add("hidden");
    renderStats({ total_games: parseInt($("num-games").value) || 100, games_run: 0, successes: 0, timeouts: 0, success_rate: 0, per_property: {} });
  } catch (e) { alert("Cannot start: " + e.message); }
}

function onSimEvent(msg) {
  if (msg.type === "progress") renderStats(msg.stats);
  else if (msg.type === "done") {
    $("run-btn").disabled = false; $("stop-btn").disabled = true;
    state.session.results = state.session.results || [];
    state.session.results.push(msg.result);
    $("load-run-btn").disabled = false;
    $("sim-seed").textContent = `seed: ${msg.result.config?.base_seed}`;
    renderStats(msg.result.stats);
    renderViz(msg.result); // show this run's successful games
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
  // Drop "pass" and "pay ..." steps, then order shortest games first.
  state.vizGames = (result.sample_success_logs || [])
    .map((g) => g.filter((f) => {
      const d = f.desc || "";
      return !d.startsWith("pass") && !d.startsWith("pay ");
    }))
    .sort((a, b) => a.length - b.length);
  const box = $("viz-box");
  const list = $("viz-list");
  if (!state.vizGames.length) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  list.replaceChildren(...state.vizGames.map((frames, i) => {
    const b = el("button", { textContent: `Game #${i + 1} · ${frames.length} steps`, style: "margin:.15rem" });
    b.onclick = () => { highlightGame(i); openBoard(i); };
    return b;
  }));
  highlightGame(0);
  openBoard(0);
}

function highlightGame(gi) {
  [...$("viz-list").children].forEach((b, i) =>
    b.classList.toggle("primary", i === gi));
}

// ---- graphical board (MTGO-like) ----
function tile(name, opts = {}) {
  const t = el("div", {
    className: "tile" + (opts.tapped ? " tapped" : "") + (opts.sick ? " sick" : "") +
      (opts.commander ? " commander" : "") + (opts.attacking ? " attacking" : ""),
    title: name + (opts.tapped ? " (tapped)" : "") + (opts.attacking ? " (attacking)" : ""),
  });
  const img = state.imageMap[name];
  if (img) t.append(el("img", { src: img, alt: name, loading: "lazy" }));
  else t.append(el("div", { className: "fallback", textContent: name }));
  if (opts.commander) t.append(el("div", { className: "badge", textContent: "CMD" }));
  const counters = opts.counters || {};
  const plus = counters["+1/+1"];
  if (plus) t.append(el("div", { className: "badge ctr", textContent: `+${plus}/+${plus}` }));
  if (counters.fade) t.append(el("div", { className: "badge ctr", textContent: `fade ${counters.fade}` }));
  if (counters.loyalty) t.append(el("div", { className: "badge ctr", textContent: `⟐${counters.loyalty}` }));
  return t;
}

function poolPips(pool) {
  const span = el("span", { className: "pool-pips" });
  for (const [c, n] of Object.entries(pool || {}))
    for (let k = 0; k < n; k++) span.append(el("span", { className: "pip " + c, textContent: c }));
  if (!span.childNodes.length) span.append(el("span", { className: "muted", textContent: "—" }));
  return span;
}

function renderBoard(f) {
  const bf = f.battlefield || [];
  const mkPerm = (p) => tile(p.name, { tapped: p.tapped, sick: p.sick, commander: p.commander, attacking: p.attacking, counters: p.counters });
  const lands = bf.filter((p) => p.is_land).map(mkPerm);
  const nonlands = bf.filter((p) => !p.is_land).map(mkPerm);
  const c = f.counters || {};

  const header = el("div", { className: "board-header" },
    el("span", { className: "turn", textContent: `Turn ${f.turn} · ${f.phase}` }),
    el("span", {}, el("span", { className: "k", textContent: "life " }), String(f.life)),
    el("span", {}, el("span", { className: "k", textContent: "opp " }), String(f.opponent_life ?? 20)),
    el("span", {}, el("span", { className: "k", textContent: "library " }), String(f.library)),
    el("span", {}, el("span", { className: "k", textContent: "pool " }), poolPips(f.mana_pool)),
    el("span", { className: "counter-chip", textContent: `spells ${c.spells || 0}` }),
    el("span", { className: "counter-chip", textContent: `noncreature ${c.noncreature || 0}` }),
    el("span", { className: "counter-chip", textContent: `drawn ${c.drawn || 0}` }));

  // MTGO-like layout: command zone top-left, stack top-right (graveyard below
  // it), the field in the middle (lands under the other permanents), hand at
  // the bottom.
  const grid = el("div", { className: "board-grid" });
  grid.append(
    el("div", { className: "bzone area-cmd" },
      el("div", { className: "zlabel", textContent: `Command zone (${(f.command_zone || []).length})` }),
      el("div", { className: "tiles small" }, ...(f.command_zone || []).map((n) => tile(n, { commander: true })))),
    el("div", { className: "bzone area-field" },
      el("div", { className: "field-row" },
        el("div", { className: "zlabel", textContent: `Battlefield (${nonlands.length + lands.length})` }),
        el("div", { className: "tiles" }, ...nonlands)),
      el("div", { className: "field-row lands" },
        el("div", { className: "tiles" }, ...lands))),
    el("div", { className: "bzone area-side" },
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Stack (${(f.stack || []).length})` }),
        el("div", { className: "tiles small" }, ...(f.stack || []).map((n) => tile(n)))),
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Graveyard (${(f.graveyard || []).length})` }),
        el("div", { className: "tiles small" }, ...(f.graveyard || []).map((n) => tile(n)))),
      (f.exile || []).length ? el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Exile (${f.exile.length})` }),
        el("div", { className: "tiles small" }, ...f.exile.map((n) => tile(n)))) : ""),
    el("div", { className: "bzone area-hand" },
      el("div", { className: "zlabel", textContent: `Hand (${(f.hand || []).length})` }),
      el("div", { className: "tiles hand" }, ...(f.hand || []).map((n) => tile(n)))),
  );
  return el("div", {}, header, grid);
}

function openBoard(gi) {
  const frames = state.vizGames[gi];
  if (!frames || !frames.length) return;
  state.vizIdx = gi;
  state.vizStep = 0; // start at step 1

  const host = $("viz-log");
  host.className = "";
  host.replaceChildren();

  const prev = el("button", { textContent: "◀ Prev" });
  const next = el("button", { textContent: "Next ▶" });
  const counter = el("span", { className: "muted" });
  const desc = el("span", { className: "desc" });
  const range = el("input", { type: "range", min: 0, max: frames.length - 1, value: 0, style: "flex:1" });

  const draw = () => {
    const f = frames[state.vizStep];
    counter.textContent = `step ${state.vizStep + 1} / ${frames.length}`;
    desc.textContent = f.desc || "";
    range.value = state.vizStep;
    board.replaceChildren(renderBoard(f));
  };
  prev.onclick = () => { state.vizStep = Math.max(0, state.vizStep - 1); draw(); };
  next.onclick = () => { state.vizStep = Math.min(frames.length - 1, state.vizStep + 1); draw(); };
  range.oninput = () => { state.vizStep = +range.value; draw(); };

  const board = el("div", { className: "board" });
  host.append(
    el("div", { className: "board-toolbar" }, prev, next, counter, range),
    el("div", { className: "board-toolbar" }, desc),
    board,
  );
  draw();
}

async function deleteSession() {
  if (!confirm(`Delete session "${state.session.name}"?`)) return;
  await api(`/api/sessions/${state.session.id}`, { method: "DELETE" });
  showHome();
}

init().catch((e) => alert("Init failed: " + e.message));
