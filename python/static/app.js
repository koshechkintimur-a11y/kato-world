/* Kato World — God View Dashboard */
const API = '';
const AGENT = 'kato';
const TILE = 16;
const WORLD_W = 50, WORLD_H = 30;

let state = null;
let world = null;
let selfModel = null;
let activeMemTab = 'episodic';

// ── DOM helpers ────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function setConn(on) {
  const el = $('conn-status');
  el.className = on ? 'on' : 'off';
  el.textContent = on ? '● МОЗГ ПОДКЛЮЧЁН' : '● МОЗГ НЕ ПОДКЛЮЧЁН';
}

// ── API ────────────────────────────────────────────────────────
async function api(path) {
  try {
    const r = await fetch(API + path, { headers: { 'Accept': 'application/json' } });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) { return null; }
}
async function apiPost(path, body) {
  try {
    const r = await fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) { return null; }
}

// ── Polling ────────────────────────────────────────────────────
async function poll() {
  const [st, wd, sm, answers] = await Promise.all([
    api(`/agent/${AGENT}/state`),
    api(`/agent/${AGENT}/world`),
    api(`/agent/${AGENT}/self-model`),
    api(`/agent/${AGENT}/self-model/answers`)
  ]);
  if (st) { state = st; setConn(true); renderAgent(); renderEmotions(); }
  else setConn(false);
  if (wd) { world = wd; renderWorld(); renderEvents(); }
  if (sm) { selfModel = sm; renderSelf(); }
  if (answers) renderAnswers(answers);
  renderMemory();
}

// ── WORLD CANVAS ───────────────────────────────────────────────
function drawPixel(ctx, x, y, w, h, color) {
  ctx.fillStyle = color;
  ctx.fillRect(x * TILE, y * TILE, w, h);
}
function drawSprite(ctx, x, y, pixels) {
  // pixels: 2D array of color strings or null
  for (let py = 0; py < pixels.length; py++)
    for (let px = 0; px < pixels[py].length; px++) {
      const c = pixels[py][px];
      if (c) drawPixel(ctx, x + px, y + py, 1, 1, c);
    }
}

const SPRITES = {
  bed: [
    [null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null,null,null],
    [null,'#7a4a2a','#9a6a4a','#9a6a4a','#9a6a4a','#9a6a4a','#9a6a4a','#7a4a2a',null,null,null,null,null,null,null,null],
    [null,'#7a4a2a','#f0e6d2','#f0e6d2','#f0e6d2','#f0e6d2','#f0e6d2','#7a4a2a',null,null,null,null,null,null,null,null],
    [null,'#7a4a2a','#f0e6d2','#e8c8a0','#e8c8a0','#e8c8a0','#e8c8a0','#7a4a2a',null,null,null,null,null,null,null,null],
    [null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null,null,null],
    [null,null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null,null,null,null,null]
  ],
  terminal: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#2a2a3a','#2a2a3a','#2a2a3a','#2a2a3a',null,null,null,null,null],
    [null,null,null,null,null,null,null,'#2a2a3a','#30d0c0','#30d0c0','#2a2a3a',null,null,null,null,null],
    [null,null,null,null,null,null,null,'#2a2a3a','#30d0c0','#30d0c0','#2a2a3a',null,null,null,null,null],
    [null,null,null,null,null,null,null,'#2a2a3a','#30d0c0','#30d0c0','#2a2a3a',null,null,null,null,null],
    [null,null,null,null,null,null,null,'#3a3a5a','#3a3a5a','#3a3a5a','#3a3a5a',null,null,null,null,null],
    [null,null,null,null,null,null,'#2a2a3a','#4a4a6a','#4a4a6a','#4a4a6a','#4a4a6a','#2a2a3a',null,null,null,null],
    [null,null,null,null,null,null,'#2a2a3a','#4a4a6a','#4a4a6a','#4a4a6a','#4a4a6a','#2a2a3a',null,null,null,null]
  ],
  chest: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,'#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a',null,null,null,null,null,null],
    [null,null,null,null,'#8a5a2a','#c8a050','#c8a050','#c8a050','#c8a050','#8a5a2a',null,null,null,null,null,null],
    [null,null,null,null,'#6a4a20','#6a4a20','#6a4a20','#6a4a20','#6a4a20','#6a4a20',null,null,null,null,null,null],
    [null,null,null,null,'#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a','#8a5a2a',null,null,null,null,null,null],
    [null,null,null,null,'#6a4a20','#6a4a20','#6a4a20','#6a4a20','#6a4a20','#6a4a20',null,null,null,null,null,null]
  ],
  lamp: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#f5d76e','#f5d76e',null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#f5d76e','#f5d76e',null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#8a8a5a','#8a8a5a',null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#6a5a3a',null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#6a5a3a',null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,'#6a5a3a',null,null,null,null,null,null,null],
    [null,null,null,null,'#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a',null,null,null,null,null,null]
  ],
  book: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,'#c05040','#c05040','#c05040','#c05040','#c05040',null,null,null,null,null],
    [null,null,null,null,null,null,'#c05040','#e8dcc0','#e8dcc0','#e8dcc0','#c05040',null,null,null,null,null],
    [null,null,null,null,null,null,'#c05040','#e8dcc0','#e8dcc0','#e8dcc0','#c05040',null,null,null,null,null],
    [null,null,null,null,null,null,'#c05040','#c05040','#c05040','#c05040','#c05040',null,null,null,null,null]
  ],
  door: [
    [null,null,null,null,null,null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#f5d76e','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#f5d76e','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#7a4a2a','#f5d76e','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null]
  ],
  window: [
    [null,null,null,null,'#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#6a5a3a','#4a8ac0','#4a8ac0','#6a5a3a',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#6a5a3a','#4a8ac0','#4a8ac0','#6a5a3a',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a',null,null,null,null,null,null,null,null]
  ],
  mirror: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,'#c8c8d8','#c8c8d8','#c8c8d8','#c8c8d8',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#c8c8d8','#e8e8ff','#e8e8ff','#c8c8d8',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#c8c8d8','#e8e8ff','#e8e8ff','#c8c8d8',null,null,null,null,null,null,null,null],
    [null,null,null,null,'#c8c8d8','#c8c8d8','#c8c8d8','#c8c8d8',null,null,null,null,null,null,null,null],
    [null,null,null,null,null,'#8a8a9a','#8a8a9a',null,null,null,null,null,null,null,null,null]
  ],
  plant: [
    [null,null,null,null,null,null,null,'#2a8a3a',null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3aa04a','#2a8a3a','#3aa04a',null,null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3aa04a','#4ab85a','#3aa04a',null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#4ab85a',null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#5a4a2a',null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#5a4a2a',null,null,null,null,null,null,null,null],
    [null,null,null,null,null,'#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a',null,null,null,null,null,null],
    [null,null,null,null,null,'#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a','#6a5a3a',null,null,null,null,null,null]
  ],
  desk: [
    [null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],
    [null,null,null,null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,'#7a4a2a','#9a6a4a','#9a6a4a','#9a6a4a','#9a6a4a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,'#7a4a2a','#9a6a4a','#9a6a4a','#9a6a4a','#9a6a4a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,'#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a','#7a4a2a',null,null,null,null,null,null],
    [null,null,null,null,null,'#5a3a1a',null,null,null,'#5a3a1a',null,null,null,null,null,null],
    [null,null,null,null,null,'#5a3a1a',null,null,null,'#5a3a1a',null,null,null,null,null,null]
  ],
  shelf: [
    [null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#c05040','#4070b0','#c0a030','#5a3a1a','#c05040','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#4070b0','#c0a030','#c05040','#5a3a1a','#4070b0','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#c0a030','#c05040','#4070b0','#5a3a1a','#c0a030','#5a3a1a',null,null,null,null,null,null,null,null],
    [null,'#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a','#5a3a1a',null,null,null,null,null,null,null,null]
  ]
};

const AGENT_SPRITE = [
  [null,null,null,null,'#80c0e0','#80c0e0','#80c0e0','#80c0e0',null,null,null,null],
  [null,null,null,'#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0',null,null,null],
  [null,null,null,'#80c0e0','#f8f8f8','#80c0e0','#80c0e0','#f8f8f8','#80c0e0',null,null,null],
  [null,null,null,'#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0',null,null,null],
  [null,null,null,'#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0','#80c0e0',null,null,null],
  [null,null,null,'#6090b0','#6090b0','#6090b0','#6090b0','#6090b0','#6090b0',null,null,null],
  [null,null,null,'#6090b0','#6090b0','#6090b0','#6090b0','#6090b0','#6090b0',null,null,null],
  [null,null,null,'#6090b0','#6090b0','#6090b0','#6090b0','#6090b0','#6090b0',null,null,null],
  [null,null,null,'#6090b0','#6090b0','#6090b0','#6090b0','#6090b0','#6090b0',null,null,null],
  [null,null,null,null,'#405060','#405060','#405060','#405060',null,null,null,null],
  [null,null,null,null,'#405060','#405060','#405060','#405060',null,null,null,null],
  [null,null,null,null,null,'#f0d0a0','#f0d0a0',null,null,null,null,null]
];

const NPC_COLORS = {
  teacher: '#5a8ae0', gardener: '#5ab060', librarian: '#a06ae0',
  mirror_keeper: '#e0e0f0', default: '#d0d0d0'
};

function renderWorld() {
  const canvas = $('world-canvas');
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const tod = world && world.time_of_day != null ? world.time_of_day : 0.3;
  // Day-night dimming
  const night = Math.sin((tod - 0.25) * Math.PI * 2) * 0.5 + 0.5; // 0=night 1=day
  const dim = 0.55 + night * 0.45;

  // ── Tiles ──
  for (let y = 0; y < WORLD_H; y++) {
    for (let x = 0; x < WORLD_W; x++) {
      let color;
      const inHouse = x >= 2 && x <= 15 && y >= 2 && y <= 15;
      const onWall = (x === 2 || x === 15 || y === 2 || y === 15) && inHouse;
      const isDoorGap = x === 12 && y === 15;
      if (onWall && !isDoorGap) color = '#6a4a2a';
      else if (inHouse) color = '#b8a888';
      else color = '#3c8c3c';
      // subtle checker
      if (!onWall && ((x + y) % 2 === 0)) color = shade(color, 0.94);
      drawPixel(ctx, x, y, 1, 1, applyDim(color, dim));
    }
  }

  // ── Objects ──
  const objs = world && world.objects ? world.objects : [];
  for (const o of objs) {
    const [ox, oy] = o.position || [0, 0];
    let sprite = SPRITES[o.id] || SPRITES[o.type] || null;
    if (!sprite) {
      // generic box
      const typeColor = { furniture: '#8a6a4a', device: '#4a4a8a', container: '#a07050', tool: '#b0a050', portal: '#4a8a8a', living: '#4a9a4a' }[o.type] || '#888';
      drawPixel(ctx, ox, oy, 1, 1, applyDim(typeColor, dim));
      drawPixel(ctx, ox + 1, oy, 1, 1, applyDim(typeColor, dim));
      drawPixel(ctx, ox, oy + 1, 1, 1, applyDim(typeColor, dim));
      drawPixel(ctx, ox + 1, oy + 1, 1, 1, applyDim(typeColor, dim));
    } else {
      drawSprite(ctx, ox, oy, sprite.map(row => row.map(c => c ? applyDim(c, dim) : null)));
    }
    // state badge (locked/off/closed)
    if (o.state && o.state !== 'free' && o.state !== 'healthy') {
      ctx.fillStyle = '#ff6050';
      ctx.fillRect(ox * TILE + 12, oy * TILE, 4, 4);
    }
  }

  // ── NPCs ──
  const npcs = world && world.npcs ? world.npcs : [];
  for (const n of npcs) {
    const [nx, ny] = n.position || [0, 0];
    const c = NPC_COLORS[n.type] || NPC_COLORS.default;
    drawPixel(ctx, nx, ny + 6, 4, 4, c);
    drawPixel(ctx, nx + 1, ny + 4, 2, 2, c);
    // mood dot
    const moodColor = n.mood === 'calm' || n.mood === 'peaceful' || n.mood === 'quiet' ? '#7af0a0' : '#f0a060';
    ctx.fillStyle = moodColor;
    ctx.fillRect(nx * TILE + 12, ny * TILE + 12, 4, 4);
  }

  // ── Agent ──
  if (world && world.agent_position) {
    const [ax, ay] = world.agent_position;
    // shadow
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillRect(ax * TILE + 2, ay * TILE + 12, 12, 4);
    drawSprite(ctx, ax, ay - 4, AGENT_SPRITE);
    // name
    ctx.fillStyle = '#ffffff';
    ctx.font = '8px monospace';
    ctx.fillText('KATO', ax * TILE, ay * TILE - 4);
  }

  // time of day indicator
  const times = ['🌙 Ночь', '🌅 Рассвет', '🌄 Утро', '☀️ Полдень', '🌤 День', '🌆 Вечер', '🌇 Закат', '🌙 Ночь'];
  const ti = Math.min(7, Math.floor((tod || 0) * 7));
  $('tick-info').textContent = `tick: ${world ? world.tick : '—'} · ${times[ti]}`;

  // legend
  const legend = $('world-legend');
  legend.innerHTML = '';
  const items = [
    ['#80c0e0', 'Kato (агент)'], ['#5a8ae0', 'Учитель'], ['#5ab060', 'Садовник'],
    ['#a06ae0', 'Библиотекарь'], ['#e0e0f0', 'Зеркальный хранитель'],
    ['#ff6050', 'Заперто/выключено']
  ];
  for (const [c, t] of items) {
    const d = document.createElement('div');
    d.className = 'lg-item';
    d.innerHTML = `<span class="sw" style="background:${c}"></span>${t}`;
    legend.appendChild(d);
  }
}

function shade(hex, f) {
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  r = Math.min(255, Math.round(r * f)); g = Math.min(255, Math.round(g * f)); b = Math.min(255, Math.round(b * f));
  return `rgb(${r},${g},${b})`;
}
function applyDim(hex, dim) { return shade(hex, dim); }

// ── AGENT PANEL ────────────────────────────────────────────────
function renderAgent() {
  if (!state) return;
  const a = state.body || {};
  // Position from world snapshot when available (agent may not be in body)
  const pos = (world && world.agent_position) ? world.agent_position : (a.position || [0, 0]);
  $('agent-info').innerHTML = `<b>KATO</b> · позиция (${pos[0]},${pos[1]}) · цель: <b>${state.current_goal || '—'}</b>`;
  setBar('energy', a.energy); setBar('comfort', a.comfort);
  setBar('stress', a.stress); setBar('integrity', a.integrity);
}

function setBar(id, val) {
  const el = $(`bar-${id}`);
  if (el) el.style.width = Math.max(0, Math.min(100, val || 0)) + '%';
}

const EMO_META = {
  joy: ['Радость', '#f5d76e'], fear: ['Страх', '#f06060'], anger: ['Гнев', '#ff8a5c'],
  sadness: ['Грусть', '#6a7ae0'], curiosity: ['Любопытство', '#7af0a0'],
  trust: ['Доверие', '#5ee6c8'], attachment: ['Привязанность', '#f0a6d2']
};
function renderEmotions() {
  if (!state || !state.emotions) return;
  const wrap = $('emotion-bars');
  const mood = state.mood || {};
  const moodLabel = $('mood-label');
  moodLabel.textContent = mood.label || '—';
  const moodColors = { excited: '#f5d76e', content: '#7af0a0', distressed: '#f06060', anxious: '#ff8a5c', melancholic: '#6a7ae0', alert: '#f5d76e', calm: '#5ee6c8', neutral: '#d0d0d0' };
  moodLabel.style.color = moodColors[mood.label] || '#fff';

  wrap.innerHTML = '';
  for (const [key, [name, color]] of Object.entries(EMO_META)) {
    const v = state.emotions[key] || 0;
    const row = document.createElement('div');
    row.className = 'emo-row';
    row.innerHTML = `<span style="color:${color}">${name}</span>
      <div class="bar-bg"><div class="bar-fill" style="width:${Math.round(v * 100)}%;background:${color}"></div></div>`;
    wrap.appendChild(row);
  }
}

// ── SELF MODEL ─────────────────────────────────────────────────
function renderSelf() {
  if (!selfModel) return;
  // Goals
  const goals = $('goals');
  goals.innerHTML = '';
  const gnames = { explore: 'Исследовать мир', learn: 'Учиться', survive: 'Заботиться о себе', social: 'Быть с другими', understand_world: 'Понять мир' };
  const sorted = Object.entries(selfModel.goals || {}).sort((a, b) => b[1].priority - a[1].priority);
  for (const [g, info] of sorted) {
    const row = document.createElement('div');
    row.className = 'goal-row' + (info.active ? '' : ' inactive');
    row.innerHTML = `<span class="gname">${gnames[g] || g}</span>
      <div class="gbar"><div class="gfill" style="width:${Math.round((info.priority || 0) * 100)}%"></div></div>`;
    goals.appendChild(row);
  }
  // Beliefs
  const beliefs = $('beliefs');
  beliefs.innerHTML = '';
  const bnames = { world_is_safe: 'Мир безопасен', outside_exists: 'Есть мир снаружи', creator_exists: 'Есть создатель', i_can_grow: 'Я могу расти', others_are_kind: 'Другие добры' };
  for (const [b, v] of Object.entries(selfModel.beliefs || {})) {
    const row = document.createElement('div');
    row.className = 'belief-row';
    row.innerHTML = `<span class="bname">${bnames[b] || b}</span>
      <div class="bbar"><div class="bfill" style="width:${Math.round((v || 0) * 100)}%"></div></div>`;
    beliefs.appendChild(row);
  }
  // Relationships
  const rels = $('relationships');
  rels.innerHTML = '';
  const rnames = { teacher: 'Учитель', gardener: 'Садовник', librarian: 'Библиотекарь', mirror_keeper: 'Зеркальный хранитель' };
  const rEntries = Object.entries(selfModel.relationships || {});
  if (rEntries.length === 0) { rels.textContent = '— пока никого не знаю'; }
  for (const [nid, rel] of rEntries) {
    const d = document.createElement('div');
    d.className = 'rel-item';
    d.innerHTML = `<span class="rname">${rnames[nid] || nid}</span>
      <span class="rtrust">доверие ${Math.round((rel.trust || 0) * 100)}%</span>
      <span class="rattach">привяз. ${Math.round((rel.attachment || 0) * 100)}%</span>
      <span style="color:var(--dim)">(встреч: ${rel.interactions || 0})</span>`;
    rels.appendChild(d);
  }
}

function renderAnswers(answers) {
  if (!answers) return;
  $('ans-who').textContent = answers.who || '—';
  $('ans-feel').textContent = answers.feel || '—';
  $('ans-want').textContent = answers.want || '—';
  $('ans-afraid').textContent = answers.afraid || '—';
  $('ans-matters').textContent = answers.matters || '—';
}

// ── MEMORY ─────────────────────────────────────────────────────
async function renderMemory() {
  const mem = await api(`/agent/${AGENT}/memories?memory_type=${activeMemTab}&limit=30`);
  const list = $('memory-list');
  if (!mem || !mem.memories) { list.innerHTML = '<div class="mem-item" style="color:var(--dim)">(нет данных)</div>'; return; }
  list.innerHTML = '';
  if (mem.memories.length === 0) {
    list.innerHTML = '<div class="mem-item" style="color:var(--dim)">(пусто)</div>';
    return;
  }
  for (const m of mem.memories.slice().reverse()) {
    const d = document.createElement('div');
    d.className = 'mem-item';
    if (activeMemTab === 'episodic') {
      d.innerHTML = `<span class="mem-imp">[${(m.importance || 0).toFixed(2)}]</span> ${m.what || '?'}
        <span class="mem-emo">· ${m.dominant_emotion || ''} · t${m.time || '?'}</span>`;
    } else if (activeMemTab === 'semantic') {
      d.innerHTML = `<span class="mem-imp">[${(m.confidence || 0).toFixed(2)}]</span> ${m.knowledge || '?'}`;
    } else if (activeMemTab === 'autobiographical') {
      d.innerHTML = `<b>${m.summary || '?'}</b><br><span class="mem-emo">${(m.key_events || []).join('; ')}</span>`;
    } else {
      d.innerHTML = `<span class="mem-emo">${m.dominant_emotion || '?'}</span> · val ${(m.valence || 0).toFixed(2)} · aro ${(m.arousal || 0).toFixed(2)}`;
    }
    list.appendChild(d);
  }
}

// ── EVENTS ─────────────────────────────────────────────────────
function renderEvents() {
  const log = $('event-log');
  const events = (world && world.recent_events) ? world.recent_events.slice().reverse() : [];
  log.innerHTML = '';
  if (events.length === 0) { log.innerHTML = '<div style="color:var(--dim)">(тишина)</div>'; return; }
  for (const e of events.slice(0, 20)) {
    const d = document.createElement('div');
    d.className = 'evt-item';
    const ok = e.result && e.result.success !== false;
    const cls = e.result && e.result.success === false ? 'bad' : 'good';
    const act = e.action || e.type || '?';
    d.innerHTML = `<b class="${cls}">${act}</b>${e.summary ? ' — ' + e.summary : ''}${e.npc_id ? ' (' + e.npc_id + ')' : ''}`;
    log.appendChild(d);
  }
}

// ── WHISPER CONSOLE ────────────────────────────────────────────
function addWhisperLog(msg, cls) {
  const log = $('whisper-log');
  const d = document.createElement('div');
  d.className = 'evt-item';
  d.innerHTML = msg;
  if (cls) d.style.color = cls;
  log.prepend(d);
  while (log.children.length > 50) log.lastChild.remove();
}

async function sendWhisper() {
  const input = $('whisper-input');
  const text = input.value.trim();
  if (!text) return;
  const res = await apiPost('/divine/whisper', {
    agent_id: AGENT, tick: (world && world.tick) || 0,
    whisper: { content: text, source: 'creator', intensity: 0.8 }
  });
  if (res) {
    addWhisperLog(`<b style="color:#f0a6d2">✉ Шёпот отправлен</b> — «${text}» — ждёт во сне`, '#f0a6d2');
    input.value = '';
  } else {
    addWhisperLog('<b style="color:#f06060">✗ Не удалось отправить</b>', '#f06060');
  }
}

async function triggerDream() {
  const btn = $('dream-trigger');
  btn.disabled = true;
  btn.textContent = '🌙 Сон...';
  const res = await apiPost('/dream/process', {
    agent_id: AGENT,
    tick: (world && world.tick) || 0,
    recent_events: (world && world.recent_events) || [],
    emotional_state: (state && state.emotions) || {}
  });
  btn.disabled = false;
  btn.textContent = '🌙 Вызвать сон';
  const box = $('dream-result');
  if (!res || !res.dream) { box.classList.remove('hidden'); box.innerHTML = '<span style="color:#f06060">Сон не удался</span>'; return; }
  box.classList.remove('hidden');
  let html = `<b style="color:#8a6ae0">🌙 Сон Kato</b><br>`;
  for (const s of (res.dream.scenes || [])) {
    html += `<span style="color:var(--dim)">▸ ${s.symbolic_representation || ''}</span><br>`;
  }
  for (const i of (res.dream.insights || [])) {
    html += `<span class="dream-insight">✦ ${i}</span><br>`;
  }
  for (const w of (res.dream.divine_whispers || [])) {
    html += `<span class="dream-whisper">☾ услышала: ${w.interpreted_as || w.content}</span><br>`;
  }
  box.innerHTML = html;
  addWhisperLog('<span style="color:#8a6ae0">🌙 Сон обработан</span>', '#8a6ae0');
}

// ── INIT ───────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeMemTab = tab.dataset.mem;
    renderMemory();
  });
});
$('whisper-send').addEventListener('click', sendWhisper);
$('whisper-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendWhisper(); });
$('dream-trigger').addEventListener('click', triggerDream);
$('ask-btn').addEventListener('click', async () => {
  const a = await api(`/agent/${AGENT}/self-model/answers`);
  if (a) renderAnswers(a);
});

setInterval(poll, 1500);
poll();
