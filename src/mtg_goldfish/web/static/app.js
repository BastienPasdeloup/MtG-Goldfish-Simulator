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
  vizRuns: [],     // per-game run metadata (hand, branch counts, tree, frames)
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
  updateLlmUi();

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
  $("impl-all").onclick = implementAll;
  $("model-btn").onclick = openModelModal;
  $("model-modal-close").onclick = () => $("model-modal").classList.add("hidden");
  $("model-modal").onclick = (e) => { if (e.target.id === "model-modal") $("model-modal").classList.add("hidden"); };
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
  // Always open with a single uninitialized property (a previous run's
  // properties can be restored explicitly via "Load previous run").
  state.props = [];
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
  addProperty(); // exactly one blank property on open
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
  return p.description || `${timingLabel(p.timing)} ${p.phase} of turn ${p.turn}: ${p.english}`;
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
  $("search-mode").value = cfg.search_mode ?? "dfs_heuristic";
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
  // Global implement-all wrench appears only when something is unimplemented.
  $("impl-all").classList.toggle("hidden", impl >= state.cards.length);

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

function hoverable(node, img, meta = null) {
  if (!img) return node;
  node.onmouseenter = () => showHover(img, meta);
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
    w.onclick = (e) => { e.stopPropagation(); askImplement(c.name, w); };
    row.append(w);
  }
  row.append(costEnd(c)); // mana cost at the far right
  return row;
}

// Refresh the deck's implemented flags after code generation.
async function refreshDeck() {
  const payload = await api(`/api/sessions/${state.session.id}`);
  state.cards = payload.cards;
  renderDeck();
}

async function askImplement(name, el0) {
  if (el0) { el0.textContent = "⏳"; el0.style.pointerEvents = "none"; }
  try {
    await api(`/api/sessions/${state.session.id}/cards/${encodeURIComponent(name)}/implement`,
      { method: "POST" });
    await refreshDeck();
  } catch (e) {
    alert(`${name}: ${e.message}`);
    if (el0) { el0.textContent = "🔧"; el0.style.pointerEvents = ""; }
  }
}

async function implementAll() {
  const btn = $("impl-all");
  const n = state.cards.filter((c) => !c.implemented).length;
  if (!n) return;
  if (!confirm(`Ask the selected model to implement ${n} unimplemented card(s)?\n` +
    `Quality depends on the model; failures keep their vanilla approximation.`)) return;
  btn.textContent = " ⏳";
  try {
    const r = await api(`/api/sessions/${state.session.id}/cards/implement-all`, { method: "POST" });
    await refreshDeck();
    const failed = (r.results || []).filter((x) => !x.ok);
    let msg = `Implemented ${r.implemented}/${r.total} cards.`;
    if (failed.length) msg += `\n\nStill unimplemented:\n` +
      failed.slice(0, 12).map((x) => `• ${x.name}: ${x.error}`).join("\n");
    alert(msg);
  } catch (e) {
    alert("Implement-all failed: " + e.message);
  } finally {
    btn.textContent = " 🔧";
  }
}

// ---- model picker ----
// Reflect the currently selected LLM everywhere it's shown: the top pill, the
// Properties-section model button, and the note under it. The provider is
// shared — the same model compiles properties and implements cards.
function updateLlmUi() {
  const m = state.meta || {};
  const pill = $("llm-pill");
  if (pill) {
    pill.textContent = "LLM: " + m.llm_provider + (m.llm_is_real ? "" : " (offline stub)");
    pill.classList.toggle("warn", !m.llm_is_real);
  }
  const note = $("prop-llm-note");
  if (note) {
    note.textContent = m.llm_is_real
      ? `Properties are compiled to code by ${m.llm_provider}.`
      : `Properties are compiled by the offline stub (regex heuristics only). Click “⚙ Model” to pick a local or API model for accurate compilation.`;
    note.classList.toggle("warnings", !m.llm_is_real);
  }
}

async function openModelModal() {
  const body = $("model-list");
  body.replaceChildren(el("div", { className: "muted", textContent: "Loading…" }));
  $("model-modal").classList.remove("hidden");
  let data;
  try { data = await api("/api/llm"); }
  catch (e) { body.replaceChildren(el("div", { className: "err", textContent: e.message })); return; }

  const rows = data.options.map((o) => {
    const row = el("div", { className: "model-row" + (o.id === data.selected ? " selected" : "") });
    const head = el("div", { className: "model-head" },
      el("b", { textContent: o.label }),
      o.id === data.selected ? el("span", { className: "pill warn", textContent: "active" }) : "");
    if (o.size) head.append(el("span", { className: "muted", textContent: " " + o.size }));
    row.append(head, el("div", { className: "muted", style: "font-size:12px", textContent: o.detail }));

    // Status + action line.
    const foot = el("div", { className: "model-foot" });
    if (o.kind === "local") {
      if (!o.ollama_running) {
        foot.append(el("span", { className: "problems", textContent:
          "Ollama not detected — install from ollama.com, then run it." }));
      } else if (!o.installed) {
        foot.append(el("span", { className: "warnings", textContent: `Not downloaded — run:  ${o.pull_cmd}` }));
      } else {
        foot.append(el("span", { className: "muted", textContent: "Downloaded and ready." }));
      }
    } else if (o.kind === "api") {
      foot.append(el("span", { className: "muted", textContent:
        data.has_api_key ? "API key set." : "Requires an API key (entered below, stored locally)." }));
    }
    row.append(foot);

    let keyInput = null;
    if (o.needs_key && !data.has_api_key) {
      keyInput = el("input", { type: "password", placeholder: "ANTHROPIC_API_KEY", style: "width:100%;margin-top:.4rem" });
      row.append(keyInput);
    }

    const use = el("button", { className: "primary", style: "margin-top:.5rem",
      textContent: o.id === data.selected ? "Selected" : "Use this model" });
    use.disabled = o.id === data.selected;
    use.onclick = async () => {
      try {
        await api("/api/llm", { method: "POST",
          body: JSON.stringify({ model_id: o.id, api_key: keyInput ? keyInput.value : null }) });
        state.meta = await api("/api/meta"); // pick up the new provider
        updateLlmUi();
        openModelModal(); // refresh the list
      } catch (e) { alert(e.message); }
    };
    row.append(use);
    return row;
  });
  body.replaceChildren(...rows);
}

const hover = $("hover-img");
function showHover(src, meta = null) {
  hover.querySelector("img").src = src;
  const box = hover.querySelector(".hover-meta");
  if (meta && (meta.title || meta.trigger || meta.ability)) {
    box.innerHTML = "";
    if (meta.title) box.append(el("div", { className: "k", textContent: meta.title }));
    if (meta.trigger) box.append(el("div", { textContent: `Triggered by: ${meta.trigger}` }));
    if (meta.ability) box.append(el("div", { textContent: `On stack: ${meta.ability}` }));
    box.style.display = "block";
  } else {
    box.textContent = "";
    box.style.display = "none";
  }
  hover.style.display = "block";
}
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

// Display label for a timing value ("at" is checked during/at that phase, but
// reads better as "at the end of" in the UI).
const timingLabel = (t) => (t === "at" ? "at the end of" : t);

function propRow(p, i) {
  const wrap = el("div", { className: "prop" });
  const timing = el("select", {}, ...["before", "at"].map((t) =>
    el("option", { value: t, textContent: timingLabel(t), selected: p.timing === t })));
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
    search_mode: $("search-mode").value,
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
  state.props.forEach((p) => {
    const phase = (p.phase || "").replace(/_/g, " ");
    propNames[p.id] = `${timingLabel(p.timing || "at")} ${phase} of turn ${p.turn}, ${p.english || p.id}`;
  });

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

// Normalise a result into a list of run objects, tolerating older results that
// only stored `sample_success_logs` (those were successes by construction).
function normalizeRuns(result) {
  if (result.sample_runs && result.sample_runs.length) return result.sample_runs;
  return (result.sample_success_logs || []).map((log, i) => ({
    game_index: i, success: true, timed_out: false, node_capped: false,
    hand: (log[0] && log[0].hand) || [],
    branches_explored: null, branches_considered: null,
    tree: null, tree_truncated: false, log,
  }));
}

function renderViz(result) {
  // One row per game, in game order. Replay frames drop "pass"/"pay" steps.
  const runs = normalizeRuns(result).map((r, i) => ({
    ...r,
    _i: i, // original game index — openBoard/highlightGame key on this
    frames: (r.log || []).filter((f) => {
      const d = f.desc || "";
      return !d.startsWith("pass") && !d.startsWith("pay ");
    }),
  }));

  state.vizRuns = runs;
  state.vizProps = result.properties || []; // for the tree's status circles
  state.vizGames = runs.map((r) => r.frames); // openBoard indexes into this
  state.runsSort = { key: "#", dir: 1 };

  const box = $("viz-box");
  if (!runs.length) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  renderRunsTable();
  // Open the first replayable (successful) game, if any.
  const first = runs.findIndex((r) => r.frames.length);
  $("viz-log").replaceChildren();
  if (first >= 0) { highlightGame(first); openBoard(first); }
}

function renderRunsTable() {
  const scroll = el("div", { className: "runs-scroll" }, runsTable(state.vizRuns));
  scroll.classList.toggle("scrolling", state.vizRuns.length > 10);
  $("viz-list").replaceChildren(scroll);
  highlightGame(state.vizIdx);
}

// Sort accessors per column; null = "no value" (always sorted last).
const RUN_SORTS = {
  "#": (r) => r._i,
  Result: (r) => (r.success ? 0 : r.timed_out || r.node_capped ? 1 : 2),
  Steps: (r) => (r.frames.length ? r.frames.length : null),
  Explored: (r) => r.branches_explored,
  Considered: (r) => r.branches_considered,
};

function runsTable(runs) {
  // [header, alignment-class, sortable] triples.
  const COLS = [["#", "numc", true], ["Result", "cc", true], ["Hand", "cc", false],
    ["Steps", "numc", true], ["Explored", "numc", true], ["Considered", "numc", true],
    ["Tree", "cc", false]];
  const { key, dir } = state.runsSort;
  const thead = el("thead", {}, el("tr", {},
    ...COLS.map(([h, cls, sortable]) => {
      const th = el("th", { className: cls + (sortable ? " sortable" : "") }, h);
      if (sortable) {
        const active = key === h;
        th.append(el("span", {
          className: "sortv" + (active ? " active" : ""),
          textContent: active && dir === -1 ? "▴" : "▾",
        }));
        th.title = "sort by " + h.toLowerCase();
        th.onclick = () => {
          state.runsSort = { key: h, dir: key === h ? -dir : 1 };
          renderRunsTable();
        };
      }
      return th;
    })));

  const f = RUN_SORTS[key] || RUN_SORTS["#"];
  const sorted = runs.slice().sort((a, b) => {
    const va = f(a), vb = f(b);
    if (va == null && vb == null) return a._i - b._i;
    if (va == null) return 1;   // missing values always last
    if (vb == null) return -1;
    return (va - vb) * dir || a._i - b._i;
  });

  const num = (v) => (v == null ? "—" : v.toLocaleString());
  const tbody = el("tbody");
  sorted.forEach((run) => {
    const i = run._i;
    // Result: green tick / red cross, with a suffix when the search was cut.
    const mark = run.success ? "✓" : "✗";
    const cls = run.success ? "ok" : "ko";
    let title = run.success ? "all properties satisfied"
      : "no line satisfying all properties was found";
    let suffix = "";
    if (run.timed_out) { suffix = " ⏱"; title += " — timed out before the search completed"; }
    else if (run.node_capped) { suffix = " ▦"; title += " — node cap reached before the search completed"; }

    const handIcon = el("span", { className: "hand-icon", textContent: "✋", title: "hover to see the opening hand" });
    hoverGrid(handIcon, run.hand || []);

    const treeCell = (run.tree || run.tree_gz)
      ? (() => {
          const b = el("span", { className: "icon-btn", textContent: "🌳", title: "open the explored-states tree in a new tab" });
          b.onclick = (e) => { e.stopPropagation(); openTree(run, i); };
          return b;
        })()
      : el("span", { className: "muted", textContent: "—" });

    const canReplay = run.frames.length > 0;
    const tr = el("tr", { className: "run-row" + (canReplay ? " replayable" : "") },
      el("td", { className: "numc", textContent: String(i + 1) }));
    tr.dataset.idx = i; // original game index (survives sorting)
    tr.append(
      el("td", { className: "cc status " + cls, title, textContent: mark + suffix }),
      el("td", { className: "cc" }, handIcon),
      el("td", { className: "numc", title: "steps in the winning line", textContent: canReplay ? String(run.frames.length) : "—" }),
      el("td", { className: "numc", textContent: num(run.branches_explored) }),
      el("td", { className: "numc", textContent: num(run.branches_considered) }),
      el("td", { className: "cc" }, treeCell));
    if (canReplay) {
      tr.title = "click to replay the winning line below";
      tr.onclick = () => { highlightGame(i); openBoard(i); };
    }
    tbody.append(tr);
  });
  return el("table", { className: "runs viz-runs" }, thead, tbody);
}

function highlightGame(gi) {
  state.vizIdx = gi;
  const tbody = $("viz-list").querySelector("tbody");
  if (tbody) [...tbody.children].forEach((tr) => tr.classList.toggle("active", +tr.dataset.idx === gi));
}

// Floating grid of card images shown while hovering a hand icon.
let hoverGridEl = null;
function hoverGrid(node, names) {
  const show = () => {
    if (!hoverGridEl) { hoverGridEl = el("div", { id: "hover-grid" }); document.body.append(hoverGridEl); }
    const g = hoverGridEl;
    if (!names || !names.length) {
      g.replaceChildren(el("div", { className: "gfallback", textContent: "hand not recorded" }));
    } else {
      g.replaceChildren(...names.map((n) => {
        const img = state.imageMap[n];
        return img ? el("img", { src: img, alt: n, title: n })
                   : el("div", { className: "gfallback", textContent: n });
      }));
    }
    g.style.display = "grid";
  };
  node.onmouseenter = show;
  node.onmousemove = (e) => {
    if (!hoverGridEl) return;
    const w = hoverGridEl.offsetWidth || 480, h = hoverGridEl.offsetHeight || 240;
    const x = Math.min(e.clientX + 18, window.innerWidth - w - 12);
    const y = Math.min(e.clientY + 18, window.innerHeight - h - 12);
    hoverGridEl.style.left = Math.max(8, x) + "px";
    hoverGridEl.style.top = Math.max(8, y) + "px";
  };
  node.onmouseleave = () => { if (hoverGridEl) hoverGridEl.style.display = "none"; };
}

// Inflate a gzip+base64 tree stored by the server.
async function inflateTree(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

// Open the explored-states search tree for a run in a new browser tab.
async function openTree(run, i) {
  if (!run.tree && !run.tree_gz) return;
  // window.open must happen synchronously in the click, before any await.
  const w = window.open("", "_blank");
  if (!w) { alert("Popup blocked — allow popups for this site to view the tree."); return; }
  let tree = run.tree;
  if (!tree) {
    try { tree = await inflateTree(run.tree_gz); }
    catch (e) { w.document.write("Failed to decode the stored tree: " + e); return; }
  }
  const payload = {
    tree,
    truncated: !!run.tree_truncated,
    index: i + 1,
    explored: run.branches_explored,
    considered: run.branches_considered,
    // Property list for the per-node status circles.
    props: (state.vizProps || []).map((p) => ({
      id: p.id, timing: p.timing, phase: p.phase, turn: p.turn,
      name: p.english || p.description || p.id,
    })),
  };
  w.document.open();
  w.document.write(treeHtml(payload));
  w.document.close();
}

// A self-contained HTML page that lays the tree out left-to-right as an SVG.
// The graph starts compacted to the kept hand(s); clicking a state reveals the
// subbranches initiated from it. Columns are search steps (hand / step 1..N)
// with delimiters and a sticky step header.
function treeHtml(payload) {
  const json = JSON.stringify(payload).replace(/</g, "\\u003c");
  return `<!doctype html><html><head><meta charset="utf-8">
<title>Search tree — game #${payload.index}</title>
<style>
  :root { color-scheme: dark; }
  html,body { margin:0; height:100%; background:#0f1116; color:#e6e8ee;
    font:13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  #bar { display:flex; gap:1rem; align-items:center; flex-wrap:wrap;
    padding:.6rem 1rem; border-bottom:1px solid #2e3340; background:#1c1f27; position:sticky; top:0; z-index:3; }
  #bar b { color:#d9a441; }
  #bar .k { color:#9aa3b2; }
  #bar .warn { color:#e05561; }
  #bar button { background:#232732; color:#e6e8ee; border:1px solid #2e3340; border-radius:6px; padding:.25rem .6rem; cursor:pointer; }
  #bar .legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 .25rem -1px 0; }
  #wrap { position:absolute; top:49px; bottom:0; left:0; right:0; overflow:auto; background:#0f1116; }
  /* sticky step header: scrolls horizontally with the tree, pinned vertically */
  #ruler { position:sticky; top:0; height:26px; z-index:2; background:#171a21; border-bottom:1px solid #2e3340; }
  #ruler span { position:absolute; top:5px; font-size:11px; letter-spacing:.5px; text-transform:uppercase; color:#9aa3b2; white-space:nowrap; }
  svg { display:block; }
  .colline { stroke:#232732; stroke-width:1; stroke-dasharray:4 4; }
  .edge { fill:none; stroke:#3a4150; stroke-width:1.2; }
  .edge.win { stroke:#d9a441; stroke-width:2; }
  /* one circle per property: orange = still to verify, green = verified,
     red = can no longer be verified from this state */
  .node circle { stroke:#0f1116; stroke-width:1; }
  .node circle.todo { fill:#d98f41; }
  .node circle.ok { fill:#4bbf73; }
  .node circle.ko { fill:#e05561; }
  .node circle.plain { fill:#4f8cff; }
  .node.win circle { stroke:#f2e0b8; stroke-width:1.6; }
  .node text { fill:#c5ccd8; font-size:11px; }
  .node.win text { fill:#f2e0b8; }
  .node.exp { cursor: pointer; }
  .node.exp text:hover { fill:#e6e8ee; }
</style></head><body>
<div id="bar">
  <b>Search tree · game #${payload.index}</b>
  <span><span class="k">explored </span>${payload.explored == null ? "—" : payload.explored.toLocaleString()}</span>
  <span><span class="k">considered </span>${payload.considered == null ? "—" : payload.considered.toLocaleString()}</span>
  <span class="legend"><i style="background:#4bbf73"></i>verified <i style="background:#d98f41;margin-left:.5rem"></i>to verify <i style="background:#e05561;margin-left:.5rem"></i>unreachable — one circle per property (hover it)</span>
  <span class="k">gold = winning line · click a state to show / hide its subbranches</span>
  ${payload.truncated ? '<span class="warn">tree truncated (search too large to record fully)</span>' : ""}
  <span style="flex:1"></span>
  <button onclick="setAll(true)">expand all</button><button onclick="setAll(false)">collapse all</button>
  <button onclick="zoom(1/1.2)">−</button><button onclick="zoom(1.2)">+</button><button onclick="resetView()">reset</button>
</div>
<div id="wrap"><div id="ruler"></div><svg id="svg"></svg></div>
<script>
const DATA = ${json};
const NS = "http://www.w3.org/2000/svg";
const PROPS = DATA.props || [];
const K = Math.max(1, PROPS.length);       // circles per node (one per property)
const CGAP = 13;                           // spacing between a node's circles
const R = 5, Y_GAP = 24, MX = 28, MY = 20;
const X_GAP = 260 + (K - 1) * CGAP;
// Turn order, to decide whether a property's moment is already past.
const PHASES = ["untap","upkeep","draw","precombat_main","begin_combat","declare_attackers",
  "declare_blockers","combat_damage","end_combat","postcombat_main","end_step","cleanup"];
const rankOf = (turn, phase) => turn * 100 + Math.max(0, PHASES.indexOf(phase));
const svg = document.getElementById("svg");
const ruler = document.getElementById("ruler");
// "pass" states carry no decision: hide them, grafting their subbranches
// into the parent (nested passes unroll fully; success flags are preserved,
// so the winning line stays connected).
function prunePass(n) {
  const out = [];
  for (const c of (n.children || [])) {
    prunePass(c);
    if ((c.label || "") === "pass" || (c.label || "").startsWith("pass ")) out.push(...c.children);
    else out.push(c);
  }
  n.children = out;
}
prunePass(DATA.tree);
// ✗ dead-end leaves are display noise: next to real branches they are
// dropped, and a node whose only continuation is a dead end ABSORBS it — the
// child is hidden and the node's circles take the dead end's status (its
// turn/phase/verified set), showing where the line actually died.
function tidyDead(n) {
  const kids = n.children || [];
  kids.forEach(tidyDead);
  const live = kids.filter(c => !(c.label || "").startsWith("✗"));
  if (live.length) { n.children = live; return; }
  if (kids.length) { n._dead = kids[0]; n.children = []; }
}
tidyDead(DATA.tree);
// The synthetic "game" root is hidden: the visible roots are the kept hands.
// Every state starts collapsed — except the winning line, which opens unrolled.
const roots = (DATA.tree.children && DATA.tree.children.length) ? DATA.tree.children : [DATA.tree];
function openWin(nodes) {
  for (const n of nodes) if (n.success) { n._open = true; openWin(n.children || []); }
}
openWin(roots);
let baseW = 0, baseH = 0, scale = 1;

const kidsOf = n => (n._open ? (n.children || []) : []);
function layout() {
  let yi = 0, maxDepth = 0;
  const place = (n, d) => {
    n.depth = d; if (d > maxDepth) maxDepth = d;
    const kids = kidsOf(n);
    if (!kids.length) { n.yi = yi++; }
    else { kids.forEach(c => place(c, d + 1)); n.yi = (kids[0].yi + kids[kids.length - 1].yi) / 2; }
  };
  roots.forEach(r => place(r, 0));
  return { leaves: Math.max(1, yi), maxDepth };
}
const px = n => MX + n.depth * X_GAP;
const py = n => MY + n.yi * Y_GAP;
const stepName = d => d === 0 ? "hand" : "step " + d;

function edge(a, b, win) {
  const p = document.createElementNS(NS, "path");
  const x1 = px(a) + (K - 1) * CGAP + R, y1 = py(a), x2 = px(b) - R, y2 = py(b), mx = (x1 + x2) / 2;
  p.setAttribute("d", "M" + x1 + "," + y1 + "C" + mx + "," + y1 + " " + mx + "," + y2 + " " + x2 + "," + y2);
  p.setAttribute("class", "edge" + (win ? " win" : ""));
  svg.appendChild(p);
}
// Per-property status at a node: verified (green) / dead (red: its trigger
// moment is past, it can no longer be verified from here) / pending (orange).
function propStatus(n, p) {
  if ((n.sat || []).includes(p.id)) return ["ok", "verified on this line"];
  const here = rankOf(n.turn, n.phase);
  const target = rankOf(p.turn, p.phase);
  const dead = p.timing === "before" ? here >= target : here > target;
  return dead ? ["ko", "can no longer be verified from here"] : ["todo", "still to be verified"];
}
function drawNode(n) {
  const kids = n.children || [];
  const g = document.createElementNS(NS, "g");
  g.setAttribute("class", "node" + (n.success ? " win" : "") + (kids.length ? " exp" : ""));
  // A node that absorbed its sole dead-end child shows the DEAD END's status.
  const src = n._dead || n;
  if (PROPS.length) {
    PROPS.forEach((p, i) => {
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", px(n) + i * CGAP); c.setAttribute("cy", py(n)); c.setAttribute("r", R);
      const [cls, why] = propStatus(src, p);
      c.setAttribute("class", cls);
      const tt = document.createElementNS(NS, "title");
      tt.textContent = (p.timing || "at") + " " + (p.phase || "").replace(/_/g, " ") +
        " of turn " + p.turn + ", " + p.name + " — " + why;
      c.appendChild(tt);
      g.appendChild(c);
    });
  } else { // old runs without a stored property list: a single neutral circle
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", px(n)); c.setAttribute("cy", py(n)); c.setAttribute("r", R);
    c.setAttribute("class", "plain");
    g.appendChild(c);
  }
  const t = document.createElementNS(NS, "text");
  t.setAttribute("x", px(n) + (K - 1) * CGAP + R + 4); t.setAttribute("y", py(n) + 4);
  let lbl = n.label || "";
  if (lbl.length > 36) lbl = lbl.slice(0, 35) + "…";
  // ▸N = N hidden subbranches (click to show); ▾ = expanded (click to hide).
  const marker = kids.length ? (n._open ? " ▾" : " ▸" + kids.length) : "";
  t.textContent = (n.turn ? "T" + n.turn + " " : "") + lbl + marker;
  const title = document.createElementNS(NS, "title");
  const where = n.phase && n.phase !== "start"
    ? "turn " + n.turn + ", " + n.phase.replace(/_/g, " ") : "";
  title.textContent = n.hand
    ? "Opening hand:\\n" + n.hand.map(c => "  · " + c).join("\\n")   // initial state
    : (n.label || "") + (where ? "\\n" + where : "") +
      (kids.length ? "\\n" + kids.length + " subbranch" + (kids.length > 1 ? "es" : "") : "") +
      (n._dead ? "\\n✗ line dies at turn " + n._dead.turn + ", " + (n._dead.phase || "").replace(/_/g, " ") : "");
  g.appendChild(title); // on the group: hovering anywhere but a circle shows it
  g.appendChild(t);
  if (kids.length) {
    g.addEventListener("click", () => { n._open = !n._open; render(); });
  }
  svg.appendChild(g);
}
function render() {
  const { leaves, maxDepth } = layout();
  baseW = MX * 2 + (maxDepth + 1) * X_GAP;
  baseH = MY * 2 + leaves * Y_GAP;
  svg.setAttribute("viewBox", "0 0 " + baseW + " " + baseH);
  svg.replaceChildren();
  ruler.replaceChildren();
  // Column delimiters between steps + the sticky step header.
  for (let d = 0; d <= maxDepth; d++) {
    const s = document.createElement("span");
    s.textContent = stepName(d);
    s.dataset.x = MX + d * X_GAP - R;
    ruler.appendChild(s);
    if (d > 0) {
      const l = document.createElementNS(NS, "line");
      const x = MX + d * X_GAP - 14; // just before this step's nodes
      l.setAttribute("x1", x); l.setAttribute("x2", x);
      l.setAttribute("y1", 0); l.setAttribute("y2", baseH);
      l.setAttribute("class", "colline");
      svg.appendChild(l);
    }
  }
  const walk = n => { kidsOf(n).forEach(c => { edge(n, c, n.success && c.success); walk(c); }); drawNode(n); };
  roots.forEach(walk);
  applyScale();
}
function setAll(open) {
  if (open) {
    let count = 0;
    const cnt = n => { count++; (n.children || []).forEach(cnt); };
    roots.forEach(cnt);
    if (count > 4000 && !confirm("Expand all " + count.toLocaleString() + " states? Rendering may be slow.")) return;
  }
  const w = n => { n._open = open; (n.children || []).forEach(w); };
  roots.forEach(w);
  render();
}
render();

function applyScale() {
  svg.setAttribute("width", baseW * scale);
  svg.setAttribute("height", baseH * scale);
  ruler.style.width = (baseW * scale) + "px";
  [...ruler.children].forEach(sp => { sp.style.left = (sp.dataset.x * scale) + "px"; });
}
function zoom(f, reset) {
  scale = reset ? 1 : Math.max(0.2, Math.min(4, scale * f));
  applyScale();
}
// Reset = zoom 1 + expansion back to the initial view: the winning line
// unrolled when one exists, everything collapsed otherwise.
function resetView() {
  const close = n => { n._open = false; (n.children || []).forEach(close); };
  roots.forEach(close);
  openWin(roots);
  scale = 1;
  render();
}
document.getElementById("wrap").addEventListener("wheel", (e) => {
  if (!e.ctrlKey && !e.metaKey) return;
  e.preventDefault(); zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1);
}, { passive: false });
</script></body></html>`;
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
  // Markers: render every counter kind present on the permanent, not just a
  // hardcoded few. +1/+1 and -1/-1 get P/T formatting, loyalty a shield, and
  // any other kind (charge, oil, fade, page, lore, ...) shows "N×kind".
  const counters = opts.counters || {};
  const kinds = Object.entries(counters).filter(([, v]) => v);
  if (kinds.length) {
    const row = el("div", { className: "ctr-row" });
    for (const [k, v] of kinds) {
      let label, cls = "badge ctr";
      if (k === "+1/+1") { label = `+${v}/+${v}`; }
      else if (k === "-1/-1") { label = `−${v}/−${v}`; cls += " neg"; }
      else if (k === "loyalty") { label = `⟐${v}`; }
      else { label = `${v}×${k}`; }
      row.append(el("div", { className: cls, title: `${v} ${k} counter${v === 1 ? "" : "s"}`, textContent: label }));
    }
    t.append(row);
  }
  hoverable(t, img); // enlarge on hover, like the decklist
  return t;
}

// A pile of cards stacked on top of each other, each revealing only the top
// strip of its image. Cards are added chronologically, so the last (most
// recent) one paints over the previous. Hover shows the full card.
function normalizePileItem(raw) {
  if (typeof raw === "string") {
    return { name: raw, source_name: raw, kind: "card", trigger: null, ability: raw };
  }
  const asName = (v) => {
    if (typeof v === "string") return v;
    if (v && typeof v.name === "string") return v.name;
    if (v && typeof v.label === "string") return v.label;
    return null;
  };
  const name = asName(raw?.name) || asName(raw?.label) || asName(raw?.source_name) || "unknown";
  const source = asName(raw?.source_name) || name;
  return {
    name,
    source_name: source,
    kind: typeof raw?.kind === "string" ? raw.kind : "card",
    trigger: typeof raw?.trigger === "string" ? raw.trigger : null,
    ability: typeof raw?.ability === "string" ? raw.ability : name,
  };
}

function pile(items) {
  const wrap = el("div", { className: "pile" });
  const list = items || [];
  if (!list.length) {
    wrap.append(el("div", { className: "pile-empty", textContent: "—" }));
    return wrap;
  }
  for (const raw of list) {
    const item = normalizePileItem(raw);
    const source = item.source_name || item.name;
    const img = state.imageMap[source] || state.imageMap[item.name];
    const card = el("div", { className: "pile-img", title: item.name });
    if (img) card.append(el("img", { src: img, alt: item.name, loading: "lazy" }));
    else card.append(el("div", { className: "fallback", textContent: item.name }));
    wrap.append(hoverable(card, img, {
      title: item.kind === "spell" || item.kind === "card" ? item.name : source,
      trigger: item.kind === "triggered" ? item.trigger : (item.kind === "activated" ? "Activated ability" : null),
      ability: item.kind === "spell" || item.kind === "card" ? null : item.ability,
    }));
  }
  return wrap;
}

function poolPips(pool) {
  const span = el("span", { className: "pool-pips" });
  for (const [c, n] of Object.entries(pool || {}))
    for (let k = 0; k < n; k++) span.append(el("span", { className: "pip " + c, textContent: c }));
  if (!span.childNodes.length) span.append(el("span", { className: "muted", textContent: "—" }));
  return span;
}

// A permanent tile with any auras/equipment attached to it stacked BEHIND it
// (peeking out from the top-right), so the enchanted/equipped card is on top.
function permTile(p, attachedByHost) {
  const host = tile(p.name, { tapped: p.tapped, sick: p.sick, commander: p.commander, attacking: p.attacking, counters: p.counters });
  const attached = attachedByHost[p.uid] || [];
  if (!attached.length) return host;
  const wrap = el("div", { className: "perm-stack" });
  attached.forEach((a, i) => {
    const at = tile(a.name, { tapped: a.tapped, counters: a.counters });
    at.classList.add("attached");
    at.style.transform = `translate(${(i + 1) * 13}px, ${-(i + 1) * 11}px)` + (a.tapped ? " rotate(90deg) scale(.86)" : "");
    at.title = a.name + (a.is_aura ? " (enchanting " + p.name + ")" : " (equipping " + p.name + ")");
    wrap.append(at);
  });
  host.classList.add("host");
  wrap.append(host);
  return wrap;
}

function renderBoard(f) {
  const bf = f.battlefield || [];
  // Attached permanents (auras/equipment) render behind their host, not as
  // their own top-level tile.
  const attachedByHost = {};
  const hostUids = new Set(bf.map((p) => p.uid));
  for (const p of bf) {
    if (p.attached_to != null && hostUids.has(p.attached_to)) {
      (attachedByHost[p.attached_to] ||= []).push(p);
    }
  }
  const isAttached = (p) => p.attached_to != null && hostUids.has(p.attached_to);
  const mkPerm = (p) => permTile(p, attachedByHost);
  const lands = bf.filter((p) => p.is_land && !isAttached(p)).map(mkPerm);
  const nonlands = bf.filter((p) => !p.is_land && !isAttached(p)).map(mkPerm);
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

  // MTGO-like layout: exile + graveyard piles on the left, the field in the
  // middle (lands under the other permanents), command zone + stack on the
  // right, hand across the bottom.
  const grid = el("div", { className: "board-grid" });
  grid.append(
    el("div", { className: "bzone area-left" },
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Graveyard (${(f.graveyard || []).length})` }),
        pile(f.graveyard)),
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Exile (${(f.exile || []).length})` }),
        pile(f.exile))),
    el("div", { className: "bzone area-field" },
      el("div", { className: "field-row" },
        el("div", { className: "zlabel", textContent: `Battlefield (${nonlands.length + lands.length})` }),
        el("div", { className: "tiles" }, ...nonlands)),
      el("div", { className: "field-row lands" },
        el("div", { className: "tiles" }, ...lands))),
    el("div", { className: "bzone area-right" },
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Command zone (${(f.command_zone || []).length})` }),
        pile(f.command_zone)),
      el("div", { className: "side-box" },
        el("div", { className: "zlabel", textContent: `Stack (${(f.stack || []).length})` }),
        pile(f.stack))),
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
    board,
    el("div", { className: "board-toolbar" }, desc),
    el("div", { className: "board-toolbar" }, prev, next, counter, range),
  );
  draw();
}

async function deleteSession() {
  if (!confirm(`Delete session "${state.session.name}"?`)) return;
  await api(`/api/sessions/${state.session.id}`, { method: "DELETE" });
  showHome();
}

init().catch((e) => alert("Init failed: " + e.message));
