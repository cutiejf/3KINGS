try {
  var debugBanner = document.getElementById('debug-banner');
  var debugMsg = document.getElementById('debug-banner-msg');
  var debugMin = document.getElementById('debug-banner-min');
  if (debugBanner && debugMsg) {
    debugBanner.style.display = 'block';
    debugMsg.textContent = 'Three Kings game.js loaded';
    if (debugMin) {
      debugMin.onclick = function() {
        debugBanner.style.display = 'none';
      };
    }
  }
} catch (e) {}
"use strict";

const STATE = {
  balance: 1000.0,
  bet: 0.5,
  playing: false,
  results: {},
  history: [],
  turbo: false,
  instant: false,
  auto: { active: false, remaining: 0, timer: null, _pendingCount: 0, _lastCount: 0, _skipConfirm: false },
};

const BET = { base: 0.5, step: 0.5, max: 5 };
let PAYTABLE = {};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const fmt = (n) => `$${n.toFixed(2)}`;

// ---- Sound helpers ----
function initToneSafe() { try { if (typeof initTone === 'function') initTone(); } catch (_) {} }
function sfxCall(name, ...args) { try { if (typeof SFX !== 'undefined' && typeof SFX[name] === 'function') SFX[name](...args); } catch(_) {} }
function toggleMuteHandler(e) { try { if (typeof masterGain !== 'undefined' && masterGain) { masterGain.gain.value = e.target.checked ? 0 : 0.28; } } catch(_) {} }

// ---- Symbols ----
const SYMBOLS = [
  { s: "🍒", p: 2.41,   w: 320 },
  { s: "🍋", p: 5.30,   w: 260 },
  { s: "🔔", p: 12.53,  w: 180 },
  { s: "🍊", p: 26.96,  w: 110 },
  { s: "🍉", p: 57.81,  w: 70 },
  { s: "⭐", p: 125.29, w: 35 },
  { s: "💵", p: 211.97, w: 18 },
  { s: "💎", p: 404.67, w: 9 },
  { s: "7️⃣", p: 818.98, w: 4 },
  { s: "👑", p: 1735.00,w: 2 },
];

// ---- Paytable ----
async function loadPaytable() {
  PAYTABLE = Object.fromEntries(SYMBOLS.map(x => [x.s, x.p]));
}

function prizeFor(sym) { 
  const v = parseFloat(PAYTABLE[sym]); 
  return isNaN(v) ? 0 : v; 
}

function renderPrizeBoard() {
  const list = $("#prize-list"); 
  if (!list) return; 
  list.innerHTML = "";
  Object.entries(PAYTABLE)
    .sort((a,b)=>parseFloat(b[1])-parseFloat(a[1]))
    .forEach(([symbol, mult]) => {
      const li = document.createElement("li");
      const prizeValue = parseFloat(mult) * STATE.bet;
      li.innerHTML = `<span class="symbol">${symbol}${symbol}${symbol}</span><span class="prize">${fmt(prizeValue)}</span>`;
      list.appendChild(li);
    });
}

// ---- History rendering ----
function renderHistory() {
  const list = document.getElementById('last-bets-list');
  if (!list) return;
  list.innerHTML = '';
  
  if (!STATE.history.length) {
    list.innerHTML = '<li>No bets yet.</li>';
    return;
  }
  
  STATE.history.slice(0, 100).forEach((h, idx) => {
    const li = document.createElement('li');
    li.className = (h.win > 0) ? 'win' : 'loss';
    li.style.gridTemplateColumns = '70px 70px 80px 110px'; // Column 4 now 100px
    
    // Column 1: Symbol grid (3x3)
    const grid = document.createElement('div');
    grid.className = 'symbol-group';
    const rows = [h.results.slice(0,3), h.results.slice(3,6), h.results.slice(6,9)];
    rows.forEach(r => {
      const line = document.createElement('div');
      line.className = 'symbol-line';
      r.forEach(s => {
        const sp = document.createElement('span');
        sp.className = 'symbols';
        sp.textContent = s || '-';
        line.appendChild(sp);
      });
      grid.appendChild(line);
    });
    
    // Column 2: Bet (simple centered value)
    const colBet = document.createElement('span');
    colBet.textContent = fmt(h.bet || 0);
    colBet.style.display = 'flex';
    colBet.style.alignItems = 'center';
    colBet.style.justifyContent = 'center';
    colBet.style.fontWeight = '600';
    
    // Column 3: Payout (top) and Multiplier (bottom)
    const colPayoutMulti = document.createElement('span');
    colPayoutMulti.style.display = 'flex';
    colPayoutMulti.style.flexDirection = 'column';
    colPayoutMulti.style.justifyContent = 'center';
    colPayoutMulti.style.gap = '2px';
    
    const payout = document.createElement('div');
    payout.textContent = h.win > 0 ? fmt(h.win) : '-';
    payout.style.fontWeight = '700';
    payout.style.fontSize = '0.95em';
    payout.style.color = h.win > 0 ? 'var(--accent-lime)' : 'var(--light-gray)';
    
    const multi = document.createElement('div');
    let multiVal = h.bet && h.win ? +(h.win / h.bet).toFixed(2) : 0;
    multi.textContent = multiVal ? `${multiVal}x` : '-';
    multi.style.fontSize = '0.8em';
    multi.style.color = 'var(--light-gray)';
    multi.style.opacity = '0.8';
    
    if (multiVal >= 10) {
      const trophy = document.createElement('span');
      trophy.textContent = ' 🏆';
      trophy.title = '10x+ Win!';
      multi.appendChild(trophy);
    }
    
    colPayoutMulti.appendChild(payout);
    colPayoutMulti.appendChild(multi);
    
    // Column 4: Date/Time and Code (right-aligned, bigger font)
    const colTime = document.createElement('span');
    colTime.style.display = 'flex';
    colTime.style.flexDirection = 'column';
    colTime.style.justifyContent = 'center';
    colTime.style.alignItems = 'flex-end'; // Keep right-aligned
    colTime.style.gap = '4px';
    
    try {
      const d = new Date(h.ts);
      
      // Date and time combined (bold date, regular time) - BIGGER
      const dateTime = document.createElement('div');
      dateTime.style.fontSize = '1.1em'; // Bigger font
      dateTime.style.lineHeight = '1.2';
      
      const dateSpan = document.createElement('span');
      dateSpan.textContent = `${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
      dateSpan.style.fontWeight = '900';
      
      const timeSpan = document.createElement('span');
      timeSpan.textContent = ` ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
      timeSpan.style.fontWeight = '900';
      
      dateTime.appendChild(dateSpan);
      dateTime.appendChild(timeSpan);
      
      // Ticket code - BIGGER
      const code = document.createElement('div');
      code.textContent = `#${d.getFullYear().toString().slice(-2)}${(d.getMonth()+1).toString().padStart(2,'0')}${d.getDate().toString().padStart(2,'0')}-${idx.toString().padStart(3, '0')}`;
      code.style.fontSize = '1em'; // Bigger code
      code.style.color = 'var(--light-gray)';
      code.style.opacity = '0.8';
      
      colTime.appendChild(dateTime);
      colTime.appendChild(code);
    } catch(_) {
      colTime.textContent = '-';
    }
    
    li.appendChild(grid);
    li.appendChild(colBet);
    li.appendChild(colPayoutMulti);
    li.appendChild(colTime);
    list.appendChild(li);
  });
}

function setStatus(html, mode) {
  const el = $("#status-message"); 
  if (!el) return;
  const cls = mode === "win" ? "win-bg" : mode === "loss" ? "loss-bg" : mode === "idle" ? "idle" : "neutral";
  el.className = `status-message ${cls}`; 
  el.innerHTML = html;
}

function setMultiplierDisplay(value) {
  const el = $("#status-multiplier"); 
  if (!el) return;
  el.textContent = value == null ? "-" : String(value);
}

function updateBalanceBetUI() {
  $("#balance-display") && ($("#balance-display").textContent = fmt(STATE.balance));
  $("#bet-amount") && ($("#bet-amount").textContent = fmt(STATE.bet));
  $("#current-bet-display") && ($("#current-bet-display").textContent = fmt(STATE.bet));
}

function updatePlayButtonUI() {
  const btn = $("#reset-button"); 
  if (!btn) return;
  btn.textContent = STATE.auto.active ? `STOP (${STATE.auto.remaining})` : (STATE.playing ? "REVEAL ALL" : "BUY TICKET");
}

function updateTabEnabledState() {
  const canPull = STATE.playing;
  $$(".pull-tab").forEach(tab => {
    const isPulled = tab.classList.contains("pulled");
    
    // Remove all state classes first
    tab.classList.remove("disabled", "active", "locked");
    
    if (isPulled) {
      // Already pulled - keep pulled state
      tab.classList.add("pulled");
    } else if (canPull) {
      // Can be pulled
      tab.classList.add("active");
      tab.setAttribute("tabindex", "0");
      tab.setAttribute("aria-disabled", "false");
    } else {
      // Locked (waiting for ticket purchase)
      tab.classList.add("locked");
      tab.setAttribute("tabindex", "-1");
      tab.setAttribute("aria-disabled", "true");
    }
  });
}

function updateControlsEnabledState() {
  const minus = $("#bet-minus-btn");
  const plus = $("#bet-plus-btn");
  const autoToggle = $("#auto-play-toggle");
  const autoStartBtn = $("#auto-start-btn");
  
  // Disable bet +/- during play or autoplay
  const disableBet = STATE.playing || STATE.auto.active;
  if (minus) minus.disabled = disableBet;
  if (plus) plus.disabled = disableBet;
  
  // Disable autoplay toggle during play or autoplay
  if (autoToggle) autoToggle.disabled = STATE.playing || STATE.auto.active;
  
  // Disable start button during autoplay
  if (autoStartBtn) autoStartBtn.disabled = STATE.auto.active;
}

// ---- RNG / Reels ----
function buildReels() {
  const base = [];
  const sumW = SYMBOLS.reduce((s,x)=>s+(x.w||0),0);
  const desired = Math.max(30,Math.floor(sumW*0.3));
  SYMBOLS.forEach(sym => {
    const c = Math.max(1,Math.round((sym.w/sumW)*desired));
    for(let i=0; i<c; i++) base.push(sym.s);
  });
  return [shuffle(base.slice()), shuffle(base.slice()), shuffle(base.slice())];
}

function shuffle(a) {
  for(let i=a.length-1; i>0; i--) {
    const j=Math.floor(Math.random()*(i+1));
    [a[i],a[j]]=[a[j],a[i]];
  }
  return a;
}

const REELS = buildReels();
const REEL_LEN = REELS[0].length;

function chooseTicket() {
  const i=r(), j=r(), k=r();
  const rows = {};
  for(let t=0; t<3; t++) {
    rows[t+1] = [
      REELS[0][(i+t)%REEL_LEN],
      REELS[1][(j+t)%REEL_LEN],
      REELS[2][(k+t)%REEL_LEN]
    ];
  }
  return rows;
  function r() { return Math.floor(Math.random()*REEL_LEN); }
}

function drawRowsToDOM() {
  for(let r=1; r<=3; r++) {
    const c = document.getElementById(`symbols-1-${r}`);
    if(!c) continue;
    c.innerHTML='';
    (STATE.results[r]||[]).forEach(sym => {
      const sp = document.createElement('span');
      sp.className='symbols';
      sp.textContent=sym;
      c.appendChild(sp);
    });
  }
}

// ---- Game flow ----
function buyTicket() {
  if (STATE.playing) return;
  if (STATE.balance < STATE.bet) {
    setStatus(`<span class="status-loss">INSUFFICIENT FUNDS</span>`, "loss");
    return;
  }
  
  initToneSafe();
  STATE.playing = true;
  STATE.balance = +(STATE.balance - STATE.bet).toFixed(2);
  updateBalanceBetUI();
  setStatus(`<span class="status-main">New Ticket</span><span class="subtext">Good luck!</span>`, "neutral");
  setMultiplierDisplay(null);
  
  // Reset tabs
  $$(".pull-tab").forEach(t => {
    t.classList.remove("pulled");
    t.style.transform = "translateX(0)";
    t.style.opacity = "1";
  });
  
  STATE.results = chooseTicket();
  drawRowsToDOM();
  updateTabEnabledState();
  updatePlayButtonUI();
  updateControlsEnabledState();
  
  if (STATE.instant && !STATE.auto.active) {
    setTimeout(() => revealAll(), STATE.turbo ? 60 : 120);
  }
}

function revealPanel(panelId) {
  if (!STATE.playing) return;
  
  const tab = document.querySelector(`.pull-tab[data-panel="${panelId}"]`);
  if (!tab || tab.classList.contains('pulled') || !tab.classList.contains('active')) return;
  
  sfxCall('pull');
  tab.classList.remove('active');
  tab.classList.add('pulled');
  tab.style.transform = 'translateX(-100%)';
  
  revealRow(parseInt(panelId, 10));
  updateTabEnabledState();
}

function revealAll() {
  const ids = [1, 2, 3];
  if (STATE.instant) {
    ids.forEach(id => revealPanel(id));
  } else {
    const step = STATE.turbo ? 80 : 140;
    ids.forEach((id, i) => setTimeout(() => revealPanel(id), i * step));
  }
}

function revealRow(rowIndex) {
  const [a, b, c] = STATE.results[rowIndex] || [null, null, null];
  if (a && a === b && b === c) {
    const rowEl = document.querySelector(`#symbols-1-${rowIndex}`);
    if (rowEl) {
      const rowWrap = rowEl.closest('.pull-window-row');
      if (rowWrap) rowWrap.classList.add('row-win');
    }
    sfxCall('rowWin');
  }
  checkEnd();
}

function checkEnd() {
  const done = $$(".pull-tab").every(t => t.classList.contains('pulled'));
  if (!done) return;
  
  let total = 0;
  for(let i=1; i<=3; i++) {
    const [a, b, c] = STATE.results[i];
    if (a === b && b === c) {
      total += prizeFor(a) * STATE.bet;
    }
  }
  
  if (total > 0) {
    STATE.balance = +(STATE.balance + total).toFixed(2);
    setStatus(`<span class="status-win">WINNER</span><span class="subtext">+${fmt(total)}</span>`, 'win');
    setMultiplierDisplay(+(total/STATE.bet).toFixed(2));
    sfxCall('ticketWin');
  } else {
    setStatus(`<span class="status-loss">NOT A WINNER</span>`, 'loss');
    setMultiplierDisplay(0);
    sfxCall('buzz');
  }
  
  // Record history
  try {
    const flat = [
      ...(STATE.results[1]||[]),
      ...(STATE.results[2]||[]),
      ...(STATE.results[3]||[])
    ];
    STATE.history.unshift({
      bet: STATE.bet,
      win: total,
      results: flat,
      ts: new Date().toISOString()
    });
    if (STATE.history.length > 100) STATE.history.length = 100;
    renderHistory();
  } catch(_) {}
  
  updateBalanceBetUI();
  saveState();
  setTimeout(() => resetRound(), 550);
}

function resetRound() {
  STATE.playing = false;
  
  $$(".pull-tab").forEach(t => {
    t.classList.remove('pulled');
    t.style.transform = 'translateX(0)';
    t.style.opacity = '1';
  });
  
  $$(".pull-window-row").forEach(r => r.classList.remove('row-win'));
  
  updateTabEnabledState();
  updatePlayButtonUI();
  updateControlsEnabledState();
  
  if (STATE.auto.active) {
    scheduleNextAuto();
  }
}

function adjustBet(dir) {
  if (STATE.playing || STATE.auto.active) return;
  
  let next = STATE.bet + dir * BET.step;
  next = Math.max(BET.base, Math.min(BET.max, next));
  
  if (next !== STATE.bet) {
    STATE.bet = +next.toFixed(2);
    updateBalanceBetUI();
    renderPrizeBoard();
    saveState();
  }
}

// ---- Local Storage ----
function saveState() {
  try {
    const toSave = {
      balance: STATE.balance,
      bet: STATE.bet,
      history: STATE.history.slice(0, 100)
    };
    localStorage.setItem("threeKingsGameState", JSON.stringify(toSave));
  } catch (e) {
    console.warn("Could not save game state.", e);
  }
}

function loadState() {
  try {
    const saved = localStorage.getItem("threeKingsGameState");
    if (saved) {
      const data = JSON.parse(saved);
      STATE.balance = data.balance ?? 1000.0;
      STATE.bet = data.bet ?? 0.5;
      STATE.history = data.history ?? [];
    }
  } catch (e) {
    console.warn("Could not load game state.", e);
  }
}

// ---- Settings ----
function switchTab(panelId) {
  $$(".tab-btn").forEach(b => b.classList.toggle('active', b.dataset.panel === panelId));
  const ids = ['general', 'lastbets'];
  ids.forEach(id => {
    const el = document.getElementById(`panel-${id}`);
    if (el) el.style.display = (id === panelId) ? 'block' : 'none';
  });
  if (panelId === 'lastbets') renderHistory();
}

// ---- Autoplay ----
function startAutoPlay() {
  const menu = $("#auto-play-menu");
  
  // Always read from the selected option first (don't use old pending count)
  const selected = $(".auto-option.selected");
  let count = selected ? parseInt(selected.dataset.count, 10) : STATE.auto._pendingCount;
  
  if (!count || count <= 0) {
    setStatus('Select an auto-play count', 'neutral');
    return;
  }
  
  // Update pending count with the current selection
  STATE.auto._pendingCount = count;
  
  // Show confirmation modal before starting
  if (!STATE.auto._skipConfirm) {
    showModal('autoplay-confirm-overlay');
    const confirmMsg = document.getElementById('autoplay-confirm-message');
    if (confirmMsg) confirmMsg.textContent = `Start autoplay for ${count} rounds?`;
    STATE.auto._pendingCount = count;
    return;
  }
  
  menu && menu.classList.remove('active');
  STATE.auto.active = true;
  STATE.auto.remaining = count;
  STATE.auto._lastCount = count;
  
  updatePlayButtonUI();
  updateControlsEnabledState();
  
  if (STATE.auto.timer) {
    clearTimeout(STATE.auto.timer);
    STATE.auto.timer = null;
  }
  
  if (!STATE.playing) buyTicket();
  scheduleAutoplayReveal();
  STATE.auto._skipConfirm = false;
}

function stopAutoPlay() {
  STATE.auto.active = false;
  STATE.auto.remaining = 0;
  STATE.auto._pendingCount = 0; // Clear pending count when stopping
  
  if (STATE.auto.timer) {
    clearTimeout(STATE.auto.timer);
    STATE.auto.timer = null;
  }
  
  updatePlayButtonUI();
  updateControlsEnabledState();
}

function scheduleNextAuto() {
  if (!STATE.auto.active) return;
  
  if (STATE.auto.remaining <= 0) {
    stopAutoPlay();
    showAutoplayFinishedModal();
    return;
  }
  
  updatePlayButtonUI();
  updateControlsEnabledState();
  
  const gap = STATE.turbo ? 220 : 380;
  STATE.auto.timer = setTimeout(() => {
    if (!STATE.playing) {
      STATE.auto.remaining -= 1;
      buyTicket();
    }
    scheduleAutoplayReveal();
  }, gap);
}

function scheduleAutoplayReveal() {
  if (!STATE.auto.active) return;
  
  const delay = STATE.instant ? (STATE.turbo ? 20 : 60) : (STATE.turbo ? 80 : 160);
  
  if (STATE.auto.timer) {
    clearTimeout(STATE.auto.timer);
    STATE.auto.timer = null;
  }
  
  STATE.auto.timer = setTimeout(() => revealAll(), delay);
}

function showAutoplayFinishedModal() {
  showModal('autoplay-finish-overlay');
  const msg = document.getElementById('autoplay-finish-message');
  if (msg) {
    const lastCount = STATE.auto._lastCount || STATE.auto._pendingCount || 0;
    msg.textContent = `Autoplay finished! Replay ${lastCount} rounds?`;
  }
}

// ---- Modal helpers ----
function showModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'flex';
    modal.classList.add('active');
    modal.style.zIndex = 9999;
  }
}

function hideModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('active');
    modal.style.zIndex = '';
  }
}

function showSettings(show = true) {
  const modal = document.getElementById("settings-modal-overlay");
  if (!modal) return;
  
  if (show) {
    showModal('settings-modal-overlay');
  } else {
    hideModal('settings-modal-overlay');
  }
}

// ---- Event binding ----
function bindUI() {
  // Autoplay finished modal
  const autoplayYes = document.getElementById('autoplay-replay-yes');
  const autoplayNo = document.getElementById('autoplay-replay-no');
  
  if (autoplayYes) {
    autoplayYes.onclick = function() {
      hideModal('autoplay-finish-overlay');
      STATE.auto._skipConfirm = true;
      let count = STATE.auto._lastCount || STATE.auto._pendingCount || 0;
      const selected = $(".auto-option.selected");
      if (selected && count) selected.dataset.count = count;
      STATE.auto._pendingCount = count;
      STATE.auto._lastCount = count;
      startAutoPlay();
    };
  }
  
  if (autoplayNo) {
    autoplayNo.onclick = function() {
      hideModal('autoplay-finish-overlay');
      STATE.auto._skipConfirm = false;
    };
  }
  
  // Autoplay confirmation modal
  const autoConfirmYes = document.getElementById('autoplay-confirm-yes');
  const autoConfirmNo = document.getElementById('autoplay-confirm-no');
  
  if (autoConfirmYes) {
    autoConfirmYes.onclick = function() {
      hideModal('autoplay-confirm-overlay');
      STATE.auto._skipConfirm = true;
      if (typeof STATE.auto._pendingCount === 'number') {
        const selected = $(".auto-option.selected");
        if (selected) selected.dataset.count = STATE.auto._pendingCount;
      }
      startAutoPlay();
    };
  }
  
  if (autoConfirmNo) {
    autoConfirmNo.onclick = function() {
      hideModal('autoplay-confirm-overlay');
      STATE.auto._skipConfirm = false;
    };
  }
  
  // Pull tabs
  $$(".pull-tab").forEach(t => {
    t.addEventListener('click', () => revealPanel(t.dataset.panel));
    t.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        revealPanel(t.dataset.panel);
      }
    });
  });
  
  // Bet controls
  const minusBtn = $("#bet-minus-btn");
  if (minusBtn) minusBtn.addEventListener('click', () => adjustBet(-1));
  
  const plusBtn = $("#bet-plus-btn");
  if (plusBtn) plusBtn.addEventListener('click', () => adjustBet(1));
  
  // Buy/Reveal/Stop button
  const buyBtn = $("#reset-button");
  if (buyBtn) {
    buyBtn.addEventListener('click', () => {
      if (STATE.auto.active) {
        stopAutoPlay();
        return;
      }
      if (STATE.playing) {
        revealAll();
      } else {
        buyTicket();
      }
    });
  }
  
  // Settings modal
  const settingsBtn = $("#settings-btn");
  const closeBtn = $("#close-settings");
  
  if (settingsBtn) settingsBtn.addEventListener('click', () => showSettings(true));
  if (closeBtn) closeBtn.addEventListener('click', () => showSettings(false));
  
  const modal = $("#settings-modal-overlay");
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) showSettings(false);
    });
  }
  
  // Settings tabs
  $$(".tab-btn").forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.panel));
  });
  
  // Toggles
  const turboT = $("#turbo-toggle");
  if (turboT) {
    turboT.addEventListener('change', function(e) {
      STATE.turbo = !!e.target.checked;
    });
  }
  
  const instantT = $("#instant-toggle");
  if (instantT) {
    instantT.addEventListener('change', function(e) {
      STATE.instant = !!e.target.checked;
    });
  }
  
  const muteT = $("#mute-toggle");
  if (muteT) muteT.addEventListener('change', toggleMuteHandler);
  
  // Autoplay menu
  const autoToggle = $("#auto-play-toggle");
  const autoMenu = $("#auto-play-menu");
  
  if (autoToggle) {
    autoToggle.addEventListener('click', function() {
      if (autoMenu) autoMenu.classList.toggle('active');
    });
  }
  
  $$(".auto-option").forEach(function(btn) {
    btn.addEventListener('click', function() {
      $$(".auto-option").forEach(function(b) {
        b.classList.remove('selected');
      });
      btn.classList.add('selected');
    });
  });
  
  const cancelBtn = $("#auto-cancel-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function() {
      if (autoMenu) autoMenu.classList.remove('active');
    });
  }
  
  const autoStartBtn = $("#auto-start-btn");
  if (autoStartBtn) {
    autoStartBtn.addEventListener('click', function(e) {
      e.preventDefault();
      startAutoPlay();
    });
  }
}

// ---- Initialize ----
document.addEventListener('DOMContentLoaded', async () => {
  await loadPaytable();
  loadState();
  renderPrizeBoard();
  updateBalanceBetUI();
  bindUI();
  updateTabEnabledState();
  updateControlsEnabledState();
  setStatus('Ready Player? <b>Set Bet and Play</b>', 'idle');
  renderHistory();
});