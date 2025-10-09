// === THREE KINGS — GAME ENGINE (Refined Build) ===

// ---------------- Sound ----------------
let isToneInitialized = false;
let isMuted = false;

let masterGain, synthRow, synthTicket, paperNoise;

function initTone() {
  if (isToneInitialized || !window.Tone) return;
  masterGain = new Tone.Gain(0.28).toDestination();

  paperNoise = new Tone.NoiseSynth({
    noise: { type: "white" },
    envelope: { attack: 0.001, decay: 0.05, sustain: 0, release: 0.05 }
  }).connect(masterGain);

  synthRow = new Tone.Synth({
    oscillator: { type: "triangle" },
    envelope: { attack: 0.001, decay: 0.08, sustain: 0.1, release: 0.08 }
  }).connect(masterGain);

  synthTicket = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: "sine" },
    envelope: { attack: 0.005, decay: 0.2, sustain: 0.1, release: 0.2 }
  }).connect(masterGain);

  Tone.start();
  isToneInitialized = true;
}

const SFX = {
  pull() { if (!isToneInitialized || isMuted) return; paperNoise.triggerAttackRelease("32n"); },
  rowWin() { if (!isToneInitialized || isMuted) return; synthRow.triggerAttackRelease("E5", "16n"); },
  ticketWin() { if (!isToneInitialized || isMuted) return; synthTicket.triggerAttackRelease(["C5","E5","G5"], "8n"); }
};

// ---------------- State ----------------
const STATE = {
  balance: 1000.0,
  bet: 0.5,
  playing: false,
  results: {},
  auto: { active:false, turbo:false, remaining:0, timer:null },
  history: [],
  settings: {
    turboSticky: false,
    turboAutopull: true,
    showLastBets: true,
    turboInstant: false
  }
};

const BET = { base: 0.5, step: 0.5, max: 5 };

// ---------------- Symbols / RNG ----------------
const SYMBOLS = [
  { s:"🍒", p:0.5,  w:15 },
  { s:"🍋", p:1,    w:12 },
  { s:"🔔", p:2,    w:10 },
  { s:"🍊", p:3,    w: 8 },
  { s:"🍉", p:5,    w: 6 },
  { s:"⭐", p:10,   w: 4 },
  { s:"💵", p:25,  w: 2 },
  { s:"💎", p:50,  w: 1.5 },
  { s:"7️⃣", p:100, w: 1 },
  { s:"👑", p:250, w: 0.5 },
];

const REEL_SCALE = 2;
const REELS = buildReels(REEL_SCALE);
const REEL_LEN = REELS[0].length;

function buildReels(scale) {
  const base = [];
  SYMBOLS.forEach(sym => {
    const count = Math.floor(sym.w * scale);
    for (let i = 0; i < count; i++) base.push(sym.s);
  });
  return [shuffle(base.slice()), shuffle(base.slice()), shuffle(base.slice())];
}
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

let PAYTABLE = null;
function prizeFor(symbol) {
  if (PAYTABLE && PAYTABLE[symbol] !== undefined) return PAYTABLE[symbol];
  return SYMBOLS.find(x => x.s === symbol)?.p || 0;
}

// ---------------- DOM ----------------
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const EL = {
  status: $("#status-message"),
  balance: $("#balance-display"),
  betMinus: $("#bet-minus-btn"),
  betPlus: $("#bet-plus-btn"),
  betAmount: $("#bet-amount"),
  betHeader: $("#current-bet-display"),
  buyStop: $("#reset-button"),
  turbo: $("#turbo-btn"),
  autoToggle: $("#auto-play-toggle"),
  autoMenu: $("#auto-play-menu"),
  autoOptions: $$(".auto-option"),
  autoStartBtn: $("#auto-start-btn"),
  autoCancelBtn: $("#auto-cancel-btn"),
  settingsBtn: $("#settings-btn"),
  modal: $("#settings-modal-overlay"),
  autoplayModal: $("#autoplay-finish-overlay"),
  autoplayTitle: $("#autoplay-finish-title"),
  autoplayMessage: $("#autoplay-finish-message"),
  autoplayYes: $("#autoplay-replay-yes"),
  autoplayNo: $("#autoplay-replay-no"),
  mute: $("#mute-toggle"),
  turboInstant: $("#turbo-instant"),
  prizeList: $("#prize-list"),
  pullArea: $("#pull-area-wrapper"),
  tabs: $$(".pull-tab"),
};

// ---------------- UI Helpers ----------------
const fmt = n => `$${n.toFixed(2)}`;

function setStatus(content, mode) {
  const cls = mode === "win" ? "win-bg" :
              mode === "loss" ? "loss-bg" :
              mode === "idle" ? "idle" : "neutral";
  EL.status.className = "status-message " + cls;
  EL.status.innerHTML = content;
}

function setMultiplierDisplay(mult) {
  const el = $("#status-multiplier");
  el.textContent = mult == null ? "—" : `${mult}x`;
}

function updateBalanceBetUI() {
  STATE.bet = Math.max(BET.base, +(STATE.bet || 0));
  EL.balance.textContent = fmt(STATE.balance);
  EL.betAmount.textContent = fmt(STATE.bet);
  EL.betHeader.textContent = fmt(STATE.bet);
  updateActionButtonState();
}

// Disable/enable bet and buy buttons dynamically
function updateActionButtonState() {
  const active = STATE.playing || STATE.auto.active;

  // Disable bet controls while active
  EL.betMinus.disabled = active;
  EL.betPlus.disabled = active;
  EL.betMinus.classList.toggle('inactive', active);
  EL.betPlus.classList.toggle('inactive', active);

  // Disable buy button if insufficient funds or during play
  const insufficient = STATE.balance < STATE.bet;
  EL.buyStop.disabled = active || insufficient;
  EL.buyStop.classList.toggle('inactive', EL.buyStop.disabled);
}

// ---------------- Game Core ----------------
function lockGameUI(lock) {
  EL.betMinus.disabled = lock;
  EL.betPlus.disabled = lock;
  EL.pullArea.classList.toggle("game-disabled", !lock);
}

function drawRowsToDOM() {
  for (let i = 1; i <= 3; i++) {
    const [a,b,c] = STATE.results[i];
    $(`#symbols-1-${i}`).innerHTML = `<span>${a}</span><span>${b}</span><span>${c}</span>`;
  }
}

function newTicket() {
  if (STATE.balance < STATE.bet) {
    setStatus(`<span class="status-loss">INSUFFICIENT FUNDS</span>`, "loss");
    return;
  }

  initTone();
  STATE.playing = true;
  STATE.balance = +(STATE.balance - STATE.bet).toFixed(2);
  updateBalanceBetUI();
  clearHighlights();

  EL.tabs.forEach(t => t.classList.remove("pulled"));

  // Generate results
  const i = Math.floor(Math.random() * REEL_LEN);
  const j = Math.floor(Math.random() * REEL_LEN);
  const k = Math.floor(Math.random() * REEL_LEN);
  STATE.results = {};
  for (let r = 0; r < 3; r++) {
    const a = REELS[0][(i + r) % REEL_LEN];
    const b = REELS[1][(j + r) % REEL_LEN];
    const c = REELS[2][(k + r) % REEL_LEN];
    STATE.results[r + 1] = [a, b, c];
  }

  drawRowsToDOM();
  setStatus(`<span class="status-main">New Ticket</span><span class="subtext">Good luck!</span>`, "neutral");
  setMultiplierDisplay(null);
  lockGameUI(true);
}

function revealRow(rowIndex) {
  const [a,b,c] = STATE.results[rowIndex];
  if (a === b && b === c) {
    SFX.rowWin();
    $(`#symbols-1-${rowIndex}`).closest(".pull-window-row").classList.add("row-win");
    highlightPayLine(a);
  }
  checkEnd();
}

function checkEnd() {
  const done = EL.tabs.every(t => t.classList.contains("pulled"));
  if (!done) return;

  let total = 0;
  for (let i = 1; i <= 3; i++) {
    const [a,b,c] = STATE.results[i];
    if (a === b && b === c) total += prizeFor(a) * (STATE.bet / BET.base);
  }

  if (total > 0) {
    SFX.ticketWin();
    STATE.balance = +(STATE.balance + total).toFixed(2);
    const multiplier = +(total / STATE.bet).toFixed(2);
    setStatus(`<span class="status-win">WINNER</span><span class="subtext">+${fmt(total)}</span>`, "win");
    setMultiplierDisplay(multiplier);
  } else {
    setStatus(`<span class="status-loss">NOT A WINNER</span>`, "loss");
    setMultiplierDisplay(0);
  }

  STATE.playing = false;
  updateBalanceBetUI();
  lockGameUI(false);
}

// ---------------- Visuals ----------------
function highlightPayLine(symbol) {
  const li = [...EL.prizeList.querySelectorAll("li")].reverse()
    .find(x => x.textContent.includes(symbol));
  if (li) li.classList.add("pay-flash");
}

function clearHighlights() {
  $$(".pull-window-row").forEach(r => r.classList.remove("row-win"));
  EL.prizeList.querySelectorAll("li").forEach(li => li.classList.remove("pay-flash"));
}

function renderPrizeBoard() {
  EL.prizeList.innerHTML = "";
  const mult = STATE.bet / BET.base;
  [...SYMBOLS].sort((a,b) => b.p - a.p).forEach(p => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${p.s.repeat(3)}</span><span>${fmt(p.p * mult)}</span>`;
    EL.prizeList.appendChild(li);
  });
}

// ---------------- Bindings ----------------
function bindUI() {
  // Bet controls
  EL.betMinus.addEventListener("click", () => {
    if (STATE.playing) return;
    STATE.bet = Math.max(BET.base, STATE.bet - BET.step);
    updateBalanceBetUI(); renderPrizeBoard();
  });
  EL.betPlus.addEventListener("click", () => {
    if (STATE.playing) return;
    STATE.bet = Math.min(BET.max, STATE.bet + BET.step);
    updateBalanceBetUI(); renderPrizeBoard();
  });

  // Buy / Play
  EL.buyStop.addEventListener("click", () => {
    if (STATE.auto.active) return;
    if (!STATE.playing) {
      const turboActive = EL.turbo.classList.contains("turbo-active");
      newTicket();

      if (turboActive) {
        const tabs = [...EL.tabs];
        tabs.forEach((t, i) => {
          setTimeout(() => {
            if (!STATE.playing) return;
            t.classList.add("pulled");
            t.style.transform = "translateX(-100%)";
            SFX.pull();
            const [a,b,c] = STATE.results[i + 1];
            if (a === b && b === c) {
              SFX.rowWin();
              $(`#symbols-1-${i+1}`).closest(".pull-window-row").classList.add("row-win");
              highlightPayLine(a);
            }
            if (i === 2) checkEnd();
          }, i * (STATE.auto.turbo ? 250 : 700));
        });
      }
    }
  });

  // Turbo toggle
  EL.turbo.addEventListener("click", () => {
    STATE.auto.turbo = !STATE.auto.turbo;
    EL.turbo.classList.toggle("turbo-active", STATE.auto.turbo);
  });

  // Mute + Instant settings
  if (EL.mute) {
    EL.mute.addEventListener("change", e => {
      isMuted = e.target.checked;
    });
  }
  if (EL.turboInstant) {
    EL.turboInstant.addEventListener("change", e => {
      STATE.settings.turboInstant = e.target.checked;
    });
  }

  // Settings modal
  EL.settingsBtn.addEventListener("click", () => EL.modal.classList.add("active"));
  $("#close-settings").addEventListener("click", () => EL.modal.classList.remove("active"));
}

// ---------------- Init ----------------
function init() {
  EL.pullArea.classList.add("game-disabled");
  updateBalanceBetUI();
  renderPrizeBoard();
  setStatus("Ready Player? <b>SET BET and PLAY</b>", "idle");
  bindUI();
  attachDrag();
}

document.addEventListener("DOMContentLoaded", init);

// ---------------- Drag Mechanics ----------------
function attachDrag() {
  EL.tabs.forEach(tab => {
    const start = e => {
      if (!STATE.playing || tab.classList.contains("pulled")) return;
      initTone();
      const getX = evt => (evt.touches?.[0]?.clientX ?? evt.clientX);
      let startX = getX(e);
      const width = tab.offsetWidth;

      const onMove = evt => {
        const dx = getX(evt) - startX;
        const progress = Math.min(Math.max(-dx / width, 0), 1);
        const eased = progress < 0.37 ? progress * 0.7 : 0.26 + (progress - 0.37) * 1.4;
        tab.style.transition = "none";
        tab.style.transform = `translateX(${-width * eased}px)`;
      };

      const onEnd = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onEnd);
        document.removeEventListener("touchmove", onMove);
        document.removeEventListener("touchend", onEnd);
        const m = new DOMMatrix(getComputedStyle(tab).transform);
        const pulledPct = Math.min(Math.abs(m.m41) / width, 1);
        tab.style.transition = "transform 0.3s cubic-bezier(.19,1,.22,1)";
        if (pulledPct > 0.37) {
          tab.classList.add("pulled");
          tab.style.transform = "translateX(-100%)";
          SFX.pull();
          revealRow(+tab.dataset.panel);
        } else tab.style.transform = "translateX(0)";
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onEnd);
      document.addEventListener("touchmove", onMove, { passive: false });
      document.addEventListener("touchend", onEnd);
    };

    tab.addEventListener("mousedown", start);
    tab.addEventListener("touchstart", start, { passive: false });
  });
}
