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
  simMode: "sim",  // "sim" (random hands + mulligans) | "fixed" (hand) | "config" (full state)
  fixedHand: [],   // fixed-hand mode: chosen card names (with duplicates)
  // Fixed-config mode: a fully-specified starting state.
  fixedConfig: null,
  fcZone: "battlefield", // which zone the card picker adds to
};

// A fresh, empty fixed-config starting state.
function newFixedConfig() {
  return {
    // battlefield: [{name, tapped, counters, granted, attacking, attached_to}]
    // where attached_to is the INDEX of the host permanent (auras/equipment).
    battlefield: [],
    hand: [], graveyard: [], exile: [],
    library: [], // explicit top of the library (top first); rest random
    life: 20, opponent_life: 20, storm_count: 0, energy: 0, turn: 1, phase: "precombat_main",
    mana_pool: { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 },
    // Commander tax: times each commander has already been cast (tax = {2}×count).
    commander_cast: {},
    // Commanders removed from every area (shuffled into the library at game start).
    commander_removed: [],
  };
}

// Phases the search can start from (a decision-relevant subset, in turn order).
const FC_PHASES = [
  ["upkeep", "Upkeep"], ["draw", "Draw step"], ["precombat_main", "Precombat main"],
  ["begin_combat", "Beginning of combat"], ["declare_attackers", "Declare attackers"],
  ["postcombat_main", "Postcombat main"], ["end_step", "End step"],
];
const FC_MANA = ["W", "U", "B", "R", "G", "C"];
// Token tile tint by colour: the MTG pip colours; multicolour → gold; colorless → none.
const FC_COLOR_BG = { W: "#f7f0dc", U: "#a9cbe8", B: "#b3a9a2", R: "#eda28c", G: "#9fcf9a" };
function tokenTint(colors) {
  const cs = (colors || []).filter((c) => FC_COLOR_BG[c]);
  if (!cs.length) return null;
  return cs.length === 1 ? FC_COLOR_BG[cs[0]] : "#e6c976";
}
// Counter kinds offered as quick "+1" entries in the card context menu.
const FC_COUNTER_KINDS = ["+1/+1", "-1/-1", "loyalty", "charge"];
// Keywords that can be granted until end of turn from the card context menu.
const FC_KEYWORDS = ["flying", "first strike", "double strike", "trample",
  "lifelink", "haste", "vigilance", "deathtouch", "reach", "menace",
  "hexproof", "indestructible"];

const MAX_FIXED_HAND = 7;

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

  // Software version badge next to the title.
  if (state.meta.version) $("app-version").textContent = "v" + state.meta.version;

  // Clicking the title/logo goes home (there is no separate Home button).
  const logo = $("home-logo");
  logo.onclick = showHome;
  logo.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showHome(); } };
  $("docs-btn").onclick = () =>
    window.open("https://bastienpasdeloup.github.io/MtG-Goldfish-Simulator/", "_blank", "noopener");
  $("create-btn").onclick = doCreate;
  $("add-prop").onclick = () => { addProperty(); renderProps(); };
  $("run-btn").onclick = runSim;
  $("play-draw-toggle").onclick = (e) => {
    const b = e.currentTarget;
    const on = b.dataset.play === "1";
    b.dataset.play = on ? "0" : "1";
    b.textContent = on ? "On the draw" : "On the play";
  };
  $("instant-speed-toggle").onclick = (e) => {
    const b = e.currentTarget;
    const on = b.dataset.on === "1";
    b.dataset.on = on ? "0" : "1";
    b.textContent = on ? "Disabled" : "Enabled";
  };
  $("fake-shuffle-toggle").onclick = (e) => {
    const b = e.currentTarget;
    const on = b.dataset.on === "1";
    b.dataset.on = on ? "0" : "1";
    b.textContent = on ? "Disabled" : "Enabled";
  };
  $("stop-btn").onclick = () => api(`/api/sessions/${state.session.id}/simulate/stop`, { method: "POST" });
  $("resume-btn").onclick = resumeRun;
  $("prop-help-btn").onclick = () => $("prop-help-modal").classList.remove("hidden");
  $("prop-help-close").onclick = () => $("prop-help-modal").classList.add("hidden");
  $("prop-help-modal").onclick = (e) => { if (e.target.id === "prop-help-modal") $("prop-help-modal").classList.add("hidden"); };
  // Card names mentioned in the help text show the card image on hover
  // (fetched from Scryfall by exact name — these cards need not be in the deck).
  for (const n of document.querySelectorAll(".card-ref")) {
    hoverable(n, "https://api.scryfall.com/cards/named?exact=" +
      encodeURIComponent(n.dataset.card) + "&format=image&version=normal");
  }
  $("delete-session").onclick = deleteSession;
  $("load-run-btn").onclick = openRunsModal;
  $("run-modal-close").onclick = closeRunsModal;
  $("run-modal").onclick = (e) => { if (e.target.id === "run-modal") closeRunsModal(); };
  $("bug-btn").onclick = openBugModal;
  $("bug-download").onclick = downloadBugFile;
  $("bug-modal-close").onclick = () => $("bug-modal").classList.add("hidden");
  $("bug-modal").onclick = (e) => { if (e.target.id === "bug-modal") $("bug-modal").classList.add("hidden"); };
  $("model-btn").onclick = openModelModal;
  $("model-modal-close").onclick = () => $("model-modal").classList.add("hidden");
  $("model-modal").onclick = (e) => { if (e.target.id === "model-modal") $("model-modal").classList.add("hidden"); };
  // Escape closes whichever popup is open.
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const open = document.querySelector(".modal-overlay:not(.hidden)");
    if (open) { e.preventDefault(); open.classList.add("hidden"); }
  });
  $("sort-select").onchange = renderDeck;
  $("tab-sim").onclick = () => setSimMode("sim");
  $("tab-fixed").onclick = () => setSimMode("fixed");
  $("tab-config").onclick = () => setSimMode("config");
  $("fixed-pad").onchange = renderFixedBuilder;
  $("fixed-pad-size").oninput = renderFixedBuilder; // slot count follows the size

  // Keyboard nav while a game is open, unless the user is typing in a field
  // (or focusing the range slider, which handles arrows natively):
  //   ← / →  step through the frames of the current game (like Prev / Next)
  //   ↑ / ↓  switch to the previous / next successful (replayable) game
  document.addEventListener("keydown", (e) => {
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];
    if (!keys.includes(e.key)) return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    if (!state.vizNav) return;
    e.preventDefault();
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") state.vizNav(e.key === "ArrowLeft" ? -1 : 1);
    else stepGame(e.key === "ArrowUp" ? -1 : 1);
  });

  await loadSessionList();
  showHome();
  checkForUpdate();  // non-blocking: prompts if the repo has newer code
}

// On startup, ask the backend whether a newer release exists (compares this
// install's version against the version declared on the repo's main branch —
// works for git checkouts and ZIP downloads alike). If so, show a dismissible
// "download the latest version" popup.
async function checkForUpdate() {
  let info;
  try { info = await api("/api/version-check"); } catch { return; }
  if (!info || !info.checked || !info.update_available) return;
  // Don't nag: once dismissed for a given remote version, stay quiet until a
  // newer one appears.
  if (localStorage.getItem("mtg-update-dismissed") === (info.remote || "")) return;
  const ver = info.remote ? ` (v${info.remote})` : "";
  const bar = el("div", { id: "update-banner" },
    el("span", { className: "ic", textContent: "🔄" }),
    el("span", { className: "msg" },
      document.createTextNode(`A newer version is available${ver}. `),
      el("a", { href: info.download_url, target: "_blank", rel: "noopener", textContent: "Download latest ↗" }),
      document.createTextNode(" · "),
      el("a", { href: info.repo_url, target: "_blank", rel: "noopener", textContent: "GitHub" })),
  );
  const close = el("button", { className: "close", title: "Dismiss", textContent: "✕" });
  close.onclick = () => { localStorage.setItem("mtg-update-dismissed", info.remote || "1"); bar.remove(); };
  bar.append(close);
  document.body.append(bar);
}

function showHome() {
  closeWs();
  $("home-view").classList.remove("hidden");
  $("session-view").classList.add("hidden");
  $("bug-btn").classList.add("hidden"); // reports attach a session + run
  loadSessionList();
}

// ---------------------------------------------------------------- home
// Friendly format label ("duel_commander" -> "Duel Commander"), from /api/meta
// when available, else a title-cased fallback.
function formatName(id) {
  const f = (state.meta?.formats || []).find((x) => x.id === id);
  if (f) return f.name;
  return (id || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

async function loadSessionList() {
  const box = $("session-list");
  try {
    const { sessions } = await api("/api/sessions");
    if (!sessions.length) { box.textContent = "No sessions yet."; box.className = "muted"; return; }
    box.className = "";
    const head = el("tr", {},
      el("th", { textContent: "Deck" }),
      el("th", { textContent: "Format" }),
      el("th", { textContent: "Created" }),
      el("th", { textContent: "Last run" }),
      el("th", { className: "numc", textContent: "Runs" }));
    const rows = sessions.map((s) => {
      const fmtCell = el("td", {}, el("div", { textContent: formatName(s.format_id) }));
      if (s.commanders.length) {
        // One line per commander, each showing a card miniature on hover.
        for (const c of s.commanders) {
          const name = hoverable(el("span", { textContent: "⚔ " + c.name }), c.image);
          fmtCell.append(el("div", { className: "muted sub" }, name));
        }
      } else {
        fmtCell.append(el("div", { className: "muted sub", textContent: "no commander" }));
      }
      const tr = el("tr", { className: "session-row", title: "open this session",
                            onclick: () => openSession(s.id) },
        el("td", {}, el("b", { textContent: s.name })),
        fmtCell,
        el("td", { className: "muted nowrap", textContent: fmtDate(s.created_at).slice(0, 10) }),
        el("td", { className: "muted nowrap", textContent: s.last_run ? fmtDate(s.last_run).slice(0, 10) : "—" }),
        el("td", { className: "numc", textContent: String(s.num_results) }));
      return tr;
    });
    box.replaceChildren(el("table", { className: "sessions-table" },
      el("thead", {}, head), el("tbody", {}, ...rows)));
  } catch (e) { box.textContent = "Error: " + e.message; box.className = "err"; }
}

function homeStatus(msg, isErr) {
  const s = $("home-status");
  s.textContent = msg;
  s.className = isErr ? "err" : "muted";
}

async function doCreate() {
  // The format is inferred server-side from the deck source.
  const body = JSON.stringify({ url: $("deck-url").value, name: $("deck-name").value });
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
  state.deckFlags = payload.deck_flags || {};
  state.deckTokens = payload.tokens || [];
  // Always open with a single uninitialized property (a previous run's
  // properties can be restored explicitly via "Load previous run").
  state.props = [];
  state.imageMap = {};
  for (const c of state.cards) {
    if (c.image) state.imageMap[c.name] = c.image;
    for (const f of c.faces || []) if (f.image) state.imageMap[f.name] = f.image;
  }
  // Register token scans so tile() shows a real image in both viewers.
  state.deckTokens.forEach((t) => { if (t.image && !state.imageMap[t.name]) state.imageMap[t.name] = t.image; });
  $("home-view").classList.add("hidden");
  $("session-view").classList.remove("hidden");
  $("bug-btn").classList.remove("hidden");
  $("s-name").textContent = state.session.name;
  // One badge per commander (a partner pair shows two), each with a hover mini.
  const cmdWrap = $("s-commanders");
  cmdWrap.className = "cmd-pills";
  const cmdCards = state.cards.filter((c) => c.board === "commander");
  if (!cmdCards.length) {
    cmdWrap.replaceChildren(el("span", { className: "pill", textContent: "⚔ none" }));
  } else {
    cmdWrap.replaceChildren(...cmdCards.map((c) =>
      hoverable(el("span", { className: "pill", textContent: "⚔ " + c.name }),
                c.image || (c.faces && c.faces[0] && c.faces[0].image))));
  }
  $("s-format").textContent = formatName(state.session.format_id);
  $("s-date").textContent = "📅 " + fmtDate(state.session.created_at).slice(0, 10);
  const srcLink = $("s-source");
  const srcUrl = state.session.deck && state.session.deck.source_url;
  srcLink.classList.toggle("hidden", !srcUrl);
  if (srcUrl) {
    const src = /mtgtop8\.com/i.test(srcUrl) ? "MTGTop8" : "Moxfield";
    srcLink.href = srcUrl;
    srcLink.textContent = src + " ↗";
    srcLink.title = srcUrl;
    // Async: has the source list changed since this session imported it?
    api(`/api/sessions/${state.session.id}/deck-check`).then((r) => {
      if (r.checked && r.changed) {
        srcLink.textContent = "⚠ " + src + " ↗";
        srcLink.classList.add("warn");
        srcLink.title = "The " + src + " deck has changed since this session was imported";
      }
    }).catch(() => {});
  }
  $("s-warnings").textContent = (payload.warnings || []).join("  •  ");
  $("mulligans").value = state.session.mulligans || 0;
  renderDeck();
  addProperty(); // exactly one blank property on open
  renderProps();
  showPropWarnings([]);
  $("sim-stats").innerHTML = "";
  $("sim-seed").textContent = "";
  $("progress-box").classList.add("hidden");
  $("viz-box").classList.add("hidden");
  state.vizNav = null;
  state.fixedHand = [];
  state.fixedConfig = newFixedConfig();
  state.fcZone = "battlefield";
  setSimMode("sim");
  setResumable(null);
  $("load-run-btn").disabled = !(state.session.results || []).length;
  openWs();
}

// ---- previous-runs modal ----
const fmtDate = (s) => (s || "").slice(0, 19).replace("T", " ");

function propText(p) {
  return p.description || `${timingLabel(p.timing)} ${p.phase} of turn ${p.turn}: ${p.english}`;
}

async function openRunsModal() {
  // Fetch fresh: a run in progress already has its (live-updated) entry.
  try {
    const payload = await api(`/api/sessions/${state.session.id}`);
    state.session.results = payload.session.results || [];
  } catch {}
  const results = state.session.results || [];
  const body = $("run-modal-body");
  // Header actions: run count + "Delete all", on the same line as the title.
  const actions = $("run-modal-actions");
  if (!results.length) {
    actions.replaceChildren();
    body.replaceChildren(el("div", { className: "muted", textContent: "No runs yet." }));
  } else {
    actions.replaceChildren(
      el("span", { className: "muted", textContent: `${results.length} run${results.length > 1 ? "s" : ""}` }),
      el("button", {
        className: "danger",
        textContent: "Delete all",
        onclick: async () => {
          if (!confirm(`Delete all ${results.length} runs of this session?`)) return;
          try { await api(`/api/sessions/${state.session.id}/results`, { method: "DELETE" }); }
          catch (e) { alert("Could not delete: " + e.message); return; }
          state.session.results = [];
          $("load-run-btn").disabled = true;
          openRunsModal(); // re-render (shows "No runs yet.")
        },
      }));
    const thead = el("thead", {}, el("tr", {},
      ...["Date", "Properties", "Success", "Games", "Hand", "Mulligans", "Start", "Seed", ""].map((h) => el("th", { textContent: h }))));
    const tbody = el("tbody");
    results.slice().reverse().forEach((r) => {
      const st = r.stats || {}, cfg = r.config || {}, gr = st.games_run || 0;
      // Hand mode: fixed hands show a ✋ that previews the chosen cards.
      const fh = cfg.fixed_hand || [];
      let handCell;
      // A fixed opening hand of size H is equivalent to 7 − H mulligans (you
      // always draw 7 and bottom the rest), so show that instead of the raw 0.
      let mulligansShown = cfg.mulligans ?? 0;
      if (cfg.fixed_config) {
        // Fixed-config run: no opening hand — describe the starting state.
        mulligansShown = "—";
        const fcHand = cfg.fixed_config.hand || [];
        const icon = el("span", { className: "hand-icon", textContent: "⚙" });
        boardHover(icon, cfg.fixed_config);  // hover shows the full starting board
        handCell = el("td", {}, el("span", { textContent: "config " }), icon);
      } else if (fh.length) {
        const handSize = cfg.fixed_hand_pad_to != null ? cfg.fixed_hand_pad_to : fh.length;
        mulligansShown = Math.max(0, 7 - handSize);
        const icon = el("span", { className: "hand-icon", textContent: "✋" });
        const backs = cfg.fixed_hand_pad_to != null ? Math.max(0, cfg.fixed_hand_pad_to - fh.length) : 0;
        hoverGrid(icon, fh, backs);
        handCell = el("td", {}, el("span", { textContent: "fixed " }), icon);
      } else {
        handCell = el("td", { textContent: "random" });
      }
      const propCells = (r.properties || []).map((p) => {
        const cnt = (st.per_property || {})[p.id] ?? 0;
        const rate = gr ? (100 * cnt / gr).toFixed(0) : "0";
        return el("div", {},
          el("div", { className: "prop-line", textContent: propText(p) }),
          el("div", { className: "pp", textContent: `↳ ${cnt}/${gr} (${rate}%)` }));
      });
      const dateCell = el("td", { textContent: fmtDate(r.created_at) });
      // One status badge per run: completed / stopped / failed (⏳ while live).
      const badge = {
        running: ["⏳ running…", "pill warn"],
        done: ["completed", "pill good"],
        stopped: ["stopped", "pill warn"],
        interrupted: ["failed", "pill bad"],
      }[r.status];
      if (badge) {
        dateCell.append(el("div", {}, el("span", { className: badge[1], textContent: badge[0] })));
      }
      // Clicking the row loads the run (see tr.onclick); only Delete remains here.
      const actionsCell = el("td", { className: "run-actions" },
        el("button", {
          className: "danger",
          textContent: "Delete",
          title: "remove this run from the session",
          onclick: async (e) => {
            e.stopPropagation();
            try { await api(`/api/sessions/${state.session.id}/results/${r.id}`, { method: "DELETE" }); }
            catch (err) { alert("Could not delete: " + err.message); return; }
            state.session.results = (state.session.results || []).filter((x) => x.id !== r.id);
            $("load-run-btn").disabled = !state.session.results.length;
            openRunsModal(); // re-render the table
          },
        }));
      const tr = el("tr", {},
        dateCell,
        el("td", {}, ...(propCells.length ? propCells : [el("span", { className: "muted", textContent: "—" })])),
        el("td", {},
          el("span", { className: "big", textContent: `${((st.success_rate || 0) * 100).toFixed(1)}%` }),
          el("div", { className: "pp", textContent: `${st.successes || 0}/${gr}` })),
        el("td", { title: "games completed / games asked",
                   textContent: `${gr}/${cfg.num_games ?? "?"}` }),
        handCell,
        el("td", { textContent: String(mulligansShown) }),
        el("td", { textContent: cfg.on_the_play === false ? "draw" : "play" }),
        el("td", { textContent: String(cfg.base_seed ?? "") }),
        actionsCell);
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
  state.currentResultId = r.id; // bug reports attach the run being shown
  const cfg = r.config || {};
  $("num-games").value = cfg.num_games ?? 100;
  $("mulligans").value = cfg.mulligans ?? 0;
  $("timeout").value = cfg.timeout_per_game_s ?? 5;
  $("seed").value = cfg.base_seed ?? "";
  // Fall back to best-first if this run used a search mode that no longer exists.
  const sm = $("search-mode");
  sm.value = cfg.search_mode ?? "best_first";
  if (sm.value !== (cfg.search_mode ?? "best_first")) sm.value = "best_first";
  const isb = $("instant-speed-toggle"), ison = !!cfg.instant_speed;
  isb.dataset.on = ison ? "1" : "0";
  isb.textContent = ison ? "Enabled" : "Disabled";
  const fsb = $("fake-shuffle-toggle"), fson = !!cfg.fake_shuffle;
  fsb.dataset.on = fson ? "1" : "0";
  fsb.textContent = fson ? "Enabled" : "Disabled";
  const b = $("play-draw-toggle"), on = cfg.on_the_play !== false;
  b.dataset.play = on ? "1" : "0";
  b.textContent = on ? "On the play" : "On the draw";
  if (cfg.fixed_config) {
    state.fixedConfig = { ...newFixedConfig(), ...cfg.fixed_config };
    state.fixedConfig.mana_pool = { ...newFixedConfig().mana_pool, ...(cfg.fixed_config.mana_pool || {}) };
    setSimMode("config");
  } else if (cfg.fixed_hand && cfg.fixed_hand.length) {
    state.fixedHand = cfg.fixed_hand.slice();
    $("fixed-pad").checked = cfg.fixed_hand_pad_to != null;
    if (cfg.fixed_hand_pad_to != null) $("fixed-pad-size").value = cfg.fixed_hand_pad_to;
    setSimMode("fixed");
  } else {
    setSimMode("sim");
  }
  if (r.properties && r.properties.length) {
    state.props = r.properties.map((p) => ({ ...p }));
    renderProps();
  }
  $("sim-seed").textContent = `seed: ${cfg.base_seed}`;
  renderStats(r.stats || {});
  renderViz(r); // offers to visualize the games (shows the board viewer)
  setResumable(r); // stopped/interrupted runs with missing games offer Resume
}

// Show the Resume button when `r` is a resumable run (stopped by the user or
// interrupted by a crash, with games still missing), hide it otherwise. The
// button only appears on the tab the run was made from (fixed vs random hand).
function setResumable(r) {
  const missing = r && (((r.stats || {}).games_run || 0) < ((r.config || {}).num_games || 0));
  const ok = !!(r && missing && (r.status === "stopped" || r.status === "interrupted"));
  state.resumableId = ok ? r.id : null;
  const cfg = r ? (r.config || {}) : {};
  state.resumableMode = ok
    ? (cfg.fixed_config ? "config" : ((cfg.fixed_hand || []).length ? "fixed" : "sim"))
    : null;
  updateResumeButton();
}

function updateResumeButton() {
  const show = !!state.resumableId && state.resumableMode === state.simMode;
  $("resume-btn").classList.toggle("hidden", !show);
  // With a resumable run pending, Run means "discard that continuation and
  // start over" — say so on the button.
  $("run-btn").textContent = state.resumableId ? "Run (reset)" : "Run";
}

// Back to a clean slate — same reset a fresh Run does: clear the games table,
// the progress box and any pending Resume offer.
function resetRunState() {
  resetViz();
  $("progress-box").classList.add("hidden");
  $("sim-stats").innerHTML = "";
  $("sim-seed").textContent = "";
  state.currentResultId = null;
  setResumable(null);
}

async function resumeRun() {
  if (!state.resumableId) return;
  try {
    const r = await api(`/api/sessions/${state.session.id}/results/${state.resumableId}/resume`,
      { method: "POST" });
    state.currentResultId = r.result_id;
    $("sim-seed").textContent = `seed: ${r.seed}`;
    $("run-btn").disabled = true; $("stop-btn").disabled = false;
    $("load-run-btn").disabled = false;
    setResumable(null);
    // Keep the already-loaded rows: resumed games stream in alongside them
    // (merged by game index), so no resetViz here.
  } catch (e) { alert("Cannot resume: " + e.message); }
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
  const approx = state.cards.filter((c) => !c.implemented).length;
  $("deck-summary").textContent = `${total} cards` +
    (approx ? ` · ${approx} not yet implemented (in red)` : "");

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
  row.append(costEnd(c)); // mana cost at the far right
  return row;
}

// ---- bug report: download the session file + how-to for a GitHub issue ----
function openBugModal() {
  $("bug-github").href = (state.meta && state.meta.github_issues_url) || "#";
  $("bug-file-note").textContent = state.currentResultId
    ? "" : "(no run yet — the file will contain the session only)";
  $("bug-modal").classList.remove("hidden");
}

function downloadBugFile() {
  const q = state.currentResultId ? `?result_id=${encodeURIComponent(state.currentResultId)}` : "";
  // A plain anchor click keeps the Content-Disposition download behaviour.
  const a = el("a", { href: `/api/sessions/${state.session.id}/bug-report-file${q}` });
  document.body.append(a);
  a.click();
  a.remove();
  $("bug-file-note").textContent = "downloaded — attach it to the issue (step 4)";
}

// ---- model picker ----
// Reflect the currently selected LLM in the Properties-box badge.
function updateLlmUi() {
  const m = state.meta || {};
  const pill = $("llm-pill");
  if (pill) {
    pill.textContent = "LLM: " + m.llm_provider + (m.llm_is_real ? "" : " (offline stub)");
    pill.classList.toggle("warn", !m.llm_is_real);
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
    confidence: null,
    compile_note: null,
    manual: false,
    codeValid: null, // set to true/false by the validity check when Run is clicked
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

  const ta = el("textarea", { rows: 2, placeholder: "There are at least 2 creatures in play", value: p.english });
  // Editing the English invalidates the compiled code and its confidence/note.
  ta.oninput = () => {
    p.english = ta.value;
    p.code = null; p.confidence = null; p.compile_note = null;
    p.manual = false; p.codeValid = null;
  };
  // One Compile button per property, to the right of its text box — it compiles
  // ONLY this property (from its English).
  const compileBtn = el("button", { className: "primary", textContent: "Compile" });
  compileBtn.onclick = () => compileProperty(p, compileBtn);

  wrap.append(trigger, el("div", { className: "compose" }, ta, compileBtn));
  if (p.code) {
    // Generated code shows the model's confidence; once hand-edited it becomes
    // "Manual code" whose valid/invalid status is set when Run is clicked.
    const label = el("label");
    const note = p.compile_note
      ? el("div", {
          className: (p.confidence || "").toLowerCase() === "low" ? "compile-note warn" : "compile-note",
          textContent: p.compile_note,
        })
      : null;
    const refreshLabel = () => {
      label.replaceChildren(p.manual ? "Manual code" : "Generated code");
      if (p.manual) {
        if (p.codeValid === true)
          label.append(el("span", { className: "confidence conf-high", textContent: "valid" }));
        else if (p.codeValid === false)
          label.append(el("span", { className: "confidence conf-low", textContent: "invalid" }));
      } else if (p.confidence) {
        const c = p.confidence.toLowerCase();
        label.append(el("span", {
          className: "confidence conf-" + c,
          textContent: c + " confidence",
          title: "the model's confidence that this code matches your English",
        }));
      }
    };
    refreshLabel();
    wrap.append(label);
    if (note) wrap.append(note); // clarification / resolved-names note (generated only)

    const codeTa = el("textarea", {
      className: "code-edit",
      rows: Math.min(14, p.code.split("\n").length + 1),
      value: p.code,
      spellcheck: false,
    });
    codeTa.oninput = () => {
      p.code = codeTa.value;
      if (!p.manual) {
        p.manual = true;
        p.confidence = null;
        p.compile_note = null;
        if (note) note.remove(); // the compiler note no longer applies
      }
      p.codeValid = null; // re-checked at next Run
      refreshLabel();
    };
    wrap.append(codeTa);
  }
  return wrap;
}

async function saveProps() {
  const body = JSON.stringify({ properties: state.props, mulligans: parseInt($("mulligans").value) || 0 });
  await api(`/api/sessions/${state.session.id}/properties`, { method: "PUT", body });
}

// Show (or clear) compiler warnings — e.g. an empty property that produced no
// code — in the status line under the property list.
function showPropWarnings(warnings) {
  const box = $("prop-status");
  if (!box) return;
  if (!warnings || !warnings.length) {
    box.classList.add("hidden");
    box.replaceChildren();
    return;
  }
  box.classList.remove("hidden");
  box.replaceChildren(...warnings.map((w) => el("div", { textContent: "⚠ " + w })));
}

// Compile a SINGLE property from its English (one button per property). Only
// the associated property is affected; the others are left untouched.
async function compileProperty(p, btn) {
  await saveProps();
  if (btn) { btn.disabled = true; btn.textContent = "Compiling…"; }
  try {
    const r = await api(
      `/api/sessions/${state.session.id}/properties/${p.id}/compile`,
      { method: "POST" });
    Object.assign(p, r.property); // code/confidence/compile_note/manual for THIS prop
    p.codeValid = null;
    renderProps();
    showPropWarnings(r.warnings);
    // This property changed: the shown run no longer reflects it — clean slate.
    resetRunState();
  } catch (e) { alert("Compile failed: " + e.message); }
  finally { if (btn) { btn.disabled = false; btn.textContent = "Compile"; } }
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

// ---- fixed-hand mode ----
function setSimMode(mode) {
  state.simMode = mode;
  $("tab-sim").classList.toggle("active", mode === "sim");
  $("tab-fixed").classList.toggle("active", mode === "fixed");
  $("tab-config").classList.toggle("active", mode === "config");
  $("fixed-builder").classList.toggle("hidden", mode !== "fixed");
  $("config-builder").classList.toggle("hidden", mode !== "config");
  // Mulligans only apply to random opening hands.
  $("mull-field").classList.toggle("hidden", mode !== "sim");
  updateResumeButton(); // Resume only shows on the tab its run was made from
  if (mode === "fixed") renderFixedBuilder();
  if (mode === "config") renderConfigBuilder();
}

// Cards that can be placed in a zone: mainboard cards + the commander(s).
function placeableCards() {
  return state.cards.filter((c) => c.board === "mainboard" || c.board === "commander");
}

// Total number of copies of `name` placed across every fixed-config zone.
function fcUsage(name) {
  const fc = state.fixedConfig;
  return fc.battlefield.filter((x) => x.name === name).length
    + fc.hand.filter((x) => x === name).length
    + fc.graveyard.filter((x) => x === name).length
    + fc.exile.filter((x) => x === name).length
    + (fc.library || []).filter((x) => x === name).length;
}

const fcCardMeta = (name) => state.cards.find((c) => c.name === name) || {};
const fcTypeHead = (name) => (fcCardMeta(name).type_line || "").split("—")[0].toLowerCase();
const fcTypeFull = (name) => (fcCardMeta(name).type_line || "").toLowerCase();
const fcIsLand = (name) => !!fcCardMeta(name).is_land;
const fcIsCreature = (name) => fcTypeHead(name).includes("creature");
const fcIsPlaneswalker = (name) => fcTypeHead(name).includes("planeswalker");
const fcIsAura = (name) => fcTypeFull(name).includes("aura");
const fcIsEquipment = (name) => fcTypeFull(name).includes("equipment");
const fcCommanderCards = () => state.cards.filter((c) => c.board === "commander");
const fcIsCommander = (name) => fcCardMeta(name).board === "commander";
// A double-faced card's faces ([{name,type_line,image}, ...]); [] for single-faced.
const fcFaces = (name) => fcCardMeta(name).faces || [];
const fcIsDfc = (name) => fcFaces(name).length === 2;
// The active face's characteristics for a battlefield entry (front / back).
function fcFace(name, transformed) {
  const faces = fcFaces(name);
  const f = faces.length === 2 ? faces[transformed ? 1 : 0] : null;
  const type_line = f ? f.type_line : (fcCardMeta(name).type_line || "");
  const head = type_line.split("—")[0].toLowerCase();
  return {
    name: f ? f.name : name, type_line,
    is_land: head.includes("land"), is_creature: head.includes("creature"),
  };
}

// Whether a card of `name` may legally exist in `zone`.
function fcCanPlace(name, zone) {
  if (zone === "battlefield") {
    const t = fcTypeHead(name);
    // A DFC whose back face is a permanent (an MDFC land) can enter too.
    const ok = (h) => ["creature", "land", "artifact", "enchantment", "planeswalker", "battle"].some((k) => h.includes(k));
    return ok(t) || (fcIsDfc(name) && ok((fcFaces(name)[1].type_line || "").split("—")[0].toLowerCase()));
  }
  if (zone === "command") return fcIsCommander(name);
  return ["hand", "graveyard", "exile", "library"].includes(zone);
}

// Which face indices (0/1) of `name` are permanents that can be on the
// battlefield. A single-faced permanent is [0]; a DFC returns the permanent
// faces (an instant/sorcery face is excluded — e.g. Waterlogged Teachings).
function fcBattlefieldFaces(name) {
  const isPerm = (tl) => ["creature", "land", "artifact", "enchantment", "planeswalker", "battle"]
    .some((k) => (tl || "").split("—")[0].toLowerCase().includes(k));
  if (!fcIsDfc(name)) return isPerm(fcCardMeta(name).type_line) ? [0] : [];
  const faces = fcFaces(name);
  return [0, 1].filter((i) => isPerm(faces[i].type_line));
}

// Put a battlefield entry for `name` (on `transformed` face), initialised with
// the counters that face enters play with (planeswalker loyalty, a Saga's lore,
// Peter Parker's Camera's film, a flipped Tamiyo's loyalty, ...).
function fcPushPermanent(name, transformed = false) {
  let counters;
  if (transformed && fcIsDfc(name)) {
    const loy = parseInt((fcFaces(name)[1] || {}).loyalty, 10);
    counters = loy ? { loyalty: loy } : {};
  } else {
    counters = { ...(fcCardMeta(name).enters_counters || {}) };
  }
  const entry = {
    name, tapped: false, sick: false, counters,
    granted: [], granted_eot: [], attacking: false, attached_to: null, transformed: !!transformed,
  };
  state.fixedConfig.battlefield.push(entry);
  return state.fixedConfig.battlefield.length - 1;
}

// Finish placing a battlefield permanent: (aura) pick a host to enchant.
function fcAfterPlace(idx, name, x, y) {
  renderConfigBuilder();
  if (fcIsAura(name)) {
    const hosts = fcValidHosts(idx, "aura");
    if (!hosts.length) alert(`${name} has no permanent to enchant — added unattached.`);
    else if (hosts.length === 1) { fcPerm(idx).attached_to = hosts[0]; renderConfigBuilder(); }
    else fcChooseAttach(idx, hosts, x, y);
  }
}

// Place `name` on the battlefield. A DFC with BOTH faces permanents asks
// front/back; if only one face is a valid permanent it is used silently
// (Waterlogged Teachings → its land back). `x`/`y` position any chooser.
function fcPlaceOnBattlefield(name, x, y) {
  const valid = fcBattlefieldFaces(name);
  if (fcIsDfc(name) && valid.length >= 2) {
    const faces = fcFaces(name);
    showContextMenu(x || 300, y || 300, [
      { label: `Front — ${faces[0].name}`, onClick: () => fcAfterPlace(fcPushPermanent(name, false), name, x, y) },
      { label: `Back — ${faces[1].name}`, onClick: () => fcAfterPlace(fcPushPermanent(name, true), name, x, y) },
    ]);
    return;
  }
  const transformed = fcIsDfc(name) && valid.length === 1 && valid[0] === 1;
  fcAfterPlace(fcPushPermanent(name, transformed), name, x, y);
}

// ---- tokens (created on the battlefield, not deck cards) ----
const FC_COLOR_NAME = { W: "white", U: "blue", B: "black", R: "red", G: "green" };
const fcTokenLabel = (t) => {
  const cols = (t.colors || []).map((c) => FC_COLOR_NAME[c] || c).join("/");
  return (t.power != null ? `${t.power}/${t.toughness} ` : "") + (t.name || "Token")
    + (cols ? ` (${cols})` : " (colorless)");
};

function fcAddToken(spec) {
  state.fixedConfig.battlefield.push({
    name: spec.name || "Token", token: true,
    power: spec.power ?? null, toughness: spec.toughness ?? null,
    type_line: spec.type_line || "Token", text: spec.text || "", colors: spec.colors || [],
    tapped: false, sick: false, counters: {}, granted: [], granted_eot: [], attacking: false, attached_to: null,
  });
  renderConfigBuilder();
}

// A plain, editable token carrying just the typed name (fallback when the
// search finds nothing, or the user wants a bare token).
const fcPlainTokenSpec = (name) => ({
  name, type_line: "Token", text: "", colors: [], power: null, toughness: null, image: null,
});

// Lazily build (once) and return the token-search modal.
function fcTokenModal() {
  let ov = document.getElementById("fc-token-modal");
  if (ov) return ov;
  ov = el("div", { id: "fc-token-modal", className: "modal-overlay hidden" });
  const input = el("input", { id: "fc-token-q", type: "text", autocomplete: "off",
    placeholder: "Token name (e.g. Soldier, Treasure, Spirit)…" });
  const hint = el("div", { id: "fc-token-hint", className: "muted sub" });
  const results = el("div", { id: "fc-token-results", className: "tok-results" });
  ov.append(el("div", { className: "modal" },
    el("div", { className: "modal-head" },
      el("b", {}, "Add token"),
      el("span", { className: "spacer" }),
      el("button", { className: "modal-close", title: "Close (Esc)", textContent: "✕",
        onclick: () => ov.classList.add("hidden") })),
    el("div", { className: "modal-body" }, input, hint, results)));
  ov.onclick = (e) => { if (e.target === ov) ov.classList.add("hidden"); };
  document.body.append(ov);
  let timer = null;
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(() => fcTokenSearch(input.value), 250); };
  input.onkeydown = (e) => { if (e.key === "Enter") { clearTimeout(timer); fcTokenSearch(input.value); } };
  return ov;
}

async function fcTokenSearch(q) {
  q = (q || "").trim();
  const results = document.getElementById("fc-token-results");
  const hint = document.getElementById("fc-token-hint");
  results.replaceChildren();
  if (q.length < 2) { hint.textContent = "Type at least 2 letters to search."; return; }
  hint.textContent = "Searching…";
  let toks = [];
  try { toks = (await api("/api/tokens/search?q=" + encodeURIComponent(q))).tokens || []; }
  catch (err) { hint.textContent = "Search failed: " + err.message; return; }
  // Ignore results for a query the user has since changed.
  if ((document.getElementById("fc-token-q").value || "").trim() !== q) return;
  hint.textContent = toks.length
    ? `${toks.length} match${toks.length === 1 ? "" : "es"} — click one to add it.`
    : "No Scryfall tokens found — add a plain token below.";
  for (const spec of toks) results.append(fcTokenCandidate(spec, false));
  results.append(fcTokenCandidate(fcPlainTokenSpec(q), true));
}

function fcTokenCandidate(spec, isCustom) {
  const face = el("div", { className: "tok-cand-img" });
  if (spec.image) face.append(el("img", { src: spec.image, alt: spec.name, loading: "lazy" }));
  else {
    face.classList.add("token-card");
    const tint = tokenTint(spec.colors);
    if (tint) { face.style.boxShadow = `inset 0 0 0 3px ${tint}`; face.style.borderColor = tint; }
    face.append(el("div", { className: "tok-cand-name", textContent: spec.name }));
    if (spec.power != null) face.append(el("div", { className: "tok-cand-pt", textContent: `${spec.power}/${spec.toughness}` }));
  }
  const wrap = el("div", { className: "tok-cand" + (isCustom ? " custom" : "") }, face,
    el("div", { className: "tok-cand-label", textContent: isCustom ? `Add “${spec.name}” as a plain token` : fcTokenLabel(spec) }));
  wrap.onclick = () => fcPickToken(spec);
  return wrap;
}

function fcPickToken(spec) {
  // Register the scan so both visualizers show the real token art.
  if (spec.image && !state.imageMap[spec.name]) state.imageMap[spec.name] = spec.image;
  // Remember it so it can be re-added (quantity) from the "Add token" menu.
  state.customTokens = state.customTokens || [];
  if (!state.customTokens.some((t) => fcTokenLabel(t) === fcTokenLabel(spec))) state.customTokens.push(spec);
  fcAddToken(spec);
  const ov = document.getElementById("fc-token-modal");
  if (ov) ov.classList.add("hidden");
}

function fcAddTokenPrompt() {
  const ov = fcTokenModal();
  ov.classList.remove("hidden");
  const input = document.getElementById("fc-token-q");
  input.value = "";
  document.getElementById("fc-token-results").replaceChildren();
  document.getElementById("fc-token-hint").textContent = "Type a token name to search Scryfall.";
  setTimeout(() => input.focus(), 30);
}

// Right-click menu on empty battlefield space: add a token (deck tokens +
// previously-added custom tokens + a fresh "Add token…").
function fcBattlefieldMenu(e) {
  const all = [...(state.deckTokens || []), ...(state.customTokens || [])];
  const seen = new Set();
  const toks = all.filter((t) => { const k = fcTokenLabel(t); if (seen.has(k)) return false; seen.add(k); return true; })
    .map((t) => ({ label: fcTokenLabel(t), onClick: () => fcAddToken(t) }));
  toks.push({ sep: true }, { label: "Add token…", onClick: () => fcAddTokenPrompt() });
  showContextMenu(e.clientX, e.clientY, [{ label: "Add token", submenu: toks }]);
}

// Add a card to a zone (from the picker, via drag-and-drop). Non-battlefield
// zones always use the front face.
function fcAddToZone(name, zone, x, y) {
  // Placing/dragging a commander anywhere un-removes it (it's back in an area).
  const rem = state.fixedConfig.commander_removed || [];
  const ri = rem.indexOf(name);
  if (ri >= 0) rem.splice(ri, 1);
  if (zone === "command") { renderConfigBuilder(); return; }  // commanders live here by default
  const card = placeableCards().find((c) => c.name === name);
  if (!card || fcUsage(name) >= card.quantity || !fcCanPlace(name, zone)) return;
  if (zone === "battlefield") { fcPlaceOnBattlefield(name, x, y); return; }
  state.fixedConfig[zone].push(name);
  renderConfigBuilder();
}

// Commit a live drag-reorder: read the new DOM order of a pile (each card
// carries its ORIGINAL model index in data-idx) and rebuild the zone's list to
// match. For the library this changes which card is on top (front = top).
function fcCommitPileOrder(zone, wrap) {
  const orig = state.fixedConfig[zone];
  if (!Array.isArray(orig)) return;
  const order = Array.prototype.map.call(wrap.querySelectorAll(".pile-img"), (c) => +c.dataset.idx);
  const next = order.map((i) => orig[i]).filter((v) => v !== undefined);
  if (next.length === orig.length) state.fixedConfig[zone] = next;
  renderConfigBuilder();
}

// Move a card already in the editor from one zone to another (only if legal).
// The command zone is a pseudo-zone: a commander not placed elsewhere shows
// there, so moving OUT of "command" places it, moving IN just frees it.
function fcMoveCard(fromZone, fromIdx, toZone, x, y) {
  if (fromZone === toZone) return;
  const fc = state.fixedConfig;
  let name;
  if (fromZone === "command") {
    name = (fcFrame().command_zone || [])[fromIdx];
    if (!name || !fcCanPlace(name, toZone) || toZone === "command") return;
    return fcAddToZone(name, toZone, x, y);  // place the unplaced commander
  }
  // A token dragged off the battlefield ceases to exist (it can't go to another zone).
  if (fromZone === "battlefield" && (fc.battlefield[fromIdx] || {}).token) {
    if (toZone !== "battlefield") fcRemove("battlefield", fromIdx);
    return;
  }
  name = fromZone === "battlefield" ? (fc.battlefield[fromIdx] || {}).name : fc[fromZone][fromIdx];
  if (!name || !fcCanPlace(name, toZone)) return;
  fcRemove(fromZone, fromIdx);  // re-renders; fixes attachment indices
  if (toZone === "command") { renderConfigBuilder(); return; }  // returns to command zone
  if (toZone === "battlefield") fcPlaceOnBattlefield(name, x, y);  // DFC front/back checked here too
  else { fc[toZone].push(name); renderConfigBuilder(); }
}

// Battlefield indices a card at `idx` may attach to. Auras go on any other
// permanent; Equipment attaches to creatures.
function fcValidHosts(idx, kind) {
  const bf = state.fixedConfig.battlefield;
  return bf.map((b, i) => i).filter((i) =>
    i !== idx && (kind === "equipment" ? fcIsCreature(bf[i].name) : true));
}

function fcChooseAttach(idx, hosts, x, y) {
  const bf = state.fixedConfig.battlefield;
  const items = hosts.map((h) => ({
    label: `Attach to ${bf[h].name}`,
    onClick: () => { bf[idx].attached_to = h; renderConfigBuilder(); },
  }));
  items.push({ sep: true }, { label: "Leave unattached", onClick: () => {} });
  showContextMenu(x || 300, y || 300, items);
}

function fcRemove(zone, idx) {
  if (zone === "battlefield") {
    state.fixedConfig.battlefield.splice(idx, 1);
    // Fix up attachment indices after the splice.
    state.fixedConfig.battlefield.forEach((b) => {
      if (b.attached_to === idx) b.attached_to = null;
      else if (b.attached_to != null && b.attached_to > idx) b.attached_to -= 1;
    });
  } else {
    state.fixedConfig[zone].splice(idx, 1);
  }
  renderConfigBuilder();
}

// Build a replay-style board frame from the fixed-config model, so the editor
// reuses the exact game-replay layout (renderBoard). uid = the model index
// (`_idx`), so attachments (attached_to = host index) line up with host uids.
function fcFrame() {
  const fc = state.fixedConfig;
  const combat = fc.phase === "declare_attackers" || fc.phase === "begin_combat";
  const battlefield = fc.battlefield.map((it, i) => {
    const common = {
      uid: i, _idx: i, tapped: !!it.tapped, sick: !!it.sick,
      counters: it.counters || {}, granted: [...(it.granted || []), ...(it.granted_eot || [])],
      is_lander: false, attached_to: it.attached_to,
    };
    if (it.token) {  // a token — composed tile (no card image), tinted by colour
      const head = (it.type_line || "").split("—")[0].toLowerCase();
      const isCreature = head.includes("creature");
      return {
        ...common, name: it.name, token: true, type_line: it.type_line, text: it.text || "",
        colors: it.colors || [],
        power: isCreature ? (it.power ?? 0) : null, toughness: isCreature ? (it.toughness ?? 0) : null,
        is_land: head.includes("land"), is_creature: isCreature, commander: false,
        attacking: !!it.attacking && combat && isCreature,
      };
    }
    const face = fcFace(it.name, it.transformed);  // active (front/back) face
    return {
      ...common, name: face.name, commander: fcIsCommander(it.name), token: false,
      attacking: !!it.attacking && combat && face.is_creature,
      is_land: face.is_land, is_creature: face.is_creature, is_aura: fcIsAura(it.name),
    };
  });
  const removed = fc.commander_removed || [];
  const command = [];
  fcCommanderCards().forEach((c) => {
    if (removed.includes(c.name)) return;  // shuffled into the library — not here
    for (let k = 0; k < Math.max(0, c.quantity - fcUsage(c.name)); k++) command.push(c.name);
  });
  const library = mainboardCards().reduce(
    (s, c) => s + Math.max(0, c.quantity - fcUsage(c.name)), 0);
  const phaseLabel = (FC_PHASES.find(([v]) => v === fc.phase) || [null, fc.phase])[1];
  return {
    battlefield, hand: fc.hand.slice(), graveyard: fc.graveyard.slice(),
    exile: fc.exile.slice(), command_zone: command, stack: [],
    library_top: (fc.library || []).slice(),  // editor: the set top of the library
    turn: fc.turn, phase: phaseLabel, desc: "",
    life: fc.life, opponent_life: fc.opponent_life, library,
    counters: { storm: fc.storm_count }, mana_pool: fc.mana_pool, energy: fc.energy || 0,
  };
}

// ---- global-state setters (inline number-input controls in the header) ----
function fcSet(field, value) {
  const fc = state.fixedConfig;
  value = parseInt(value, 10);
  if (isNaN(value)) value = 0;
  if (field === "storm") fc.storm_count = Math.max(0, value);
  else if (field === "energy") fc.energy = Math.max(0, value);
  else fc[field] = value;  // life / opponent_life may go negative
  renderConfigBuilder();
}
function fcSetMana(sym, value) {
  value = parseInt(value, 10);
  state.fixedConfig.mana_pool[sym] = Math.max(0, isNaN(value) ? 0 : value);
  renderConfigBuilder();
}
function fcSetTurn(value) {
  value = parseInt(value, 10);
  state.fixedConfig.turn = Math.max(1, isNaN(value) ? 1 : value);
  renderConfigBuilder();
}
function fcAdjustPhase(delta) {
  const fc = state.fixedConfig;
  let i = FC_PHASES.findIndex(([v]) => v === fc.phase);
  if (i < 0) i = 0;
  i = Math.min(FC_PHASES.length - 1, Math.max(0, i + delta));
  fc.phase = FC_PHASES[i][0];
  renderConfigBuilder();
}
function fcSetTax(name, value) {
  const cc = state.fixedConfig.commander_cast;
  value = Math.max(0, parseInt(value, 10) || 0);
  if (value) cc[name] = value; else delete cc[name];
  renderConfigBuilder();
}

// ---- editor actions on a battlefield permanent (by model index) ----
const fcPerm = (idx) => state.fixedConfig.battlefield[idx];

function fcTogglePermTap(p) {
  const it = fcPerm(p._idx);
  if (it) { it.tapped = !it.tapped; renderConfigBuilder(); }
}
function fcSetCounter(idx, kind, value) {
  const it = fcPerm(idx); if (!it) return;
  it.counters = it.counters || {};
  if (value) it.counters[kind] = value; else delete it.counters[kind];
  renderConfigBuilder();
}

// The counter kinds to offer for a card: the ones its rules reference (from the
// server-computed `counter_kinds`) plus any kind already present on it.
function fcCounterKinds(it) {
  const kinds = (fcCardMeta(it.name).counter_kinds || []).slice();
  // Tokens aren't deck cards: offer +1/+1 & −1/−1 for creature tokens.
  if (it.token && (it.type_line || "").split("—")[0].toLowerCase().includes("creature")) {
    ["+1/+1", "-1/-1"].forEach((k) => { if (!kinds.includes(k)) kinds.push(k); });
  }
  Object.keys(it.counters || {}).forEach((k) => { if (!kinds.includes(k)) kinds.push(k); });
  return kinds;
}

// Right-click menu on a battlefield permanent — entries are gated by the
// card's type and the current phase (game-rules-valid actions only).
function fcPermMenu(p, e) {
  const idx = p._idx;
  const it = fcPerm(idx); if (!it) return;
  const fc = state.fixedConfig;
  // A token is not a deck card — derive its face from the entry's type line.
  const face = it.token
    ? { name: it.name, is_creature: (it.type_line || "").split("—")[0].toLowerCase().includes("creature"),
        is_land: (it.type_line || "").split("—")[0].toLowerCase().includes("land") }
    : fcFace(it.name, it.transformed);
  const items = [{ label: it.tapped ? "Untap" : "Tap", onClick: () => fcTogglePermTap(p) }];

  // Flip — double-faced cards switch between their front and back face.
  if (!it.token && fcIsDfc(it.name)) {
    const other = fcFaces(it.name)[it.transformed ? 0 : 1];
    items.push({ label: `Flip to ${other.name}`, onClick: () => { it.transformed = !it.transformed; renderConfigBuilder(); } });
  }

  // Summoning sickness — creatures (incl. creature tokens).
  if (face.is_creature) {
    items.push({
      label: "Summoning sickness", checked: !!it.sick,
      onClick: () => { it.sick = !it.sick; renderConfigBuilder(); },
    });
  }

  // Declare as attacker — only a creature, only in the declare-attackers step.
  if (face.is_creature && fc.phase === "declare_attackers") {
    items.push({
      label: it.attacking ? "Remove from combat" : "Declare as attacker",
      onClick: () => { it.attacking = !it.attacking; if (it.attacking) it.tapped = true; renderConfigBuilder(); },
    });
  }

  // Counters — one "kind [−] N [+]" stepper per counter type this card uses
  // (initialised to its enters-with count; "Add counter type…" allows custom).
  const cval = (k) => (it.counters && it.counters[k] != null) ? it.counters[k] : 0;
  const counterItems = fcCounterKinds(it).map((k) => ({ stepper: {
    label: k, get: () => cval(k),
    dec: () => fcSetCounter(idx, k, Math.max(0, cval(k) - 1)),
    inc: () => fcSetCounter(idx, k, cval(k) + 1),
  } }));
  counterItems.push({
    label: "Add counter type…", onClick: () => {
      const kind = (prompt("Counter kind (e.g. charge, oil, page):", "") || "").trim();
      if (kind) fcSetCounter(idx, kind, (it.counters && it.counters[kind] || 0) + 1);
    },
  });
  items.push({ label: "Add counter", submenu: counterItems });

  // Add keyword — one row per keyword with its OWN "until end of turn" checkbox
  // (permanent grant vs granted_eot); creatures only.
  if (face.is_creature) {
    it.granted = it.granted || []; it.granted_eot = it.granted_eot || [];
    const has = (kw) => it.granted.includes(kw) || it.granted_eot.includes(kw);
    const drop = (kw) => {
      [it.granted, it.granted_eot].forEach((arr) => { const j = arr.indexOf(kw); if (j >= 0) arr.splice(j, 1); });
    };
    // The standard keywords plus any custom one already granted (so its EOT can
    // be toggled and it can be removed).
    const kwList = FC_KEYWORDS.slice();
    [...it.granted, ...it.granted_eot].forEach((kw) => { if (!kwList.includes(kw)) kwList.push(kw); });
    const kwItems = kwList.map((kw) => ({
      kwrow: {
        label: kw,
        checked: () => has(kw),
        eot: () => it.granted_eot.includes(kw),
        onToggle: () => { if (has(kw)) drop(kw); else it.granted.push(kw); renderConfigBuilder(); },
        onEot: () => {
          const eot = it.granted_eot.includes(kw);
          drop(kw);
          (eot ? it.granted : it.granted_eot).push(kw);  // toggle bucket (grants it if absent)
          renderConfigBuilder();
        },
      },
    }));
    kwItems.push({ sep: true }, {
      label: "Add keyword…", onClick: () => {
        const kw = (prompt("Keyword to grant (e.g. flying, deathtouch):", "") || "").trim().toLowerCase();
        if (kw && !has(kw)) { it.granted.push(kw); renderConfigBuilder(); }
      },
    });
    items.push({ label: "Add keyword", submenu: kwItems });
  }

  // Attach — equipment onto a creature (or move/unattach it).
  if (fcIsEquipment(it.name)) {
    const hosts = fcValidHosts(idx, "equipment");
    const sub = hosts.map((h) => ({
      label: fcPerm(h).name, checked: it.attached_to === h,
      onClick: () => { it.attached_to = h; renderConfigBuilder(); },
    }));
    if (!sub.length) sub.push({ label: "(no creature in play)", onClick: () => {} });
    if (it.attached_to != null) sub.push({ sep: true },
      { label: "Unattach", onClick: () => { it.attached_to = null; renderConfigBuilder(); } });
    items.push({ label: "Attach to", submenu: sub });
  }

  items.push({ sep: true }, { label: "Remove from battlefield", onClick: () => fcRemove("battlefield", idx) });
  // A commander can always be shuffled into the library, wherever it is.
  if (!it.token && fcIsCommander(it.name)) {
    items.push({ label: "Shuffle to library", onClick: () => fcShuffleCommander(it.name) });
  }
  showContextMenu(e.clientX, e.clientY, items);
}

// Right-click menu on a hand / graveyard / exile card.
function fcZoneMenu(zone, idx, name, e) {
  const items = [{ label: `Remove ${name} from ${zone}`, onClick: () => fcRemove(zone, idx) }];
  if (fcIsCommander(name)) {
    items.push({ label: "Shuffle to library", onClick: () => fcShuffleCommander(name) });
  }
  showContextMenu(e.clientX, e.clientY, items);
}

// Shuffle a commander into the library: remove it from every area and mark it
// removed (the backend shuffles it into the deck at game start; the picker
// shows it as 0). Available wherever the commander is.
function fcShuffleCommander(name) {
  const fc = state.fixedConfig;
  const bi = fc.battlefield.findIndex((b) => !b.token && b.name === name);
  if (bi >= 0) {
    fc.battlefield.splice(bi, 1);
    fc.battlefield.forEach((b) => {
      if (b.attached_to === bi) b.attached_to = null;
      else if (b.attached_to != null && b.attached_to > bi) b.attached_to -= 1;
    });
  }
  ["hand", "graveyard", "exile", "library"].forEach((z) => {
    fc[z] = (fc[z] || []).filter((n) => n !== name);
  });
  if (!fc.commander_removed.includes(name)) fc.commander_removed.push(name);
  renderConfigBuilder();
}

// Right-click menu on a commander in the command zone.
function fcCommandMenu(idx, name, e) {
  showContextMenu(e.clientX, e.clientY, [
    { label: "Shuffle to library", onClick: () => fcShuffleCommander(name) },
  ]);
}

// ---- lightweight right-click context menu (with one level of submenus) ----
function closeContextMenu() {
  document.querySelectorAll(".ctx-menu").forEach((m) => m.remove());
  document.removeEventListener("click", closeContextMenu);
  document.removeEventListener("keydown", ctxEsc);
}
function ctxEsc(e) { if (e.key === "Escape") closeContextMenu(); }

function buildMenu(items) {
  const menu = el("div", { className: "ctx-menu" });
  items.forEach((it) => {
    if (it.sep) { menu.append(el("div", { className: "ctx-sep" })); return; }
    // A stepper row: "label [−] value [+]" — the buttons adjust without closing.
    if (it.stepper) {
      const s = it.stepper;
      const valEl = el("b", { className: "ctx-val", textContent: String(s.get()) });
      const btn = (sym, fn) => {
        const b = el("button", { className: "ctx-step", textContent: sym });
        b.onclick = (ev) => { ev.stopPropagation(); fn(); valEl.textContent = String(s.get()); };
        return b;
      };
      menu.append(el("div", { className: "ctx-item ctx-stepper" },
        el("span", { className: "ctx-label", textContent: s.label }),
        btn("−", s.dec), valEl, btn("+", s.inc)));
      return;
    }
    // A keyword row: "[✓] keyword ......... [EOT]" — grant + per-entry until-EOT.
    if (it.kwrow) {
      const k = it.kwrow;
      const chk = el("span", { className: "ctx-check", textContent: k.checked() ? "✓" : "" });
      const eot = el("button", { className: "ctx-eot" + (k.eot() ? " on" : ""), title: "until end of turn", textContent: "EOT" });
      const row = el("div", { className: "ctx-item ctx-kwrow" }, chk,
        el("span", { className: "ctx-label", textContent: k.label }), eot);
      const sync = () => { chk.textContent = k.checked() ? "✓" : ""; eot.classList.toggle("on", k.eot()); };
      row.onclick = (ev) => { ev.stopPropagation(); k.onToggle(); sync(); };
      eot.onclick = (ev) => { ev.stopPropagation(); k.onEot(); sync(); };
      menu.append(row);
      return;
    }
    const check = el("span", { className: "ctx-check", textContent: it.checked ? "✓" : "" });
    const row = el("div", { className: "ctx-item" + (it.submenu ? " has-sub" : "") },
      check, el("span", { className: "ctx-label", textContent: it.label }));
    if (it.submenu) {
      row.append(el("span", { className: "ctx-arrow", textContent: "▸" }));
      let sub = null;
      row.onmouseenter = () => { if (!sub) { sub = buildMenu(it.submenu); sub.classList.add("ctx-submenu"); row.append(sub); } };
      row.onmouseleave = () => { if (sub) { sub.remove(); sub = null; } };
    } else if (it.keepOpen && it.onClick) {
      // A checkbox that toggles in place (menu stays open); onClick returns the
      // new checked state.
      row.onclick = (ev) => { ev.stopPropagation(); check.textContent = it.onClick() ? "✓" : ""; };
    } else if (it.onClick) {
      row.onclick = (ev) => { ev.stopPropagation(); it.onClick(); closeContextMenu(); };
    }
    menu.append(row);
  });
  return menu;
}

function showContextMenu(x, y, items) {
  closeContextMenu();
  const menu = buildMenu(items);
  menu.style.left = x + "px";
  menu.style.top = y + "px";
  document.body.append(menu);
  const r = menu.getBoundingClientRect();
  if (r.right > innerWidth) menu.style.left = Math.max(0, innerWidth - r.width - 4) + "px";
  if (r.bottom > innerHeight) menu.style.top = Math.max(0, innerHeight - r.height - 4) + "px";
  setTimeout(() => document.addEventListener("click", closeContextMenu), 0);
  document.addEventListener("keydown", ctxEsc);
}

// Kept for runSim's call site; the model is now the source of truth (globals
// are edited inline via the board's +/- controls), so there is nothing to read.
function fcSyncGlobals() {}

function renderConfigBuilder() {
  if (!state.fixedConfig) state.fixedConfig = newFixedConfig();
  const fc = state.fixedConfig;

  const commanderTax = fcCommanderCards().map((c) => ({
    name: c.name, count: Math.max(0, parseInt(fc.commander_cast[c.name], 10) || 0),
  }));

  // The board — the SAME layout as game replay, made interactive: edit globals
  // with the +/- controls, click a battlefield card to tap, right-click any
  // card for the full menu, and drag cards (from the picker or between zones).
  $("fc-zones").replaceChildren(el("div", { className: "board fc-board" },
    renderBoard(fcFrame(), {
      editable: true,
      onPermClick: fcTogglePermTap,
      onPermMenu: fcPermMenu,
      onZoneMenu: fcZoneMenu,
      onCommandMenu: fcCommandMenu,
      onFieldMenu: fcBattlefieldMenu,
      onSetTurn: fcSetTurn,
      onPhase: fcAdjustPhase,
      onSet: fcSet,
      onSetMana: fcSetMana,
      commanderTax,
      onSetTax: fcSetTax,
    })));
  // Wire the drop zones tagged by renderBoard (a picker drop = add by name; a
  // tile/pile drop carries JSON {move,from,idx,name} = move between zones).
  $("fc-zones").querySelectorAll("[data-drop]").forEach((node) => {
    node.ondragover = (ev) => { ev.preventDefault(); node.classList.add("drop-hover"); };
    // Only drop the highlight when the cursor truly leaves the zone — not when
    // it crosses between the zone's own cards (which would flicker mid-reorder).
    node.ondragleave = (ev) => { if (!node.contains(ev.relatedTarget)) node.classList.remove("drop-hover"); };
    node.ondrop = (ev) => {
      ev.preventDefault();
      node.classList.remove("drop-hover");
      const raw = ev.dataTransfer.getData("text/plain");
      if (!raw) return;
      let data = null;
      try { data = JSON.parse(raw); } catch (_) { /* plain card name from the picker */ }
      if (data && data.move) fcMoveCard(data.from, data.idx, node.dataset.drop);
      else fcAddToZone(raw, node.dataset.drop, ev.clientX, ev.clientY);
    };
  });

  // Card picker — each row is draggable onto a zone (drops add the card).
  const picker = $("fc-card-picker");
  picker.replaceChildren();
  placeableCards().slice().sort((a, b) => a.name.localeCompare(b.name)).forEach((c) => {
    // A commander is normally in the command zone/in play (shown 1/grey). Once
    // "removed from any area" it shows 0 and is draggable back into a zone.
    const isCmd = c.board === "commander";
    const removed = isCmd && (state.fixedConfig.commander_removed || []).includes(c.name);
    const n = isCmd ? (removed ? 0 : c.quantity) : fcUsage(c.name);
    const full = isCmd ? !removed : n >= c.quantity;
    const nm = el("span", { className: "picker-name" }, c.name);
    hoverable(nm, c.image);
    const row = el("div", {
      className: "picker-row draggable" + (n ? " chosen" : "") + (full ? " full" : ""),
      draggable: !full,
      title: isCmd
        ? (removed ? "commander removed — drag onto a zone to bring it back"
          : "commander — in the command zone (right-click it to remove)")
        : full ? "all copies placed" : "drag onto a zone to add",
    }, el("span", { className: "picker-count", textContent: String(n) }),
      nm, el("span", { className: "muted picker-qty", textContent: `/${c.quantity}` }));
    if (!full) {
      row.ondragstart = (ev) => { ev.dataTransfer.setData("text/plain", c.name); ev.dataTransfer.effectAllowed = "copy"; };
    }
    picker.append(row);
  });
}

// Only mainboard cards are drawable into an opening hand (commanders live in
// the command zone, sideboard/companions aren't in the library).
function mainboardCards() {
  return state.cards.filter((c) => c.board === "mainboard");
}
const fixedHandCount = (name) => state.fixedHand.filter((n) => n === name).length;

function addToFixedHand(name) {
  const card = mainboardCards().find((c) => c.name === name);
  if (!card || state.fixedHand.length >= MAX_FIXED_HAND || fixedHandCount(name) >= card.quantity) return;
  state.fixedHand.push(name);
  renderFixedBuilder();
}
function removeFromFixedHand(name) {
  const i = state.fixedHand.lastIndexOf(name);
  if (i >= 0) state.fixedHand.splice(i, 1);
  renderFixedBuilder();
}

function renderFixedBuilder() {
  const total = state.fixedHand.length;
  // Padding option: the size input appears only when ticked, and can't ask
  // for fewer cards than are already chosen.
  const padding = $("fixed-pad").checked;
  $("fixed-pad-size-wrap").classList.toggle("hidden", !padding);
  const size = $("fixed-pad-size");
  size.min = Math.max(1, total);
  if (+size.value < +size.min) size.value = size.min;

  // The hand shows as many miniatures as the final hand will hold: the
  // chosen cards, then card backs up to the padded size (no padding = just
  // the chosen cards). Clicking a card removes it.
  const slots = padding ? Math.max(total, parseInt(size.value) || MAX_FIXED_HAND) : total;
  $("fixed-count").textContent = padding ? `(${total}/${slots})` : `(${total})`;
  const minis = $("fixed-hand-minis");
  minis.replaceChildren();
  if (!slots) minis.append(el("span", { className: "muted", textContent: "empty — add cards below" }));
  for (let i = 0; i < slots; i++) {
    const name = state.fixedHand[i];
    if (!name) {
      minis.append(el("div", { className: "mini back", title: "random card — added when the game starts" }));
      continue;
    }
    const m = el("div", { className: "mini", title: `${name} — click to remove` });
    const img = state.imageMap[name];
    if (img) m.append(el("img", { src: img, alt: name, loading: "lazy" }));
    else m.append(el("div", { className: "fallback", textContent: name }));
    m.onclick = () => { state.fixedHand.splice(i, 1); renderFixedBuilder(); };
    hoverable(m, img);
    minis.append(m);
  }

  // Picker: one stepper row per distinct mainboard card.
  const picker = $("fixed-card-picker");
  picker.replaceChildren();
  const full = total >= MAX_FIXED_HAND;
  mainboardCards().slice().sort((a, b) => a.name.localeCompare(b.name)).forEach((c) => {
    const n = fixedHandCount(c.name);
    const minus = el("button", { className: "step", textContent: "−" });
    minus.disabled = n <= 0;
    minus.onclick = () => removeFromFixedHand(c.name);
    const plus = el("button", { className: "step", textContent: "+" });
    plus.disabled = full || n >= c.quantity;
    plus.onclick = () => addToFixedHand(c.name);
    const nm = el("span", { className: "picker-name" }, c.name);
    hoverable(nm, c.image);
    picker.append(el("div", { className: "picker-row" + (n ? " chosen" : "") },
      minus, el("span", { className: "picker-count", textContent: String(n) }), plus,
      nm, el("span", { className: "muted picker-qty", textContent: `/${c.quantity}` })));
  });
}

async function runSim() {
  const fixed = state.simMode === "fixed";
  const config = state.simMode === "config";
  if (fixed && !state.fixedHand.length) { alert("Add at least one card to the fixed hand first."); return; }
  if (config) fcSyncGlobals();  // capture the current global fields into the model
  // Run does NOT recompile (so hand-edited code is used as-is) — it only checks
  // that every enabled property has valid, runnable code. Persist first so the
  // validity check sees the current (possibly hand-edited) code.
  await saveProps();
  let v;
  try {
    v = await api(`/api/sessions/${state.session.id}/properties/validate`, { method: "POST" });
  } catch (e) { alert("Validation failed: " + e.message); return; }
  // Stamp each property's valid/invalid status (shown on hand-edited code).
  state.props.forEach((p) => {
    const r = v.results[p.id];
    p.codeValid = r ? r.valid : (p.enabled ? p.codeValid : null);
  });
  renderProps();
  if (!v.ok) {
    showPropWarnings(v.warnings);
    alert("Cannot run — some properties need valid code first:\n\n" + v.warnings.join("\n"));
    return;
  }
  showPropWarnings(null);
  const seedField = $("seed").value.trim();
  const body = JSON.stringify({
    num_games: parseInt($("num-games").value) || 100,
    timeout_per_game_s: parseFloat($("timeout").value) || 5,
    mulligans: state.simMode === "sim" ? (parseInt($("mulligans").value) || 0) : 0,
    on_the_play: $("play-draw-toggle").dataset.play === "1",
    base_seed: seedField === "" ? null : parseInt(seedField),
    search_mode: $("search-mode").value,
    instant_speed: $("instant-speed-toggle").dataset.on === "1",
    fake_shuffle: $("fake-shuffle-toggle").dataset.on === "1",
    fixed_hand: fixed ? state.fixedHand.slice() : null,
    fixed_hand_pad_to: fixed && $("fixed-pad").checked
      ? Math.max(state.fixedHand.length, parseInt($("fixed-pad-size").value) || 7)
      : null,
    fixed_config: config ? JSON.parse(JSON.stringify(state.fixedConfig)) : null,
  });
  try {
    const r = await api(`/api/sessions/${state.session.id}/simulate`, { method: "POST", body });
    state.currentResultId = r.result_id;
    $("sim-seed").textContent = `seed: ${r.seed}` + (seedField === "" ? " (random)" : "");
    $("run-btn").disabled = true; $("stop-btn").disabled = false;
    setResumable(null);
    // The run's entry exists (and updates) in "previous runs" from this moment.
    $("load-run-btn").disabled = false;
    resetViz();
    renderStats({ total_games: parseInt($("num-games").value) || 100, games_run: 0, successes: 0, timeouts: 0, success_rate: 0, per_property: {} });
  } catch (e) { alert("Cannot start: " + e.message); }
}

function onSimEvent(msg) {
  if (msg.type === "progress") {
    renderStats(msg.stats);
    if (msg.run) appendLiveRun(msg.run); // populate the games table on the fly
  } else if (msg.type === "done") {
    $("run-btn").disabled = false; $("stop-btn").disabled = true;
    // msg.result is LEAN — no per-game rows (each was already streamed live
    // via a progress event; resending them all could reach hundreds of MB and
    // crash the tab). The games table already shows everything: keep it, and
    // just finalize the stats, the stored entry and the Resume offer.
    const rs = state.session.results = state.session.results || [];
    const at = rs.findIndex((x) => x.id === msg.result.id);
    if (at >= 0) rs[at] = msg.result; else rs.push(msg.result);
    $("load-run-btn").disabled = false;
    setResumable(msg.result); // a stopped/failed, incomplete run offers Resume
    $("sim-seed").textContent = `seed: ${msg.result.config?.base_seed}`;
    renderStats(msg.result.stats);
  }
}

function renderStats(stats) {
  $("progress-box").classList.remove("hidden");
  const box = $("sim-stats");
  const pct = (stats.success_rate * 100).toFixed(1);
  const progress = stats.total_games ? (stats.games_run / stats.total_games) * 100 : 0;
  // Failures = games that finished the search without success and without
  // timing out (a genuine "no line exists"), kept separate from timeouts.
  const failures = Math.max(0, (stats.games_run || 0) - (stats.successes || 0) - (stats.timeouts || 0));
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
      stat("Failures", failures),
      stat("Timeouts", stats.timeouts),
      stat("Games run", stats.games_run)),
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
    game_index: i, success: true, timed_out: false,
    hand: (log[0] && log[0].hand) || [],
    branches_explored: null, branches_considered: null,
    tree: null, tree_truncated: false, log,
  }));
}

// Turn one raw run (from a result or a live progress event) into a viz row.
// `_i` is the original game index — openBoard/highlightGame/vizGames key on it.
function normalizeRun(r, i) {
  return {
    ...r,
    _i: i,
    // Replay frames drop "pass"/"pay" steps.
    frames: (r.log || []).filter((f) => {
      const d = f.desc || "";
      return !d.startsWith("pass") && !d.startsWith("pay ");
    }),
  };
}

// Clear the games viewer at the start of a run so live rows can stream in.
function resetViz() {
  state.vizRuns = [];
  state.vizGames = [];
  state.vizProps = state.props || []; // working props → tree status circles
  state.runsSort = { key: "#", dir: 1 };
  state.vizIdx = 0;
  state.vizLiveOpened = false;
  state.vizNav = null; // no board open — arrow keys do nothing
  $("viz-box").classList.add("hidden");
  $("viz-log").replaceChildren();
}

// Append (or replace) a single game's row as it finishes, live.
function appendLiveRun(raw) {
  const nr = normalizeRun(raw, raw.game_index ?? state.vizRuns.length);
  const at = state.vizRuns.findIndex((r) => r._i === nr._i);
  if (at >= 0) state.vizRuns[at] = nr; else state.vizRuns.push(nr);
  state.vizGames[nr._i] = nr.frames;
  $("viz-box").classList.remove("hidden");
  renderRunsTable();
  // Open the first replayable game once, so a line can be watched while the
  // rest keep running; don't yank the view around on later games.
  if (!state.vizLiveOpened) {
    const first = state.vizRuns.find((r) => r.frames.length);
    if (first) { state.vizLiveOpened = true; highlightGame(first._i); openBoard(first._i); }
  }
}

function renderViz(result, opts = {}) {
  // One row per game, keyed by the game's index (a resumed run's games can be
  // stored out of order — fall back to the position for old results).
  const runs = normalizeRuns(result).map((r, i) => normalizeRun(r, r.game_index ?? i));

  state.vizRuns = runs;
  state.vizProps = result.properties || []; // for the tree's status circles
  state.vizGames = [];
  runs.forEach((r) => (state.vizGames[r._i] = r.frames)); // openBoard indexes into this
  state.runsSort = { key: "#", dir: 1 };

  const box = $("viz-box");
  if (!runs.length) { box.classList.add("hidden"); state.vizNav = null; return; }
  box.classList.remove("hidden");
  renderRunsTable();
  // A board opened during the live run stays as-is — don't yank the view.
  if (opts.keepOpenBoard) return;
  state.vizNav = null; // reset until a board is (re)opened below
  // Open the first replayable (successful) game, if any.
  const first = runs.find((r) => r.frames.length);
  $("viz-log").replaceChildren();
  if (first) { highlightGame(first._i); openBoard(first._i); }
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
  Result: (r) => (r.success ? 0 : r.timed_out ? 1 : 2),
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

    const handIcon = el("span", { className: "hand-icon", textContent: "✋", title: "hover to see the opening hand" });
    hoverGrid(handIcon, run.hand || []);

    const treeCell = (run.tree || run.tree_gz || run.has_tree)
      ? (() => {
          const b = el("span", { className: "icon-btn", textContent: "🌳", title: "open the explored-states tree in a new tab" });
          b.onclick = (e) => { e.stopPropagation(); openTree(run, i); };
          return b;
        })()
      : el("span", { className: "muted", textContent: "—" });

    // Bugs: exceptions hit during this game's search. When present, a 🐛 icon
    // is shown in the Result cell (no dedicated column) and opens the detail.
    const nbugs = (run.bugs || []).length;
    const resultCell = el("td", { className: "cc status " + cls, title });
    resultCell.append(el("span", { textContent: mark + suffix }));
    if (nbugs) {
      const b = el("span", { className: "icon-btn bug-icon", textContent: "🐛",
        title: `${nbugs} bug${nbugs > 1 ? "s" : ""} hit during the search — click for details` });
      b.append(el("span", { className: "bug-count", textContent: String(nbugs) }));
      b.onclick = (e) => { e.stopPropagation(); openBugs(run, i); };
      resultCell.append(b);
    }

    const canReplay = run.frames.length > 0;
    const tr = el("tr", { className: "run-row" + (canReplay ? " replayable" : "") },
      el("td", { className: "numc", textContent: String(i + 1) }));
    tr.dataset.idx = i; // original game index (survives sorting)
    tr.append(
      resultCell,
      el("td", { className: "cc" }, handIcon),
      el("td", { className: "numc", title: "steps in the winning line", textContent: canReplay ? String(run.frames.length) : "—" }),
      el("td", { className: "numc", textContent: num(run.branches_explored) }),
      el("td", { className: "numc", textContent: num(run.branches_considered) }),
      el("td", { className: "cc" }, treeCell));
    if (canReplay) {
      tr.title = "click to replay the winning line below";
      tr.onclick = () => { highlightGame(i, true); openBoard(i); };
    }
    tbody.append(tr);
  });
  return el("table", { className: "runs viz-runs" }, thead, tbody);
}

// `scroll` only when the user explicitly navigates (row click, keyboard) — NOT
// on the automatic table re-render each game finishes, which would otherwise
// keep yanking the view back to the games table mid-run.
function highlightGame(gi, scroll = false) {
  state.vizIdx = gi;
  const tbody = $("viz-list").querySelector("tbody");
  if (!tbody) return;
  [...tbody.children].forEach((tr) => {
    const on = +tr.dataset.idx === gi;
    tr.classList.toggle("active", on);
    if (on && scroll) tr.scrollIntoView({ block: "nearest" });
  });
}

// ↑ / ↓ : open the previous / next SUCCESSFUL (replayable) game, in the order
// they are currently shown in the runs table (so the highlight moves up/down
// the visible list, respecting the active sort).
function stepGame(d) {
  const tbody = $("viz-list").querySelector("tbody");
  if (!tbody) return;
  const order = [...tbody.querySelectorAll("tr.replayable")].map((tr) => +tr.dataset.idx);
  if (!order.length) return;
  let pos = order.indexOf(state.vizIdx);
  if (pos === -1) pos = d > 0 ? -1 : order.length;  // step in from either end
  const next = order[Math.min(order.length - 1, Math.max(0, pos + d))];
  if (next != null && next !== state.vizIdx) { highlightGame(next, true); openBoard(next); }
}

// Floating grid of card images shown while hovering a hand icon.
let hoverGridEl = null;
function hoverGrid(node, names, backs = 0) {
  const show = () => {
    if (!hoverGridEl) { hoverGridEl = el("div", { id: "hover-grid" }); document.body.append(hoverGridEl); }
    const g = hoverGridEl;
    if ((!names || !names.length) && !backs) {
      g.replaceChildren(el("div", { className: "gfallback", textContent: "hand not recorded" }));
    } else {
      g.replaceChildren(
        ...(names || []).map((n) => {
          const img = state.imageMap[n];
          return img ? el("img", { src: img, alt: n, title: n })
                     : el("div", { className: "gfallback", textContent: n });
        }),
        // Card backs for the random-padding slots of a fixed hand.
        ...Array.from({ length: backs }, () =>
          el("div", { className: "gback", title: "random card (padding)" })),
      );
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

// Build a board frame (as fcFrame does) from an ARBITRARY fixed-config dict
// (e.g. a stored run's config) — fcFrame + its helpers read state.fixedConfig,
// so briefly swap it in, then restore. Synchronous, so it never races a render.
function fcFrameFor(config) {
  const saved = state.fixedConfig, base = newFixedConfig();
  state.fixedConfig = { ...base, ...config,
    mana_pool: { ...base.mana_pool, ...((config || {}).mana_pool || {}) } };
  try { return fcFrame(); } finally { state.fixedConfig = saved; }
}

// Hover `node` to preview the full starting BOARD of a fixed-config run (the
// same layout as game replay), floated near the cursor and scaled down.
let boardHoverEl = null;
function boardHover(node, config) {
  const show = () => {
    if (!boardHoverEl) { boardHoverEl = el("div", { id: "board-hover" }); document.body.append(boardHoverEl); }
    // Wrap in .board so it looks exactly like the replay/config board; show the
    // Library (not the empty Stack) since this is a fixed-config STARTING state.
    boardHoverEl.replaceChildren(el("div", { className: "board" },
      renderBoard(fcFrameFor(config), { showLibrary: true })));
    boardHoverEl.style.display = "block";
  };
  node.onmouseenter = show;
  node.onmousemove = (e) => {
    if (!boardHoverEl) return;
    const S = 0.62;  // #board-hover is transform: scale(0.62)
    const w = (boardHoverEl.offsetWidth || 760) * S, h = (boardHoverEl.offsetHeight || 460) * S;
    const x = Math.min(e.clientX + 18, window.innerWidth - w - 12);
    const y = Math.min(e.clientY + 18, window.innerHeight - h - 12);
    boardHoverEl.style.left = Math.max(8, x) + "px";
    boardHoverEl.style.top = Math.max(8, y) + "px";
  };
  node.onmouseleave = () => { if (boardHoverEl) boardHoverEl.style.display = "none"; };
}

// Inflate a gzip+base64 tree stored by the server.
async function inflateTree(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

// Open the explored-states search tree for a run in a new browser tab.
async function openTree(run, i) {
  if (!run.tree && !run.tree_gz && !run.has_tree) return;
  // window.open must happen synchronously in the click, before any await.
  const w = window.open("", "_blank");
  if (!w) { alert("Popup blocked — allow popups for this site to view the tree."); return; }
  let tree = run.tree;
  if (!tree) {
    // Live runs carry the tree inline; reloaded runs have it stripped from the
    // session payload (it can be enormous) — fetch just this game's tree.
    let gz = run.tree_gz;
    if (!gz) {
      w.document.write("Loading search tree…");
      try {
        const gi = run.game_index ?? run._i ?? i;
        const r = await api(`/api/sessions/${state.session.id}/results/${state.currentResultId}/runs/${gi}/tree`);
        gz = r.tree_gz;
        run.tree_truncated = r.tree_truncated; // for the viewer header
      } catch (e) { w.document.write("Failed to load the tree: " + e.message); return; }
    }
    try { tree = await inflateTree(gz); }
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

// Open a plain report of the bugs hit during a game's search in a new tab.
function openBugs(run, i) {
  const bugs = run.bugs || [];
  if (!bugs.length) return;
  const w = window.open("", "_blank");
  if (!w) { alert("Popup blocked — allow popups for this site to view the bugs."); return; }
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const items = bugs.map((b, n) => `
    <div class="bug">
      <div class="h">#${n + 1} — ${esc(b.context || "search")}
        ${b.turn != null ? `<span class="k">turn ${esc(b.turn)}, ${esc(b.phase)}</span>` : ""}</div>
      <div class="err">${esc(b.error)}</div>
      <div class="k">${esc(b.where)}</div>
      <pre>${esc(b.traceback)}</pre>
    </div>`).join("");
  w.document.open();
  w.document.write(`<!doctype html><html><head><meta charset="utf-8">
<title>Search bugs — game #${i + 1}</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; background:#0f1116; color:#e6e8ee;
    font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header { padding:.7rem 1rem; border-bottom:1px solid #2e3340; background:#1c1f27; position:sticky; top:0; }
  header b { color:#e05561; }
  .wrap { padding:1rem; display:flex; flex-direction:column; gap:1rem; }
  .bug { border:1px solid #2e3340; border-radius:8px; background:#171a21; padding:.7rem .9rem; }
  .bug .h { font-weight:600; color:#e0a561; margin-bottom:.3rem; }
  .bug .err { color:#e05561; font-family:ui-monospace,Menlo,monospace; margin-bottom:.3rem; }
  .bug .k { color:#9aa3b2; font-size:12px; }
  .bug pre { margin:.5rem 0 0; padding:.6rem; background:#0f1116; border-radius:6px;
    overflow:auto; font:12px/1.45 ui-monospace,Menlo,monospace; color:#c5ccd8; }
</style></head><body>
<header><b>🐛 ${bugs.length} bug${bugs.length > 1 ? "s" : ""}</b> hit while searching game #${i + 1}
  — these lines were skipped; the search continued.</header>
<div class="wrap">${items}</div>
</body></html>`);
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
  /* sticky step header: scrolls horizontally with the tree, pinned vertically.
     Uses the same elevated surface as the top bar (#1c1f27) so the header reads
     as ONE panel over the page colour — not a third, in-between shade. */
  #ruler { position:sticky; top:0; height:26px; z-index:2; background:#1c1f27; border-bottom:1px solid #2e3340; }
  #ruler span { position:absolute; top:5px; font-size:11px; letter-spacing:.5px; text-transform:uppercase; color:#9aa3b2; white-space:nowrap; }
  /* Paint the SVG its own opaque background (same as the wrap) so a large
     transparent canvas never shows compositing seams / "darker" patches. */
  svg { display:block; background:#0f1116; }
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
  /* Non-clickable states (no hidden subbranches / leaf lines) are dimmed grey
     so the clickable, expandable ones stand out. */
  .node:not(.exp):not(.win) text { fill:#6b7280; }
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
const X_GAP = 340 + (K - 1) * CGAP;
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
// The terminal "✓ all properties satisfied" marker node is display noise: the
// winning line already ends gold on the state that satisfied everything.
function pruneFinal(n) {
  n.children = (n.children || []).filter(c => !(c.label || "").startsWith("✓ all properties satisfied"));
  n.children.forEach(pruneFinal);
}
pruneFinal(DATA.tree);
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
// A property is also dead (red) at a node when EVERY explored child is dead
// for it — no continuation from here can verify it anymore. Computed bottom-up
// over the whole tree (iterative post-order: trees can be thousands deep).
function markDeadProps(rootNodes) {
  const stack = rootNodes.map(n => [n, 0]);
  while (stack.length) {
    const top = stack[stack.length - 1];
    const n = top[0], kids = n.children || [];
    if (top[1] < kids.length) { stack.push([kids[top[1]++], 0]); continue; }
    stack.pop();
    n._deadProps = {};
    for (const p of PROPS) {
      const [cls] = propStatus(n._dead || n, p);
      if (cls === "ko" ||
          (cls === "todo" && kids.length && kids.every(c => c._deadProps[p.id]))) {
        n._deadProps[p.id] = true;
      }
    }
  }
}
markDeadProps(roots);
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
      let [cls, why] = propStatus(src, p);
      // Bubbled-up death: every explored continuation below is a dead end for
      // this property, so it can't be verified from here either.
      if (cls === "todo" && n._deadProps && n._deadProps[p.id]) {
        cls = "ko";
        why = "can no longer be verified — every explored line below is a dead end for it";
      }
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
  if (lbl.length > 56) lbl = lbl.slice(0, 55) + "…";
  // ▸N = N hidden subbranches (click to show); ▾ = expanded (click to hide).
  const marker = kids.length ? (n._open ? " ▾" : " ▸" + kids.length) : "";
  t.textContent = (n.turn ? "T" + n.turn + " " : "") + lbl + marker;
  const title = document.createElementNS(NS, "title");
  const where = n.phase && n.phase !== "start"
    ? "turn " + n.turn + ", " + n.phase.replace(/_/g, " ") : "";
  // The per-node replay steps (abilities resolving, triggers, reveals, ...) —
  // everything the board replay shows for this node, listed on hover.
  const steps = (n.steps && n.steps.length)
    ? "\\n\\nWhat happens here:\\n" + n.steps.map(s => "  · " + s).join("\\n") : "";
  title.textContent = n.hand
    ? "Opening hand:\\n" + n.hand.map(c => "  · " + c).join("\\n")   // initial state
    : (n.label || "") + (where ? "\\n" + where : "") +
      (kids.length ? "\\n" + kids.length + " subbranch" + (kids.length > 1 ? "es" : "") : "") +
      (n._dead ? "\\n✗ line dies at turn " + n._dead.turn + ", " + (n._dead.phase || "").replace(/_/g, " ") : "") +
      steps;
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
  // A token uses its real Scryfall scan when we have one; otherwise a composed
  // face. Non-token cards use their card image.
  const img = state.imageMap[name];
  if (opts.token && !img) {
    // No scan: compose a card face with name, type line, textbox and P/T,
    // tinted by the token's colour(s).
    t.classList.add("token-card");
    const face = el("div", { className: "tok-face" },
      el("div", { className: "tok-name", textContent: name }),
      el("div", { className: "tok-type", textContent: opts.typeLine || "Token" }),
      el("div", { className: "tok-text", textContent: opts.text || "" }));
    const tint = tokenTint(opts.colors);
    if (tint) { t.style.boxShadow = `inset 0 0 0 3px ${tint}`; t.style.borderColor = tint; }
    if (opts.power != null && opts.toughness != null) {
      face.append(el("div", { className: "tok-pt", textContent: `${opts.power}/${opts.toughness}` }));
    }
    t.append(face);
  } else if (img) t.append(el("img", { src: img, alt: name, loading: "lazy" }));
  else t.append(el("div", { className: "fallback", textContent: name }));
  if (opts.commander) t.append(el("div", { className: "badge", textContent: "CMD" }));
  // Variable P/T (a characteristic-defining ability, e.g. Barrowgoyf's */*):
  // the printed card gives no number, so the current values are always shown.
  if (!opts.token && opts.power != null && opts.toughness != null) {
    t.append(el("div", {
      className: "badge pt",
      title: `current power/toughness: ${opts.power}/${opts.toughness}`,
      textContent: `${opts.power}/${opts.toughness}`,
    }));
  }
  // Markers: render every counter kind present on the permanent, not just a
  // hardcoded few. +1/+1 and -1/-1 get P/T formatting, loyalty a shield, and
  // any other kind (charge, oil, fade, page, lore, ...) shows "N×kind".
  const counters = opts.counters || {};
  const kinds = Object.entries(counters).filter(([, v]) => v);
  const granted = opts.granted || [];
  if (kinds.length || granted.length || opts.chosen) {
    const row = el("div", { className: "ctr-row" });
    for (const [k, v] of kinds) {
      let label, cls = "badge ctr";
      if (k === "+1/+1") { label = `+${v}/+${v}`; }
      else if (k === "-1/-1") { label = `−${v}/−${v}`; cls += " neg"; }
      else if (k === "loyalty") { label = `⟐${v}`; }
      else if (k === "powered_up") { label = "powered up"; }
      else if (k === "deadpool") { label = "deadpool"; }
      else { label = `${v}×${k}`; }
      const title = k === "powered_up" ? "powered up"
        : k === "deadpool" ? "text box exchanged with Deadpool, Trading Card"
        : `${v} ${k} counter${v === 1 ? "" : "s"}`;
      row.append(el("div", { className: cls, title, textContent: label }));
    }
    // "As it enters, choose ..." (e.g. Multiversal Passage's basic land type).
    if (opts.chosen) {
      row.append(el("div", {
        className: "badge ctr chosen",
        title: `enters as: ${opts.chosen}`,
        textContent: opts.chosen,
      }));
    }
    // Granted (until-end-of-turn) abilities, e.g. Cosmic Spider-Man's buff.
    for (const kw of granted) {
      row.append(el("div", {
        className: "badge kw",
        title: `has ${kw} (granted until end of turn)`,
        textContent: KW_SHORT[kw] || kw,
      }));
    }
    t.append(row);
  }
  hoverable(t, img); // enlarge on hover, like the decklist
  // Fixed-config editor: make the tile interactive (click to tap, right-click
  // for the counters/keywords/remove menu).
  if (opts.editable) {
    t.classList.add("editable");
    if (opts.onClick) t.onclick = (e) => { e.preventDefault(); hideHover(); opts.onClick(e); };
    if (opts.onMenu) t.oncontextmenu = (e) => { e.preventDefault(); e.stopPropagation(); hideHover(); opts.onMenu(e); };
    if (opts.dragData) {
      t.draggable = true;
      t.ondragstart = (e) => { e.dataTransfer.setData("text/plain", JSON.stringify(opts.dragData)); e.dataTransfer.effectAllowed = "move"; hideHover(); };
    }
  }
  return t;
}

// Compact labels for granted-keyword badges (tiles are 78px wide).
const KW_SHORT = {
  "flying": "fly", "first strike": "1st", "double strike": "2×st",
  "trample": "trmp", "lifelink": "life", "haste": "haste",
  "vigilance": "vigil", "deathtouch": "death", "reach": "reach",
  "menace": "menace", "hexproof": "hex", "indestructible": "indstr",
  "unblockable": "unblk",
};

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

function pile(items, edit = {}) {
  const wrap = el("div", { className: "pile" });
  const list = items || [];
  if (!list.length) {
    wrap.append(el("div", { className: "pile-empty", textContent: "—" }));
    return wrap;
  }
  list.forEach((raw, idx) => {
    const item = normalizePileItem(raw);
    const source = item.source_name || item.name;
    const img = state.imageMap[source] || state.imageMap[item.name];
    const card = el("div", { className: "pile-img", title: item.name });
    if (img) card.append(el("img", { src: img, alt: item.name, loading: "lazy" }));
    else card.append(el("div", { className: "fallback", textContent: item.name }));
    if (edit.onMenu) {
      card.classList.add("editable");
      card.oncontextmenu = (e) => { e.preventDefault(); e.stopPropagation(); hideHover(); edit.onMenu(idx, item.name, e); };
    }
    if (edit.dragZone) {
      card.dataset.idx = idx;
      card.draggable = true;
      card.ondragstart = (e) => {
        e.dataTransfer.setData("text/plain", JSON.stringify({ move: true, from: edit.dragZone, idx, name: item.name }));
        e.dataTransfer.effectAllowed = "move"; hideHover();
        // Live in-zone sort: fade the dragged card and spread the pile out so
        // the order is visible while dragging. BOTH must be deferred to a
        // timeout: spreading the pile (`.sorting`) reflows and MOVES the dragged
        // card, and Chrome aborts a native drag whose source element moves
        // during `dragstart` — which is why only the first card (that never
        // moves when the pile spreads) used to be draggable.
        if (edit.reorder) {
          state.fcSort = { zone: edit.dragZone, el: card };
          setTimeout(() => { wrap.classList.add("sorting"); card.classList.add("dragging"); }, 0);
        }
      };
      card.ondragend = () => {
        wrap.classList.remove("sorting");
        card.classList.remove("dragging");
        if (state.fcSort && state.fcSort.zone === edit.dragZone && card.parentNode) {
          fcCommitPileOrder(edit.dragZone, card.parentNode);
        }
        state.fcSort = null;
      };
    }
    wrap.append(hoverable(card, img, {
      title: item.kind === "spell" || item.kind === "card" ? item.name : source,
      trigger: item.kind === "triggered" ? item.trigger : (item.kind === "activated" ? "Activated ability" : null),
      ability: item.kind === "spell" || item.kind === "card" ? null : item.ability,
    }));
  });
  // Live vertical sortable: while a same-zone card is dragged, insert it before
  // the first card whose middle is below the cursor (else at the end), so the
  // real order shows in real time. Cross-zone drags fall through to the zone.
  // `dragover` fires many times per frame; we coalesce the DOM work to one
  // update per animation frame (via rAF) so reordering stays smooth.
  if (edit.dragZone && edit.reorder) {
    let raf = 0, cursorY = 0;
    const apply = () => {
      raf = 0;
      if (!state.fcSort || state.fcSort.zone !== edit.dragZone) return;
      const el = state.fcSort.el;
      let target = null;
      for (const c of wrap.querySelectorAll(".pile-img:not(.dragging)")) {
        const r = c.getBoundingClientRect();
        if (cursorY < r.top + r.height / 2) { target = c; break; }
      }
      if (target) { if (el.nextElementSibling !== target) wrap.insertBefore(el, target); }
      else if (wrap.lastElementChild !== el) wrap.appendChild(el);
    };
    wrap.ondragover = (e) => {
      if (!state.fcSort || state.fcSort.zone !== edit.dragZone) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      cursorY = e.clientY;
      if (!raf) raf = requestAnimationFrame(apply);
    };
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

// Energy counters rendered like a mana pool (one pip per {E}).
function energyPips(n) {
  const span = el("span", { className: "pool-pips" });
  for (let k = 0; k < Math.min(n, 12); k++) span.append(el("span", { className: "pip E", textContent: "E" }));
  if (n > 12) span.append(el("span", { className: "muted", textContent: ` ×${n}` }));
  if (!n) span.append(el("span", { className: "muted", textContent: "—" }));
  return span;
}

// A permanent tile with any auras/equipment attached to it stacked BEHIND it
// (peeking out from the top-right), so the enchanted/equipped card is on top.
function permTile(p, attachedByHost, edit = {}) {
  const host = tile(p.name, { tapped: p.tapped, sick: p.sick, commander: p.commander, attacking: p.attacking, counters: p.counters,
    granted: p.granted, chosen: p.chosen, token: p.token, typeLine: p.type_line, text: p.text, power: p.power, toughness: p.toughness, colors: p.colors,
    editable: edit.editable,
    onClick: edit.onClick ? () => edit.onClick(p) : null,
    onMenu: edit.onMenu ? (e) => edit.onMenu(p, e) : null,
    dragData: edit.drag ? edit.drag(p) : null });
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

function renderBoard(f, edit = {}) {
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
  const ed = edit.editable;
  // In the Fixed-config editor every zone is interactive.
  const permEdit = ed ? {
    editable: true, onClick: edit.onPermClick, onMenu: edit.onPermMenu,
    drag: (p) => ({ move: true, from: "battlefield", idx: p._idx, name: p.name }),
  } : {};
  const mkPerm = (p) => permTile(p, attachedByHost, permEdit);
  const zoneMenu = (zone) => (ed && edit.onZoneMenu
    ? (idx, name, e) => edit.onZoneMenu(zone, idx, name, e) : null);
  const handTile = (n, idx) => tile(n, ed ? {
    editable: true,
    onMenu: (e) => edit.onZoneMenu && edit.onZoneMenu("hand", idx, n, e),
    dragData: { move: true, from: "hand", idx, name: n },
  } : {});
  // Bottom row: lands and Lander tokens (they fetch lands, so they live with
  // them). Top row: everything else, including all other tokens.
  const isBottom = (p) => p.is_land || p.is_lander;
  const lands = bf.filter((p) => isBottom(p) && !isAttached(p)).map(mkPerm);
  const nonlands = bf.filter((p) => !isBottom(p) && !isAttached(p)).map(mkPerm);
  const c = f.counters || {};
  const flags = state.deckFlags || {};

  // A number field (up/down spinner) for a header value; plain text off-editor.
  const numField = (value, onSet, min) => {
    const inp = el("input", { type: "number", value: String(value), className: "fc-num" });
    if (min != null) inp.min = String(min);
    inp.onchange = () => onSet(inp.value);
    return inp;
  };
  const hstat = (label, value, onSet, min) => {
    const s = el("span", { className: "fc-hstat" }, el("span", { className: "k", textContent: label }));
    s.append(ed && onSet ? numField(value, onSet, min) : document.createTextNode(String(value)));
    return s;
  };

  const line1 = el("div", { className: "board-header step-line" });
  if (ed) {
    line1.append(hstat("turn ", f.turn, edit.onSetTurn, 1));
    const pdec = el("button", { className: "fc-step", textContent: "◀" }); pdec.onclick = () => edit.onPhase(-1);
    const pinc = el("button", { className: "fc-step", textContent: "▶" }); pinc.onclick = () => edit.onPhase(1);
    line1.append(el("span", { className: "fc-hstat" }, pdec,
      el("b", { className: "turn", textContent: f.phase }), pinc));
  } else {
    line1.append(el("span", { className: "turn", textContent: `Turn ${f.turn} · ${f.phase}` }),
      el("span", { className: "action", textContent: f.desc || "" }));
  }
  const ints = el("div", { className: "board-header" },
    hstat("life ", f.life, ed && ((v) => edit.onSet("life", v))),
    hstat("opp ", f.opponent_life ?? 20, ed && ((v) => edit.onSet("opponent_life", v))));
  // In the editor the library size moves into the Library zone label; replay
  // keeps it in the header.
  if (!ed) ints.append(el("span", {}, el("span", { className: "k", textContent: "library " }), String(f.library)));
  if (flags.storm) ints.append(hstat("storm ", c.storm || 0, ed && ((v) => edit.onSet("storm", v)), 0));

  const pools = el("div", { className: "board-header pools" });
  if (ed) {
    const wrap = el("span", { className: "fc-mana-edit" },
      el("span", { className: "k pool-label", textContent: "pool" }));
    ["W", "U", "B", "R", "G", "C"].forEach((sym) => {
      wrap.append(el("span", { className: "fc-mana-edit-cell" },
        el("img", { className: "ms", alt: sym, loading: "lazy", src: `https://svgs.scryfall.io/card-symbols/${sym}.svg` }),
        numField((f.mana_pool || {})[sym] || 0, (v) => edit.onSetMana(sym, v), 0)));
    });
    pools.append(wrap);
  } else {
    pools.append(el("span", {}, el("span", { className: "k", textContent: "pool " }), poolPips(f.mana_pool)));
  }
  // A third header row for other pool-like quantities (energy, ...), shown only
  // when the deck uses them.
  const extras = el("div", { className: "board-header pools" });
  if (flags.energy) {
    if (ed) extras.append(hstat("energy ", f.energy || 0, (v) => edit.onSet("energy", v), 0));
    else extras.append(el("span", {}, el("span", { className: "k", textContent: "energy " }), energyPips(f.energy || 0)));
  }
  const header = el("div", {}, line1, ints, pools);
  if (extras.childNodes.length) header.append(extras);

  // MTGO-like layout: exile + graveyard piles on the left, the field in the
  // middle, command zone + stack/library on the right, hand across the bottom.
  const dz = (node, zone) => { if (ed) node.dataset.drop = zone; return node; };

  const gyBox = dz(el("div", { className: "side-box" },
    el("div", { className: "zlabel", textContent: `Graveyard (${(f.graveyard || []).length})` }),
    pile(f.graveyard, { onMenu: zoneMenu("graveyard"), dragZone: ed ? "graveyard" : null, reorder: ed })), "graveyard");
  const exBox = dz(el("div", { className: "side-box" },
    el("div", { className: "zlabel", textContent: `Exile (${(f.exile || []).length})` }),
    pile(f.exile, { onMenu: zoneMenu("exile"), dragZone: ed ? "exile" : null, reorder: ed })), "exile");
  const fieldArea = dz(el("div", { className: "bzone area-field" },
    el("div", { className: "field-row" },
      el("div", { className: "zlabel", textContent: `Battlefield (${nonlands.length + lands.length})` }),
      el("div", { className: "tiles" }, ...nonlands)),
    el("div", { className: "field-row lands" },
      el("div", { className: "tiles" }, ...lands))), "battlefield");
  // Right-click empty battlefield space → add a token (tiles stopPropagation).
  if (ed && edit.onFieldMenu) {
    fieldArea.oncontextmenu = (e) => { e.preventDefault(); hideHover(); edit.onFieldMenu(e); };
  }
  const handArea = dz(el("div", { className: "bzone area-hand" },
    el("div", { className: "zlabel", textContent: `Hand (${(f.hand || []).length})` }),
    el("div", { className: "tiles hand" }, ...(f.hand || []).map(handTile))), "hand");

  // Command zone — commanders are draggable out and the box is a drop target
  // (drag a commander back to return it here). Commander-tax number input each.
  const cmdBox = dz(el("div", { className: "side-box" },
    el("div", { className: "zlabel", textContent: `Command zone (${(f.command_zone || []).length})` }),
    pile(f.command_zone, {
      dragZone: ed ? "command" : null,
      onMenu: ed && edit.onCommandMenu ? (idx, name, ev) => edit.onCommandMenu(idx, name, ev) : null,
    })), "command");
  if (ed && edit.commanderTax && edit.commanderTax.length) {
    const tax = el("div", { className: "fc-tax" });
    edit.commanderTax.forEach((t) => {
      const inp = el("input", { type: "number", min: "0", value: String(t.count), className: "fc-num" });
      inp.onchange = () => edit.onSetTax(t.name, inp.value);
      // Tax = {2} per prior cast, shown compactly as "+{2} × <casts>".
      tax.append(el("div", { className: "fc-tax-row", title: `${t.name} — commander tax` },
        el("span", { className: "fc-tax-name", textContent: "+" }),
        manaCostEl("{2}"), el("span", { className: "fc-tax-eq", textContent: "×" }), inp));
    });
    cmdBox.append(tax);
  }
  // Right column: command zone + (editor / config preview) library-top /
  // (replay) stack. The library COUNT is the TOTAL library — the revealed top
  // cards PLUS the (shuffled) rest.
  let rightSecond;
  if (ed || edit.showLibrary) {
    const libTotal = (f.library || 0) + (f.library_top || []).length;
    // Library-top is an overlapping pile (like graveyard/exile); front = top.
    // In the editor you can drag to reorder; a read-only preview just shows it.
    const box = el("div", { className: "side-box" },
      el("div", { className: "zlabel", textContent: `Library — front = top (${libTotal})` }),
      ed ? pile(f.library_top, { onMenu: zoneMenu("library"), dragZone: "library", reorder: true })
         : pile(f.library_top));
    rightSecond = ed ? dz(box, "library") : box;
  } else {
    rightSecond = el("div", { className: "side-box" },
      el("div", { className: "zlabel", textContent: `Stack (${(f.stack || []).length})` }),
      pile(f.stack));
  }

  const grid = el("div", { className: "board-grid" });
  grid.append(
    el("div", { className: "bzone area-left" }, gyBox, exBox),
    fieldArea,
    el("div", { className: "bzone area-right" }, cmdBox, rightSecond),
    handArea,
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
  const range = el("input", { type: "range", min: 0, max: frames.length - 1, value: 0, style: "flex:1" });

  const draw = () => {
    const f = frames[state.vizStep];
    counter.textContent = `step ${state.vizStep + 1} / ${frames.length}`;
    range.value = state.vizStep;
    board.replaceChildren(renderBoard(f)); // the action shows in the header
  };
  const step = (d) => { state.vizStep = Math.min(frames.length - 1, Math.max(0, state.vizStep + d)); draw(); };
  prev.onclick = () => step(-1);
  next.onclick = () => step(1);
  range.oninput = () => { state.vizStep = +range.value; draw(); };
  state.vizNav = step; // ← / → keyboard navigation targets the open board

  const board = el("div", { className: "board" });
  host.append(
    board,
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
