/**
 * Boardgame Hub Frontend Application
 * Enforces bidirectional URL-state parity, safe DOM node construction, interactive SVG rule flowcharts,
 * collection analytics graphs, WhatsApp sharing, and UAE events tracking.
 */
(function () {
  "use strict";

  const VALID_TABS = ["collection", "rules", "analytics", "events"];
  const state = {
    activeTab: "collection", allGames: [], games: [], sessions: [], events: [],
    analytics: null, selectedGameId: "", activeDiagram: null, selectedNodeId: "node_setup",
    isLoadingGames: false, isLoadingSessions: false, isLoadingEvents: false, isLoadingRules: false,
  };

  const byId = (id) => document.getElementById(id);

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      Object.entries(attrs).forEach(([k, v]) => {
        if (v === undefined || v === null || v === false) return;
        if (k === "className") node.className = String(v);
        else if (k === "textContent") node.textContent = String(v);
        else if (k === "disabled" && v) node.disabled = true;
        else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
        else node.setAttribute(k, String(v));
      });
    }
    if (Array.isArray(children)) {
      children.forEach((c) => {
        if (c !== null && c !== undefined) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      });
    }
    return node;
  }

  function svgEl(tag, attrs, children) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => v !== undefined && v !== null && node.setAttribute(k, String(v)));
    if (Array.isArray(children)) children.forEach((c) => c && node.appendChild(c));
    return node;
  }

  function isSafeHttpUrl(candidate) {
    try {
      const parsed = new URL(String(candidate || ""), window.location.origin);
      return parsed.protocol === "https:" || parsed.protocol === "http:";
    } catch (_err) {
      return false;
    }
  }

  function showToast(message) {
    const banner = byId("toast-banner");
    if (!banner) return;
    banner.textContent = message;
    banner.classList.remove("hidden");
    window.clearTimeout(banner._timer);
    banner._timer = window.setTimeout(() => banner.classList.add("hidden"), 3500);
  }

  async function apiFetch(path, options) {
    const resp = await fetch(path, { headers: { "Content-Type": "application/json" }, ...(options || {}) });
    const data = await resp.json();
    if (!resp.ok) throw new Error((data && data.error && data.error.message) || "Request failed");
    return data;
  }

  const FILTER_URL_MAP = [
    ["status", "filter-status"], ["players", "filter-players"], ["max_playtime", "filter-playtime"],
    ["max_complexity", "filter-complexity"], ["search", "filter-search"],
    ["emirate", "filter-emirate"], ["event_search", "filter-event-search"],
  ];

  function syncUrlFromState() {
    const params = new URLSearchParams(window.location.search);
    params.set("tab", state.activeTab);
    if (state.selectedGameId && state.activeTab === "rules") params.set("game", state.selectedGameId);
    else params.delete("game");
    FILTER_URL_MAP.forEach(([paramKey, elId]) => {
      const inputEl = byId(elId);
      const val = inputEl ? String(inputEl.value || "").trim() : "";
      if (val) params.set(paramKey, val);
      else params.delete(paramKey);
    });
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
  }

  function readInitialUrlState() {
    const params = new URLSearchParams(window.location.search);
    const rawTab = params.get("tab") || "collection";
    state.activeTab = VALID_TABS.includes(rawTab) ? rawTab : "collection";
    const gameParam = params.get("game");
    if (gameParam) state.selectedGameId = gameParam;
    FILTER_URL_MAP.forEach(([paramKey, elId]) => {
      const val = params.get(paramKey);
      const inputEl = byId(elId);
      if (inputEl && val !== null) inputEl.value = val;
    });
    syncUrlFromState();
  }

  function switchTab(tabName) {
    state.activeTab = VALID_TABS.includes(tabName) ? tabName : "collection";
    document.querySelectorAll(".nav-tab").forEach((btn) => btn.classList.toggle("active", btn.getAttribute("data-tab") === state.activeTab));
    VALID_TABS.forEach((t) => {
      const sec = byId(`view-${t}`);
      if (sec) sec.classList.toggle("hidden", t !== state.activeTab);
    });
    syncUrlFromState();
    if (state.activeTab === "rules") {
      if (state.selectedGameId) loadRulesDiagram(state.selectedGameId);
      else renderEmptyRulesState();
    } else if (state.activeTab === "analytics") loadAnalytics();
    else if (state.activeTab === "events") loadEvents();
  }

  function buildGameFilterQuery() {
    const q = new URLSearchParams();
    FILTER_URL_MAP.slice(0, 5).forEach(([key, id]) => {
      const val = byId(id) ? byId(id).value.trim() : "";
      if (val) q.set(key, val);
    });
    return q.toString();
  }

  async function loadGamesAndSessions() {
    const query = buildGameFilterQuery();
    syncUrlFromState();
    state.isLoadingGames = true;
    state.isLoadingSessions = true;
    renderGamesGrid();
    renderSessionsList();
    try {
      const reqs = [apiFetch(`/api/v1/games${query ? "?" + query : ""}`), apiFetch("/api/v1/sessions")];
      if (query) reqs.push(apiFetch("/api/v1/games"));
      const [gamesData, sessionsData, allGamesData] = await Promise.all(reqs);
      state.games = gamesData.items || [];
      state.allGames = query ? (allGamesData && allGamesData.items) || state.games : state.games;
      state.sessions = sessionsData.items || [];
      if (!state.selectedGameId && state.allGames.length > 0) state.selectedGameId = state.allGames[0].id;
    } finally {
      state.isLoadingGames = false;
      state.isLoadingSessions = false;
    }
    renderGamesGrid();
    renderSessionsList();
    populateGameSelectors();
  }

  function populateGameSelectors() {
    const catalog = state.allGames.length > 0 ? state.allGames : state.games;
    [byId("session-game-input"), byId("rules-game-select")].forEach((sel) => {
      if (!sel) return;
      const currentVal = sel.value || state.selectedGameId;
      sel.replaceChildren(...catalog.map((g) => el("option", { value: g.id, textContent: `${g.title} (${g.min_players}-${g.max_players}P)` })));
      if (currentVal && catalog.some((g) => g.id === currentVal)) sel.value = currentVal;
    });
  }

  function renderGamesGrid() {
    const grid = byId("games-grid");
    const countSpan = byId("catalog-count");
    if (countSpan) countSpan.textContent = String(state.games.length);
    if (!grid) return;
    if (state.isLoadingGames && state.games.length === 0) {
      return grid.replaceChildren(el("div", { className: "empty-state-card", textContent: "Loading board game collection..." }));
    }
    if (state.games.length === 0) {
      const emptyMsg = state.allGames.length === 0
        ? "Your board game collection is empty. Click '+ Add Game' above to catalog your first game."
        : "No board games match the active filters. Adjust filters or click '+ Add Game' to add a new title.";
      return grid.replaceChildren(el("div", { className: "empty-state-card", textContent: emptyMsg }));
    }
    grid.replaceChildren(
      ...state.games.map((g) => {
        const pTxt = g.min_players === g.max_players ? `${g.min_players}P` : `${g.min_players}–${g.max_players}P`;
        const tTxt = g.min_playtime_mins === g.max_playtime_mins ? `${g.max_playtime_mins}m` : `${g.min_playtime_mins}–${g.max_playtime_mins}m`;
        return el("article", { className: "game-card", "data-testid": "game-card", "data-game-id": g.id }, [
          el("div", { className: "game-card-top" }, [
            el("div", null, [el("h3", { className: "game-card-title", textContent: g.title }), el("p", { className: "game-card-subtitle", textContent: g.subtitle })]),
            el("span", { className: `status-badge status-${g.status}`, textContent: g.status }),
          ]),
          el("div", { className: "game-stats-row" }, [`Players: ${pTxt}`, `Time: ${tTxt}`, `Weight: ${g.complexity_weight}/5`, `Plays: ${g.play_count}`, `Rating: ★ ${g.rating}`].map((txt) => el("span", { className: "stat-pill", textContent: txt }))),
          el("div", { className: "tag-list" }, (g.mechanics || []).slice(0, 4).map((m) => el("span", { className: "mechanic-tag", textContent: m }))),
          el("div", { className: "card-actions" }, [
            el("button", {
              type: "button", className: "btn btn-secondary", "data-testid": "btn-open-rules", textContent: "Rule Diagram",
              onClick: () => {
                state.selectedGameId = g.id;
                if (byId("rules-game-select")) byId("rules-game-select").value = g.id;
                switchTab("rules");
              },
            }),
            el("button", {
              type: "button", className: "btn btn-whatsapp", "data-testid": "btn-share-game-whatsapp", textContent: "WhatsApp Rules",
              onClick: () => openWhatsAppShare(`/api/v1/share/whatsapp/game/${encodeURIComponent(g.id)}`),
            }),
          ]),
        ]);
      })
    );
  }

  function renderSessionsList() {
    const list = byId("sessions-list");
    const countEl = byId("sessions-count");
    if (countEl) countEl.textContent = String(state.sessions.length);
    if (!list) return;
    if (state.isLoadingSessions && state.sessions.length === 0) {
      return list.replaceChildren(el("div", { className: "empty-state-card", textContent: "Loading play sessions..." }));
    }
    if (state.sessions.length === 0) {
      return list.replaceChildren(el("div", { className: "empty-state-card", textContent: "No play sessions logged yet. Click '+ Log Play Session' to record your first game night." }));
    }
    list.replaceChildren(
      ...state.sessions.slice(0, 8).map((s) => {
        const scoreEntries = s.scores && typeof s.scores === "object" ? Object.entries(s.scores) : [];
        const scoresLine = scoreEntries.length > 0 ? `Scores: ${scoreEntries.map(([n, pts]) => `${n}: ${pts}`).join(", ")}` : null;
        return el("div", { className: "session-card", "data-testid": "session-item" }, [
          el("div", { className: "session-header" }, [el("span", { textContent: s.game_title }), el("span", { className: "status-badge status-owned", textContent: `Winner: ${s.winner}` })]),
          el("div", { className: "session-meta tabular-nums", textContent: `${s.played_on} • ${s.duration_mins}m • ${s.location}` }),
          el("div", { className: "session-meta", textContent: `Players: ${(s.players || []).join(", ")}` }),
          scoresLine ? el("div", { className: "session-meta tabular-nums", textContent: scoresLine }) : null,
          s.notes ? el("p", { className: "session-notes", textContent: s.notes }) : null,
        ]);
      })
    );
  }

  function renderEmptyRulesState() {
    const container = byId("rules-svg-container");
    const inspector = byId("rules-node-inspector");
    if (container) container.replaceChildren(el("div", { className: "empty-state-card", textContent: "No game selected. Click '+ Add Game' in Collection & Plays to generate visual rule diagrams." }));
    if (inspector) inspector.textContent = "Add or select a board game to inspect setup and turn-order rules.";
  }

  async function loadRulesDiagram(gameId) {
    if (!gameId) return renderEmptyRulesState();
    state.selectedGameId = gameId;
    syncUrlFromState();
    state.isLoadingRules = true;
    try {
      const diag = await apiFetch(`/api/v1/games/${encodeURIComponent(gameId)}/rules-diagram`);
      state.activeDiagram = diag;
      state.selectedNodeId = (diag.diagram_nodes && diag.diagram_nodes[0] && diag.diagram_nodes[0].id) || "node_setup";
      renderRulesView(diag);
    } finally {
      state.isLoadingRules = false;
    }
  }

  function renderRulesView(diag) {
    byId("rules-diagram-title").textContent = `${diag.title} — Visual Rule Flowchart & Setup Guide`;
    byId("rules-diagram-subtitle").textContent = diag.subtitle;
    byId("rules-meta-badges").replaceChildren(...[diag.player_range_label, diag.playtime_label, `Complexity: ${diag.complexity_weight}/5 (${diag.complexity_tier})`].map((t) => el("span", { className: "stat-pill", textContent: t })));
    renderSvgFlowchart(diag);
    renderNodeInspector(diag);
    byId("rules-setup-list").replaceChildren(...(diag.setup_steps || []).map((s) => el("li", { textContent: s })));
    byId("rules-phases-list").replaceChildren(...(diag.turn_phases || []).map((tp, idx) => el("div", { className: "phase-item" }, [el("div", { className: "phase-item-title", textContent: `Phase ${idx + 1}: ${tp.phase}` }), el("div", { className: "phase-item-desc", textContent: tp.summary })])));
    byId("rules-scoring-list").replaceChildren(...(diag.scoring_rules || []).map((r) => el("li", { textContent: r })));
    byId("rules-tips-list").replaceChildren(...(diag.quick_tips || []).map((t) => el("li", { textContent: t })));
    byId("rules-mermaid-code").textContent = diag.mermaid_code || "";
  }

  function renderSvgFlowchart(diag) {
    const container = byId("rules-svg-container");
    if (!container) return;
    const nodes = diag.diagram_nodes || [];
    const boxW = 248, boxH = 74, gapX = 44, padX = 20, padY = 24, totalH = 126;
    const totalW = Math.max(820, padX * 2 + nodes.length * boxW + Math.max(0, nodes.length - 1) * gapX);
    const defs = svgEl("defs", null, [svgEl("marker", { id: "arrowhead", markerWidth: "10", markerHeight: "7", refX: "9", refY: "3.5", orient: "auto" }, [svgEl("polygon", { points: "0 0, 10 3.5, 0 7", fill: "var(--color-accent)" })])]);
    const children = [defs];
    nodes.forEach((n, idx) => {
      const x = padX + idx * (boxW + gapX), y = padY;
      if (idx < nodes.length - 1) children.push(svgEl("line", { x1: x + boxW, y1: y + boxH / 2, x2: x + boxW + gapX - 4, y2: y + boxH / 2, stroke: "var(--color-accent)", "stroke-width": "2.5", "marker-end": "url(#arrowhead)" }));
      const isSelected = n.id === state.selectedNodeId;
      const strokeColor = isSelected ? "var(--node-stroke-selected)" : n.kind === "setup" ? "var(--node-stroke-setup)" : n.kind === "scoring" ? "var(--node-stroke-scoring)" : "var(--node-stroke-phase)";
      const labelShort = n.label.length > 34 ? n.label.slice(0, 32) + "…" : n.label;
      const selectNode = () => {
        state.selectedNodeId = n.id;
        renderSvgFlowchart(diag);
        renderNodeInspector(diag);
      };
      const group = svgEl(
        "g",
        { class: "svg-node-group", style: "cursor: pointer;", tabindex: "0", role: "button", "aria-label": `${n.subtitle}: ${n.label}`, "aria-pressed": String(isSelected), "data-testid": `diagram-node-${n.id}` },
        [
          svgEl("rect", { x: x, y: y, width: boxW, height: boxH, rx: "10", fill: isSelected ? "var(--node-fill-selected)" : "var(--node-fill-default)", stroke: strokeColor, "stroke-width": isSelected ? "2.5" : "1.5" }),
          svgEl("text", { x: x + 14, y: y + 26, fill: "var(--node-text-muted)", "font-size": "11", "font-weight": "600" }, [document.createTextNode(n.subtitle.toUpperCase())]),
          svgEl("text", { x: x + 14, y: y + 50, fill: "var(--node-text-primary)", "font-size": "13", "font-weight": "600" }, [document.createTextNode(labelShort)]),
        ]
      );
      group.addEventListener("click", selectNode);
      group.addEventListener("keydown", (evt) => {
        if (evt.key === "Enter" || evt.key === " ") {
          evt.preventDefault();
          selectNode();
        }
      });
      children.push(group);
    });
    container.replaceChildren(svgEl("svg", { viewBox: `0 0 ${totalW} ${totalH}`, width: "100%", height: String(totalH), role: "img" }, children));
  }

  function renderNodeInspector(diag) {
    const inspector = byId("rules-node-inspector");
    const nodes = diag.diagram_nodes || [];
    const active = nodes.find((n) => n.id === state.selectedNodeId) || nodes[0];
    if (inspector && active) inspector.replaceChildren(el("strong", { textContent: `${active.label}: ` }), el("span", { textContent: active.detail }));
  }

  async function loadAnalytics() {
    const data = await apiFetch("/api/v1/analytics");
    state.analytics = data;
    const kpis = [
      { label: "Total Games in Collection", value: data.total_games },
      { label: "Owned / Wishlist", value: `${data.owned_games} / ${data.wishlist_games}` },
      { label: "Total Play Count", value: data.total_plays },
      { label: "Avg Complexity Weight", value: `${data.average_complexity} / 5.0` },
      { label: "Average Rating", value: `★ ${data.average_rating}` },
    ];
    byId("analytics-kpis").replaceChildren(...kpis.map((k) => el("div", { className: "kpi-card" }, [el("div", { className: "kpi-label", textContent: k.label }), el("div", { className: "kpi-value tabular-nums", textContent: String(k.value) })])));
    const renderBars = (id, items, key, fmt) => {
      byId(id).replaceChildren(
        ...(items || []).map((item) =>
          el("div", { className: "bar-row" }, [
            el("div", { className: "bar-label-line" }, [el("span", { textContent: String(item[key]) }), el("span", { className: "tabular-nums", textContent: fmt(item) })]),
            el("div", { className: "bar-track" }, [el("div", { className: "bar-fill", style: `width: ${Math.min(100, Math.max(6, Number(item.percentage || 0)))}%` })]),
          ])
        )
      );
    };
    renderBars("chart-complexity-bars", data.complexity_distribution, "bucket", (i) => `${i.count} games (${i.percentage}%)`);
    renderBars("chart-players-bars", data.player_count_coverage, "players", (i) => `${i.count} games (${i.percentage}%)`);
    renderBars("chart-mechanics-bars", data.mechanics_breakdown, "mechanic", (i) => `${i.count} games (${i.percentage}%)`);
    const maxP = Math.max(1, ...((data.top_played_games || []).map((g) => g.play_count)));
    renderBars("chart-top-played-bars", (data.top_played_games || []).map((g) => ({ ...g, percentage: Math.round((g.play_count * 100) / maxP) })), "title", (g) => `${g.play_count} plays • ★ ${g.rating}`);
  }

  async function loadEvents() {
    const emirate = byId("filter-emirate") ? byId("filter-emirate").value : "";
    const search = byId("filter-event-search") ? byId("filter-event-search").value.trim() : "";
    syncUrlFromState();
    const q = new URLSearchParams();
    if (emirate) q.set("emirate", emirate);
    if (search) q.set("search", search);
    const grid = byId("events-grid");
    state.isLoadingEvents = true;
    if (grid && state.events.length === 0) grid.replaceChildren(el("div", { className: "empty-state-card", textContent: "Loading UAE boardgame events..." }));
    try {
      const data = await apiFetch(`/api/v1/events${q.toString() ? "?" + q.toString() : ""}`);
      state.events = data.items || [];
    } finally {
      state.isLoadingEvents = false;
    }
    if (!grid) return;
    if (state.events.length === 0) {
      return grid.replaceChildren(el("div", { className: "empty-state-card", textContent: "No UAE boardgame events match the current filter. Click '+ Host UAE Boardgame Event' above to publish a meetup." }));
    }
    grid.replaceChildren(
      ...state.events.map((ev) => {
        const isFull = ev.rsvp_count >= ev.max_players;
        return el("article", { className: "event-card", "data-testid": "event-card", "data-event-id": ev.id }, [
          el("div", { className: "game-card-top" }, [
            el("div", null, [el("h3", { className: "game-card-title", textContent: ev.title }), el("p", { className: "game-card-subtitle", textContent: ev.venue })]),
            el("span", { className: "emirate-badge", textContent: ev.emirate }),
          ]),
          el("div", { className: "game-stats-row tabular-nums" }, [
            el("span", { className: "stat-pill", textContent: `${ev.event_date} @ ${ev.start_time} GST` }),
            el("span", { className: "stat-pill", textContent: ev.category }),
            el("span", { className: "stat-pill", "data-testid": "event-rsvp-pill", textContent: `RSVPs: ${ev.rsvp_count}/${ev.max_players}` }),
          ]),
          el("p", { className: "session-notes", textContent: ev.description }),
          el("div", { className: "tag-list" }, (ev.featured_games || []).map((fg) => el("span", { className: "mechanic-tag", textContent: fg }))),
          el("div", { className: "card-actions" }, [
            el("button", {
              type: "button", className: "btn btn-primary", "data-testid": "btn-event-rsvp", disabled: isFull, textContent: isFull ? "Full Capacity" : "RSVP (+1 Seat)",
              onClick: async () => {
                try {
                  await apiFetch(`/api/v1/events/${encodeURIComponent(ev.id)}/rsvp`, { method: "POST" });
                  showToast(`RSVP confirmed for ${ev.title}!`);
                  await loadEvents();
                } catch (err) {
                  showToast(err.message);
                }
              },
            }),
            el("button", {
              type: "button", className: "btn btn-whatsapp", "data-testid": "btn-share-event-whatsapp", textContent: "Share on WhatsApp",
              onClick: () => openWhatsAppShare(`/api/v1/share/whatsapp/event/${encodeURIComponent(ev.id)}`),
            }),
          ]),
        ]);
      })
    );
  }

  async function openWhatsAppShare(endpoint) {
    const data = await apiFetch(endpoint);
    byId("whatsapp-preview-text").textContent = data.text || "";
    const candidateUrl = data.whatsapp_url || "https://wa.me/";
    byId("link-open-whatsapp").setAttribute("href", isSafeHttpUrl(candidateUrl) ? candidateUrl : "https://wa.me/");
    byId("whatsapp-share-drawer").classList.remove("hidden");
  }

  function parseScoresInput(rawText) {
    const scores = {};
    (rawText || "").split(",").forEach((entry) => {
      const [rawName, rawPts] = entry.split(":");
      if (rawName && rawPts !== undefined) {
        const name = rawName.trim();
        const scoreVal = parseInt(rawPts.trim(), 10);
        if (name && !Number.isNaN(scoreVal)) scores[name] = scoreVal;
      }
    });
    return scores;
  }

  function bindRequiredField(inputEl, errEl) {
    inputEl.addEventListener("input", () => {
      if (inputEl.value.trim()) {
        inputEl.removeAttribute("aria-invalid");
        errEl.classList.add("hidden");
      }
    });
  }

  function requireNonEmpty(inputEl, errEl) {
    if (inputEl.value.trim()) {
      inputEl.removeAttribute("aria-invalid");
      errEl.classList.add("hidden");
      return true;
    }
    inputEl.setAttribute("aria-invalid", "true");
    errEl.classList.remove("hidden");
    inputEl.focus();
    return false;
  }

  function bindEvents() {
    document.querySelectorAll(".nav-tab").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab"))));
    window.addEventListener("popstate", () => {
      readInitialUrlState();
      loadGamesAndSessions();
      switchTab(state.activeTab);
    });
    ["filter-status", "filter-players", "filter-playtime", "filter-complexity"].forEach((id) => {
      if (byId(id)) byId(id).addEventListener("change", () => loadGamesAndSessions());
    });
    byId("filter-search").addEventListener("input", () => loadGamesAndSessions());
    byId("btn-share-list-whatsapp").addEventListener("click", () => {
      const q = buildGameFilterQuery();
      openWhatsAppShare(`/api/v1/share/whatsapp/list${q ? "?" + q : ""}`);
    });
    byId("btn-rules-whatsapp").addEventListener("click", () => {
      if (state.selectedGameId) openWhatsAppShare(`/api/v1/share/whatsapp/game/${encodeURIComponent(state.selectedGameId)}`);
    });
    byId("rules-game-select").addEventListener("change", (e) => loadRulesDiagram(e.target.value));

    const formAddGame = byId("form-add-game");
    const gameTitleInput = byId("game-title-input");
    const gameTitleErr = byId("game-title-error");
    byId("btn-toggle-add-game").addEventListener("click", () => formAddGame.classList.toggle("hidden"));
    byId("btn-cancel-add-game").addEventListener("click", () => formAddGame.classList.add("hidden"));
    bindRequiredField(gameTitleInput, gameTitleErr);
    formAddGame.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!requireNonEmpty(gameTitleInput, gameTitleErr)) return;
      const rawMechanics = byId("game-mechanics-input").value.trim();
      const rawSetup = byId("game-setup-input").value.trim();
      const setupSteps = rawSetup ? rawSetup.split(/[;\n]+/).map((s) => s.trim()).filter(Boolean) : [];
      const maxPlaytime = Math.max(5, Number(byId("game-playtime-input").value) || 60);
      const reqBody = {
        title: gameTitleInput.value.trim(), subtitle: byId("game-subtitle-input").value.trim() || "Custom boardgame entry",
        status: byId("game-status-input").value, min_players: Number(byId("game-min-players-input").value) || 2,
        max_players: Number(byId("game-max-players-input").value) || 4, min_playtime_mins: Math.min(30, maxPlaytime),
        max_playtime_mins: maxPlaytime, complexity_weight: Number(byId("game-complexity-input").value) || 2.2,
        mechanics: rawMechanics ? rawMechanics.split(",").map((m) => m.trim()).filter(Boolean) : ["Strategy"],
      };
      if (setupSteps.length > 0) reqBody.setup_steps = setupSteps;
      const created = await apiFetch("/api/v1/games", { method: "POST", body: JSON.stringify(reqBody) });
      formAddGame.reset();
      formAddGame.classList.add("hidden");
      state.selectedGameId = created.id;
      showToast(`Added "${created.title}" to your collection!`);
      await loadGamesAndSessions();
    });

    const formLogSession = byId("form-log-session");
    const sessionPlayersInput = byId("session-players-input");
    const sessionPlayersErr = byId("session-players-error");
    byId("btn-toggle-log-session").addEventListener("click", () => formLogSession.classList.toggle("hidden"));
    byId("btn-cancel-log-session").addEventListener("click", () => formLogSession.classList.add("hidden"));
    bindRequiredField(sessionPlayersInput, sessionPlayersErr);
    formLogSession.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!requireNonEmpty(sessionPlayersInput, sessionPlayersErr)) return;
      const players = sessionPlayersInput.value.split(",").map((p) => p.trim()).filter(Boolean);
      const scoresInput = byId("session-scores-input");
      await apiFetch("/api/v1/sessions", {
        method: "POST",
        body: JSON.stringify({
          game_id: byId("session-game-input").value, players: players,
          winner: byId("session-winner-input").value.trim() || players[0],
          scores: parseScoresInput(scoresInput ? scoresInput.value : ""),
          duration_mins: Number(byId("session-duration-input").value) || 60,
          location: byId("session-location-input").value.trim() || "Dubai",
          notes: byId("session-notes-input").value.trim(),
        }),
      });
      formLogSession.reset();
      formLogSession.classList.add("hidden");
      showToast("Play session recorded!");
      await loadGamesAndSessions();
    });

    byId("filter-emirate").addEventListener("change", () => loadEvents());
    byId("filter-event-search").addEventListener("input", () => loadEvents());
    const formAddEvent = byId("form-add-event");
    const eventTitleInput = byId("event-title-input");
    const eventVenueInput = byId("event-venue-input");
    const eventTitleErr = byId("event-title-error");
    byId("btn-toggle-add-event").addEventListener("click", () => formAddEvent.classList.toggle("hidden"));
    byId("btn-cancel-add-event").addEventListener("click", () => formAddEvent.classList.add("hidden"));
    const revalidateEventInputs = () => {
      if (eventTitleInput.value.trim()) eventTitleInput.removeAttribute("aria-invalid");
      if (eventVenueInput.value.trim()) eventVenueInput.removeAttribute("aria-invalid");
      if (eventTitleInput.value.trim() && eventVenueInput.value.trim()) eventTitleErr.classList.add("hidden");
    };
    eventTitleInput.addEventListener("input", revalidateEventInputs);
    eventVenueInput.addEventListener("input", revalidateEventInputs);
    formAddEvent.addEventListener("submit", async (e) => {
      e.preventDefault();
      const missingTitle = !eventTitleInput.value.trim();
      const missingVenue = !eventVenueInput.value.trim();
      if (missingTitle || missingVenue) {
        if (missingTitle) eventTitleInput.setAttribute("aria-invalid", "true");
        if (missingVenue) eventVenueInput.setAttribute("aria-invalid", "true");
        eventTitleErr.classList.remove("hidden");
        (missingTitle ? eventTitleInput : eventVenueInput).focus();
        return;
      }
      eventTitleInput.removeAttribute("aria-invalid");
      eventVenueInput.removeAttribute("aria-invalid");
      eventTitleErr.classList.add("hidden");
      await apiFetch("/api/v1/events", {
        method: "POST",
        body: JSON.stringify({
          title: eventTitleInput.value.trim(), emirate: byId("event-emirate-input").value,
          venue: eventVenueInput.value.trim(), event_date: byId("event-date-input").value || "2026-12-05",
          start_time: byId("event-time-input").value.trim() || "18:30",
          max_players: Number(byId("event-max-players-input").value) || 16,
          featured_games: byId("event-games-input").value.split(",").map((g) => g.trim()).filter(Boolean),
          description: byId("event-desc-input").value.trim(),
        }),
      });
      formAddEvent.reset();
      formAddEvent.classList.add("hidden");
      showToast("Published new UAE boardgame event!");
      await loadEvents();
    });

    byId("btn-close-whatsapp-drawer").addEventListener("click", () => byId("whatsapp-share-drawer").classList.add("hidden"));
    byId("btn-copy-whatsapp").addEventListener("click", async () => {
      const previewText = (byId("whatsapp-preview-text") && byId("whatsapp-preview-text").textContent) || "";
      try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") await navigator.clipboard.writeText(previewText);
      } catch (_err) { /* ignore clipboard permission restriction in headless context */ }
      showToast("WhatsApp message copied to clipboard!");
    });

    document.addEventListener("keydown", (evt) => {
      if (evt.key !== "Escape") return;
      const waDrawer = byId("whatsapp-share-drawer");
      if (waDrawer && !waDrawer.classList.contains("hidden")) return waDrawer.classList.add("hidden");
      [[formAddGame, "btn-toggle-add-game"], [formLogSession, "btn-toggle-log-session"], [formAddEvent, "btn-toggle-add-event"]].some(([formEl, btnId]) => {
        if (!formEl.classList.contains("hidden")) {
          formEl.classList.add("hidden");
          byId(btnId).focus();
          return true;
        }
        return false;
      });
    });
  }

  async function init() {
    readInitialUrlState();
    bindEvents();
    await loadGamesAndSessions();
    switchTab(state.activeTab);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
