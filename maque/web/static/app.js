const appEl = document.getElementById("screen");
const statusEl = document.getElementById("status");

const seatCN = { E: "东风", S: "南风", W: "西风", N: "北风" };
const actionCN = {
  DISCARD: "出牌",
  PENG: "碰",
  GANG_MING: "明杠",
  GANG_AN: "暗杠",
  GANG_JIA: "加杠",
  HU: "胡",
  PASS: "过",
};
const tileCN = {
  EW: "东风",
  SW: "南风",
  WW: "西风",
  NW: "北风",
  RD: "红中",
  GD: "发财",
  WB: "白板",
};
const nums = { "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九" };

const state = {
  sessionId: null,
  ws: null,
  connected: false,
  playerSeat: "E",
  phase: "starting",
  context: null,
  pendingOptions: [],
  leaderboardTotal: { E: 0, S: 0, W: 0, N: 0 },
  roundDelta: { E: 0, S: 0, W: 0, N: 0 },
  huWait: null,
  maResult: null,
  message: "初始化中...",
  assetStatus: null,
};

function tileText(tile) {
  if (!tile) return "(无)";
  if (tileCN[tile]) return tileCN[tile];
  if (tile.length === 2 && nums[tile[0]]) {
    return `${nums[tile[0]]}${tile[1] === "T" ? "索" : tile[1] === "B" ? "筒" : ""}`;
  }
  return tile;
}

function setStatus(msg, isError = false) {
  state.message = msg;
  statusEl.innerHTML = `<span class="${isError ? "error" : ""}">${msg}</span>`;
}

function send(data) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  state.ws.send(JSON.stringify(data));
}

function tileElement(tile, clickable = false, onClick = null) {
  const el = document.createElement("div");
  el.className = `tile${clickable ? " clickable" : ""}`;
  const img = document.createElement("img");
  img.src = `/assets/tiles/${tile}.png`;
  img.alt = tileText(tile);
  const fb = document.createElement("span");
  fb.className = "fallback";
  fb.textContent = tileText(tile);
  fb.style.display = "none";
  img.onerror = () => {
    img.style.display = "none";
    fb.style.display = "block";
  };
  el.appendChild(img);
  el.appendChild(fb);
  if (clickable && onClick) {
    el.addEventListener("click", onClick);
  }
  return el;
}

function scoreList(title, data) {
  const wrapper = document.createElement("div");
  wrapper.className = "card";
  wrapper.innerHTML = `<h3 class="section-title">${title}</h3>`;
  const ul = document.createElement("ul");
  ul.className = "kv-list";
  for (const seat of ["E", "S", "W", "N"]) {
    const li = document.createElement("li");
    li.textContent = `${seatCN[seat]}(${seat}): ${(data?.[seat] ?? 0) >= 0 ? "+" : ""}${data?.[seat] ?? 0}`;
    ul.appendChild(li);
  }
  wrapper.appendChild(ul);
  return wrapper;
}

function renderPlaying() {
  const context = state.context;
  if (!context) {
    appEl.innerHTML = `<section class="card">等待状态推送...</section>`;
    return;
  }

  const discard = context.discard_view || { recent_by_player: {} };
  const hand = context.indexed_hand || [];
  const drawSplit = context.draw_split_index;
  const pending = state.pendingOptions || [];
  const discardTiles = new Set(pending.filter((o) => o.action === "DISCARD" && o.tile).map((o) => o.tile));
  const otherActions = pending.filter((o) => o.action !== "DISCARD");

  appEl.innerHTML = "";

  const top = document.createElement("section");
  top.className = "card";
  top.innerHTML = `
    <div class="title-row">
      <h2>第 ${context.turn} 轮</h2>
      <span class="small">庄家 ${seatCN[context.dealer]} | 当前 ${seatCN[context.current]}</span>
    </div>
    <div class="small">你的风位：${seatCN[state.playerSeat]}(${state.playerSeat}) | 牌墙 ${context.wall_count}</div>
  `;
  appEl.appendChild(top);

  const board = document.createElement("section");
  board.className = "card";
  board.innerHTML = `<h3 class="section-title">弃牌区</h3>`;
  for (const seat of ["E", "S", "W", "N"]) {
    const line = document.createElement("div");
    line.className = "seat-line";
    line.textContent = `${seatCN[seat]}(${seat})`;
    board.appendChild(line);
    const row = document.createElement("div");
    row.className = "tile-row";
    (discard.recent_by_player?.[seat] || []).forEach((tile) => row.appendChild(tileElement(tile)));
    if (!row.children.length) row.innerHTML = `<span class="small">(无)</span>`;
    board.appendChild(row);
  }
  const currentDiscard = context.last_discard;
  const current = document.createElement("div");
  current.className = "card";
  current.innerHTML = `<h3 class="section-title">当前打出</h3>`;
  if (Array.isArray(currentDiscard) && currentDiscard.length === 2) {
    const who = document.createElement("div");
    who.className = "small";
    who.textContent = `${seatCN[currentDiscard[0]]} 出牌`;
    current.appendChild(who);
    current.appendChild(tileElement(currentDiscard[1]));
  } else {
    current.innerHTML += `<div class="small">(无)</div>`;
  }

  const boardWrap = document.createElement("div");
  boardWrap.className = "columns";
  boardWrap.appendChild(board);
  boardWrap.appendChild(current);
  appEl.appendChild(boardWrap);

  const handCard = document.createElement("section");
  handCard.className = "card";
  handCard.innerHTML = `<h3 class="section-title">你的手牌</h3>`;
  const handRow = document.createElement("div");
  handRow.className = "tile-grid";
  hand.forEach((item, idx) => {
    const tile = item[1];
    const canDiscard = discardTiles.has(tile);
    const el = tileElement(tile, canDiscard, () => send({ type: "action", action: "DISCARD", tile }));
    if (drawSplit !== null && drawSplit !== undefined && idx === drawSplit) {
      const spacer = document.createElement("div");
      spacer.style.width = "12px";
      handRow.appendChild(spacer);
    }
    handRow.appendChild(el);
  });
  handCard.appendChild(handRow);
  appEl.appendChild(handCard);

  const act = document.createElement("section");
  act.className = "card";
  act.innerHTML = `<h3 class="section-title">动作区</h3>`;
  const actions = document.createElement("div");
  actions.className = "actions";
  for (const option of otherActions) {
    const btn = document.createElement("button");
    const tileTag = option.tile ? ` ${tileText(option.tile)}` : "";
    btn.textContent = `${actionCN[option.action] || option.action}${tileTag}`;
    btn.onclick = () => send({ type: "action", action: option.action, tile: option.tile });
    actions.appendChild(btn);
  }
  if (!otherActions.length && !discardTiles.size) {
    actions.innerHTML = `<span class="small">等待中...</span>`;
  }
  act.appendChild(actions);

  if (state.phase === "round_end") {
    const footer = document.createElement("div");
    footer.className = "actions";
    footer.style.marginTop = "8px";
    const nextBtn = document.createElement("button");
    nextBtn.textContent = "下一局";
    nextBtn.onclick = () => send({ type: "next_round" });
    const quitBtn = document.createElement("button");
    quitBtn.className = "danger";
    quitBtn.textContent = "退出";
    quitBtn.onclick = () => send({ type: "quit" });
    footer.append(nextBtn, quitBtn);
    act.appendChild(footer);
  }
  appEl.appendChild(act);
}

function renderHuWait() {
  const data = state.huWait || {};
  appEl.innerHTML = "";
  const card = document.createElement("section");
  card.className = "card";
  card.innerHTML = `<div class="title-row"><h2>${seatCN[data.winner_seat] || ""}(${data.winner_seat || ""}) 胡牌</h2></div>`;
  const row = document.createElement("div");
  row.className = "tile-grid";
  (data.winner_hand || []).forEach((tile) => row.appendChild(tileElement(tile)));
  card.appendChild(row);
  appEl.appendChild(card);

  const formula = document.createElement("section");
  formula.className = "card";
  formula.innerHTML = `<h3 class="section-title">买马计算公式</h3>`;
  const ul = document.createElement("ul");
  ul.className = "kv-list";
  (data.formula_lines || []).forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    ul.appendChild(li);
  });
  formula.appendChild(ul);
  const actions = document.createElement("div");
  actions.className = "actions";
  const startBtn = document.createElement("button");
  startBtn.textContent = "开始买马";
  startBtn.onclick = () => send({ type: "start_ma" });
  const quitBtn = document.createElement("button");
  quitBtn.className = "danger";
  quitBtn.textContent = "退出";
  quitBtn.onclick = () => send({ type: "quit" });
  actions.append(startBtn, quitBtn);
  formula.appendChild(actions);
  appEl.appendChild(formula);
}

function renderMaResult() {
  const data = state.maResult || {};
  appEl.innerHTML = "";

  const top = document.createElement("section");
  top.className = "card";
  top.innerHTML = `<h3 class="section-title">赢家手牌 ${seatCN[data.winner_seat] || ""}(${data.winner_seat || ""})</h3>`;
  const winRow = document.createElement("div");
  winRow.className = "tile-grid";
  (data.winner_hand || []).forEach((tile) => winRow.appendChild(tileElement(tile)));
  top.appendChild(winRow);
  appEl.appendChild(top);

  const middle = document.createElement("div");
  middle.className = "columns";
  const ma = document.createElement("section");
  ma.className = "card";
  ma.innerHTML = `<h3 class="section-title">马牌</h3>`;
  const ul = document.createElement("ul");
  ul.className = "kv-list";
  (data.ma_tiles || []).forEach((tile, idx) => {
    const li = document.createElement("li");
    const unit = data.ma_unit_scores?.[idx] || 0;
    li.textContent = `${tileText(tile)}: +${unit} (x100=+${unit * 100})`;
    ul.appendChild(li);
  });
  if (!ul.children.length) {
    const li = document.createElement("li");
    li.textContent = "(无)";
    ul.appendChild(li);
  }
  ma.appendChild(ul);

  const scoresWrap = document.createElement("div");
  scoresWrap.className = "card";
  const local = scoreList("本局分数", data.round_delta || state.roundDelta);
  const total = scoreList("总排行榜", data.leaderboard_total || state.leaderboardTotal);
  scoresWrap.append(local, total);

  middle.append(ma, scoresWrap);
  appEl.appendChild(middle);

  const self = document.createElement("section");
  self.className = "card";
  self.innerHTML = `<h3 class="section-title">自己手牌 ${seatCN[data.self_seat] || ""}(${data.self_seat || ""})</h3>`;
  const selfRow = document.createElement("div");
  selfRow.className = "tile-grid";
  (data.self_hand || []).forEach((tile) => selfRow.appendChild(tileElement(tile)));
  self.appendChild(selfRow);
  appEl.appendChild(self);

  const actions = document.createElement("section");
  actions.className = "card";
  actions.innerHTML = `<h3 class="section-title">下一步</h3>`;
  const bar = document.createElement("div");
  bar.className = "actions";
  const next = document.createElement("button");
  next.textContent = "下一局";
  next.onclick = () => send({ type: "next_round" });
  const quit = document.createElement("button");
  quit.className = "danger";
  quit.textContent = "退出";
  quit.onclick = () => send({ type: "quit" });
  bar.append(next, quit);
  actions.appendChild(bar);
  appEl.appendChild(actions);
}

function render() {
  if (state.phase === "hu_wait") {
    renderHuWait();
    return;
  }
  if (state.phase === "ma_result") {
    renderMaResult();
    return;
  }
  renderPlaying();
}

function handleEvent(evt) {
  const { type, payload } = evt;
  if (type === "state_update") {
    state.phase = payload.phase || state.phase;
    state.context = payload.context || state.context;
    state.pendingOptions = payload.pending_options || [];
    state.leaderboardTotal = payload.leaderboard_total || state.leaderboardTotal;
    state.roundDelta = payload.round_delta || state.roundDelta;
    render();
    return;
  }
  if (type === "hu_wait") {
    state.huWait = payload;
    state.phase = "hu_wait";
    render();
    return;
  }
  if (type === "ma_result") {
    state.maResult = payload;
    state.phase = "ma_result";
    render();
    return;
  }
  if (type === "error") {
    setStatus(payload.message || "发生错误", true);
    return;
  }
  if (type === "info" && payload?.message) {
    setStatus(payload.message);
    return;
  }
  if (type === "joined") {
    setStatus("已连接对局");
    return;
  }
}

async function boot() {
  try {
    const resp = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data?.detail || "创建会话失败");
    }
    state.sessionId = data.session_id;
    state.playerSeat = data.player_seat || "E";
    state.assetStatus = data.asset_status || null;
    if (state.assetStatus && !state.assetStatus.all_present) {
      setStatus(`素材缺失 ${state.assetStatus.missing_codes.length} 张，已自动降级显示中文牌名`);
    } else {
      setStatus("会话已创建，连接中...");
    }
  } catch (err) {
    setStatus(`启动失败: ${err.message}`, true);
    return;
  }

  const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${wsProto}://${window.location.host}/ws/sessions/${state.sessionId}`;
  const ws = new WebSocket(wsUrl);
  state.ws = ws;
  ws.onopen = () => {
    state.connected = true;
    send({ type: "join" });
    setStatus("连接成功");
  };
  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleEvent(payload);
    } catch (_e) {
      setStatus("收到无法解析的消息", true);
    }
  };
  ws.onclose = () => {
    state.connected = false;
    setStatus("连接已关闭，可刷新重进", true);
  };
  ws.onerror = () => {
    setStatus("连接发生错误", true);
  };
}

boot();
