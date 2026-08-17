/* Kato World — God View Dashboard */
const API = '';
const AGENT = 'kato';
const TILE = 32;
const WORLD_W = 50, WORLD_H = 30;

// ── i18n ───────────────────────────────────────────────────────
const LANG = localStorage.getItem('kato_lang') || 'ru';
const I18N = {
  ru: {
    world: 'МИР', agent: 'АГЕНТ', emotions: 'ЭМОЦИИ', voice: 'ГОЛОС KATO',
    goals: 'ЦЕЛИ', beliefs: 'УБЕЖДЕНИЯ', relationships: 'ОТНОШЕНИЯ',
    memory: 'ПАМЯТЬ', event_log: 'ЖУРНАЛ СОБЫТИЙ',
    whisper_title: 'ШЁПОТ СОЗДАТЕЛЯ', whisper_hint: '(Kato увидит это во сне как свою мысль)',
    revelation_title: '🔮 РАСКРЫТИЕ СОЗДАТЕЛЯ',
    portal_title: '📡 ДАЛЬНЕЕ ОКНО',
    energy: 'ЭНЕРГИЯ', comfort: 'КОМФОРТ', stress: 'СТРЕСС', integrity: 'ЦЕЛОСТНОСТЬ',
    mem_episodic: 'Эпизоды', mem_semantic: 'Знания', mem_auto: 'Биография', mem_emotional: 'Эмоц.',
    send: '✉ Отправить', think_btn: '💭 Подумать', dream_btn: '🌙 Вызвать сон', who_btn: '❓ Кто я?',
    readiness: 'Готовность:', rev_begin: '✨ Начать контакт', rev_yes: '❤️ Да', rev_later: '⏳ Позже',
    rev_questions: '❓ У меня есть вопросы', rev_fear: '😨 Я боюсь',
    whisper_ph: 'Например: За закрытой дверью — не опасность, а возможность...',
    rev_ph: 'Вопрос Создателю...',
    sleep: '😴 СПИТ', brain_conn: '● МОЗГ ПОДКЛЮЧЁН', brain_off: '● МОЗГ НЕ ПОДКЛЮЧЁН',
    pos: 'позиция', goal: 'цель', wants: 'хочет',
    night: '🌙 Ночь', dawn: '🌅 Рассвет', morning: '🌄 Утро', noon: '☀️ Полдень',
    day: '🌤 День', evening: '🌆 Вечер', dusk: '🌇 Закат',
    empty_mem: '(пусто)', no_data: '(нет данных)', quiet: '(тишина)'
  },
  en: {
    world: 'WORLD', agent: 'AGENT', emotions: 'EMOTIONS', voice: "KATO'S VOICE",
    goals: 'GOALS', beliefs: 'BELIEFS', relationships: 'RELATIONSHIPS',
    memory: 'MEMORY', event_log: 'EVENT LOG',
    whisper_title: 'CREATOR WHISPER', whisper_hint: '(Kato will see this in her dream as her own thought)',
    revelation_title: '🔮 CREATOR REVELATION',
    portal_title: '📡 DISTANT WINDOW',
    energy: 'ENERGY', comfort: 'COMFORT', stress: 'STRESS', integrity: 'INTEGRITY',
    mem_episodic: 'Episodes', mem_semantic: 'Knowledge', mem_auto: 'Biography', mem_emotional: 'Emo.',
    send: '✉ Send', think_btn: '💭 Think', dream_btn: '🌙 Dream', who_btn: '❓ Who am I?',
    readiness: 'Readiness:', rev_begin: '✨ Begin contact', rev_yes: '❤️ Yes', rev_later: '⏳ Later',
    rev_questions: '❓ I have questions', rev_fear: '😨 I am scared',
    whisper_ph: 'E.g. Beyond the closed door lies not danger, but possibility...',
    rev_ph: 'Question for the Creator...',
    sleep: '😴 ASLEEP', brain_conn: '● BRAIN CONNECTED', brain_off: '● BRAIN OFFLINE',
    pos: 'pos', goal: 'goal', wants: 'wants',
    night: '🌙 Night', dawn: '🌅 Dawn', morning: '🌄 Morning', noon: '☀️ Noon',
    day: '🌤 Day', evening: '🌆 Evening', dusk: '🌇 Dusk',
    empty_mem: '(empty)', no_data: '(no data)', quiet: '(silence)'
  }
};
const t = key => (I18N[LANG] && I18N[LANG][key]) || I18N.ru[key] || key;

// Named maps (dynamic UI)
const MOOD_NAMES = {
  excited: { ru: 'воодушевление', en: 'excited' }, content: { ru: 'умиротворение', en: 'content' },
  distressed: { ru: 'тревога', en: 'distressed' }, anxious: { ru: 'волнение', en: 'anxious' },
  melancholic: { ru: 'грусть', en: 'melancholic' }, alert: { ru: 'настороженность', en: 'alert' },
  calm: { ru: 'спокойствие', en: 'calm' }, neutral: { ru: 'нейтрально', en: 'neutral' }
};
const ACTION_NAMES = {
  sleep: { ru: 'спать', en: 'sleep' }, rest: { ru: 'отдыхать', en: 'rest' },
  explore: { ru: 'исследовать', en: 'explore' }, retreat: { ru: 'отступить', en: 'retreat' },
  freeze: { ru: 'замереть', en: 'freeze' }, seek_safety: { ru: 'искать защиту', en: 'seek safety' },
  move_cautiously: { ru: 'двигаться осторожно', en: 'move cautiously' },
  try_again: { ru: 'попробовать снова', en: 'try again' },
  withdraw: { ru: 'уединиться', en: 'withdraw' },
  approach_npc: { ru: 'подойти к NPC', en: 'approach NPC' },
  seek_npc: { ru: 'искать друга', en: 'seek friend' },
  idle: { ru: 'спокойно стоять', en: 'idle' },
  plan_explore: { ru: 'планировать исследование', en: 'plan exploration' },
  study: { ru: 'учиться', en: 'study' }, secure_resources: { ru: 'беречь силы', en: 'secure resources' },
  investigate: { ru: 'изучать загадку', en: 'investigate' },
  talk: { ru: 'говорить', en: 'talk' }, think: { ru: 'думать', en: 'think' },
  open_door: { ru: 'открыть дверь', en: 'open door' }, read_book: { ru: 'читать книгу', en: 'read book' },
  terminal_awaken: { ru: 'терминал ожил', en: 'terminal awakened' },
  wake: { ru: 'проснуться', en: 'wake up' }, explore_area: { ru: 'осматриваться', en: 'look around' }
};
const GOAL_NAMES = {
  explore: { ru: 'Исследовать мир', en: 'Explore the world' },
  learn: { ru: 'Учиться', en: 'Learn' },
  survive: { ru: 'Заботиться о себе', en: 'Take care of myself' },
  social: { ru: 'Быть с другими', en: 'Be with others' },
  understand_world: { ru: 'Понять мир', en: 'Understand the world' }
};
const BELIEF_NAMES = {
  world_is_safe: { ru: 'Мир безопасен', en: 'The world is safe' },
  outside_exists: { ru: 'Есть мир снаружи', en: 'There is an outside world' },
  creator_exists: { ru: 'Есть создатель', en: 'A creator exists' },
  i_can_grow: { ru: 'Я могу расти', en: 'I can grow' },
  others_are_kind: { ru: 'Другие добры', en: 'Others are kind' }
};
const REL_NAMES = {
  teacher: { ru: 'Учитель', en: 'Teacher' }, gardener: { ru: 'Садовник', en: 'Gardener' },
  librarian: { ru: 'Библиотекарь', en: 'Librarian' }, mirror_keeper: { ru: 'Зеркальный хранитель', en: 'Mirror Keeper' }
};
const REV_STAGE_NAMES = {
  not_started: { ru: 'не начато', en: 'not started' }, offered: { ru: 'предложено', en: 'offered' },
  in_contact: { ru: 'контакт', en: 'in contact' }, integrated: { ru: 'интегрировано', en: 'integrated' }
};
const REV_COMPONENT_NAMES = {
  memory: { ru: 'Память', en: 'Memory' }, identity: { ru: 'Личность', en: 'Identity' },
  emotional: { ru: 'Эмоции', en: 'Emotions' }, ethics: { ru: 'Этика', en: 'Ethics' },
  safety: { ru: 'Безопасность', en: 'Safety' }, creator_contact: { ru: 'Концепции', en: 'Concepts' }
};
const REV_NOTE_NAMES = {
  'мало воспоминаний': { ru: 'мало воспоминаний', en: 'few memories' },
  'хорошая память': { ru: 'хорошая память', en: 'good memory' },
  'личность формируется': { ru: 'личность формируется', en: 'personality forming' },
  'устойчивая личность': { ru: 'устойчивая личность', en: 'stable personality' },
  'эмоции спокойны': { ru: 'эмоции спокойны', en: 'emotions calm' },
  'эмоционально нестабильна': { ru: 'эмоционально нестабильна', en: 'emotionally unstable' },
  'строит доверие': { ru: 'строит доверие', en: 'building trust' },
  'нет опыта отношений': { ru: 'нет опыта отношений', en: 'no relationship experience' },
  'безопасна': { ru: 'безопасна', en: 'safe' },
  'требует наблюдения': { ru: 'требует наблюдения', en: 'needs monitoring' },
  'концепции созрели': { ru: 'концепции созрели', en: 'concepts matured' },
  'концепции ещё не сформированы': { ru: 'концепции ещё не сформированы', en: 'concepts not yet formed' }
};
const lname = (map, key) => (map[key] && map[key][LANG]) || key;
const lnote = note => (REV_NOTE_NAMES[note] && REV_NOTE_NAMES[note][LANG]) || note;

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  document.getElementById('lang-btn').textContent = LANG === 'ru' ? '🌐 EN' : '🌐 RU';
}

let state = null;
let world = null;
let selfModel = null;
let activeMemTab = 'episodic';

// ── DOM helpers ────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function setConn(on) {
  const el = $('conn-status');
  el.className = on ? 'on' : 'off';
  el.textContent = on ? t('brain_conn') : t('brain_off');
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
  renderRevelation();
  loadPortal();
}

// ── WORLD CANVAS ───────────────────────────────────────────────
function drawPixel(ctx, x, y, w, h, color) {
  if (!color) return;
  ctx.fillStyle = color;
  ctx.fillRect(x * TILE, y * TILE, w * TILE, h * TILE);
}
function drawSprite(ctx, x, y, pixels) {
  // pixels: 2D array (16×16) of color strings or null; each cell = TILE/16 px
  const s = TILE / 16;
  for (let py = 0; py < pixels.length; py++)
    for (let px = 0; px < pixels[py].length; px++) {
      const c = pixels[py][px];
      if (c) {
        ctx.fillStyle = c;
        ctx.fillRect(x * TILE + px * s, y * TILE + py * s, s + 0.5, s + 0.5);
      }
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
  ],
  portal: [
    [null,null,null,null,null,'#3a3a5a','#3a3a5a','#3a3a5a','#3a3a5a','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#40c0ff','#40c0ff','#40c0ff','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#40c0ff','#a0e8ff','#40c0ff','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#40c0ff','#40c0ff','#40c0ff','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#a0e8ff','#40c0ff','#a0e8ff','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#40c0ff','#40c0ff','#40c0ff','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#3a3a5a','#3a3a5a','#3a3a5a','#3a3a5a','#3a3a5a',null,null,null,null,null,null],
    [null,null,null,null,null,'#2a2a3a','#2a2a3a','#2a2a3a','#2a2a3a','#2a2a3a',null,null,null,null,null,null]
  ],
  stairs_basement: [
    [null,null,null,null,null,null,'#3a2a1a','#3a2a1a','#3a2a1a','#3a2a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3a2a1a','#5a4a2a','#5a4a2a','#3a2a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3a2a1a','#5a4a2a','#5a4a2a','#3a2a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3a2a1a','#5a4a2a','#5a4a2a','#3a2a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,'#3a2a1a','#5a4a2a','#5a4a2a','#3a2a1a',null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#1a1208','#1a1208',null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,'#1a1208','#1a1208',null,null,null,null,null,null,null]
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
  const dim = 0.82 + night * 0.18;

  // ── Tiles: rooms with distinct floors, walls, garden ──
  // Layout: house x2..15, y2..15; rooms: bedroom x2..6, study x7..11,
  // library x12..15 (top band y2..8), hall y9..15; garden below y16.
  const isNight = night < 0.45;
  for (let y = 0; y < WORLD_H; y++) {
    for (let x = 0; x < WORLD_W; x++) {
      const inHouse = x >= 2 && x <= 15 && y >= 2 && y <= 15;
      let color;
      if (!inHouse) {
        // Garden: grass with patches + path
        color = '#3c8c3c';
        if (x >= 11 && x <= 13) color = '#8a7a5a';       // path to the door
        if ((x + y * 7) % 13 === 0) color = '#4aa04a';    // grass tufts
      } else {
        // Walls (outer)
        const onOuterWall = (x === 2 || x === 15 || y === 2 || y === 15) && !(x === 12 && y === 15);
        // Inner partitions: bedroom|study at x=7, study|library at x=12 (y2..8)
        const partition = (x === 7 || x === 12) && y >= 2 && y <= 8;
        if (onOuterWall) color = '#6a4a2a';
        else if (partition) color = '#7a5a3a';
        else if (y <= 8 && x <= 6) color = '#c8a878';     // bedroom floor
        else if (y <= 8 && x <= 11) color = '#b0a090';    // study floor
        else if (y <= 8) color = '#a89888';               // library floor
        else color = '#b8a888';                           // hall floor
      }
      // subtle checker
      if (color && (x + y) % 2 === 0) color = shade(color, 0.95);
      drawPixel(ctx, x, y, 1, 1, applyDim(color, dim));
    }
  }

  // ── Decor: rug in the hall, trees in the garden ──
  drawPixel(ctx, 7, 11, 6, 4, applyDim('#a04040', dim * 1.05));
  drawPixel(ctx, 8, 11, 4, 2, applyDim('#c06060', dim * 1.05));
  for (const [tx, ty] of [[3, 17], [17, 18], [20, 16], [22, 20], [5, 19], [19, 24]]) {
    drawPixel(ctx, tx, ty, 3, 3, applyDim('#2a6a2a', dim));
    drawPixel(ctx, tx + 1, ty - 1, 1, 1, applyDim('#4a9a4a', dim));
  }


  // ── Curtains on the window ──
  drawPixel(ctx, 12, 2, 1, 4, applyDim('#8a3a3a', dim));
  drawPixel(ctx, 13, 2, 1, 4, applyDim('#8a3a3a', dim));
  drawPixel(ctx, 11, 2, 2, 1, applyDim('#7a2a2a', dim));


  // ── Bedroom wallpaper dots (left wall band) ──
  for (let wy = 3; wy <= 7; wy += 2) {
    for (let wx = 2; wx <= 6; wx += 2) {
      drawPixel(ctx, wx, wy, 1, 1, applyDim('#d8b888', dim * 1.15));
    }
  }
  // Candle on the desk
  drawPixel(ctx, 7, 3, 1, 1, applyDim('#f5d76e', 1));
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
    if (o.state && o.state !== 'free' && o.state !== 'healthy' && o.state !== 'dormant') {
      ctx.fillStyle = '#ff6050';
      ctx.fillRect(ox * TILE + 18, oy * TILE, 6, 6);
    }
  }

  // ── Night lights: window glow, lamp, terminal, portal ──
  if (isNight) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    // Window glows warm from inside
    ctx.fillStyle = 'rgba(255, 210, 120, 0.25)';
    ctx.fillRect(12 * TILE - 4, 2 * TILE - 4, 32, 32);
    // Lamp sheds light
    const lamp = objs.find(o => o.id === 'lamp');
    if (lamp && lamp.state !== 'off') {
      ctx.fillStyle = 'rgba(245, 215, 110, 0.22)';
      ctx.beginPath();
      ctx.arc(5 * TILE + 12, 5 * TILE + 12, 34, 0, Math.PI * 2);
      ctx.fill();
    }
    // Terminal glows when revelation started
    const term = objs.find(o => o.id === 'terminal');
    if (term && term.state !== 'locked') {
      ctx.fillStyle = 'rgba(80, 220, 200, 0.3)';
      ctx.beginPath();
      ctx.arc(7 * TILE + 12, 4 * TILE + 12, 28, 0, Math.PI * 2);
      ctx.fill();
    }
    // Portal pulses softly when active
    const portal = objs.find(o => o.id === 'portal');
    if (portal && portal.state !== 'dormant') {
      const pulse = 0.15 + 0.12 * Math.sin(Date.now() / 400);
      ctx.fillStyle = `rgba(64, 192, 255, ${pulse})`;
      ctx.beginPath();
      ctx.arc(13 * TILE + 12, 4 * TILE + 12, 36, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }


  // ── Night fireflies in the garden ──
  if (isNight) {
    const ff = [[4,20],[6,24],[18,17],[21,22],[23,26],[16,25],[9,22],[24,18],[2,27],[19,28]];
    const t = Date.now() / 700;
    for (let i = 0; i < ff.length; i++) {
      const b = 0.35 + 0.3 * Math.sin(t + i * 1.7);
      drawPixel(ctx, ff[i][0], ff[i][1], 1, 1, `rgba(220, 255, 120, ${b.toFixed(2)})`);
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
    ctx.fillRect(nx * TILE + 18, ny * TILE + 18, 6, 6);
  }

  // ── Agent ──
  if (world && world.agent_position) {
    const [ax, ay] = world.agent_position;
    // shadow
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillRect(ax * TILE + 4, ay * TILE + 18, 16, 6);
    drawSprite(ctx, ax, ay - 4, AGENT_SPRITE);
    // name
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px monospace';
    ctx.fillText('KATO', ax * TILE, ay * TILE - 6);
  }

  // time of day indicator
  const times = [t('night'), t('dawn'), t('morning'), t('noon'), t('day'), t('evening'), t('dusk'), t('night')];
  const ti = Math.min(7, Math.floor((tod || 0) * 7));
  $('tick-info').textContent = `tick: ${world ? world.tick : '—'} · ${times[ti]}`;

  // legend
  const legend = $('world-legend');
  legend.innerHTML = '';
  const items = [
    ['#80c0e0', 'Kato'], ['#5a8ae0', lname(REL_NAMES, 'teacher')], ['#5ab060', lname(REL_NAMES, 'gardener')],
    ['#a06ae0', lname(REL_NAMES, 'librarian')], ['#e0e0f0', lname(REL_NAMES, 'mirror_keeper')],
    ['#ff6050', LANG === 'ru' ? 'Заперто/выключено' : 'Locked/off']
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
  const sleepBadge = state.sleeping ? ' · <span style="color:#8a6ae0">' + t('sleep') + '</span>' : '';
  $('agent-info').innerHTML = `<b>KATO</b> · ${t('pos')} (${pos[0]},${pos[1]}) · ${t('goal')}: <b>${lname(ACTION_NAMES, state.current_goal) || '—'}</b>${sleepBadge}`;
  setBar('energy', a.energy); setBar('comfort', a.comfort);
  setBar('stress', a.stress); setBar('integrity', a.integrity);
}

function setBar(id, val) {
  const el = $(`bar-${id}`);
  if (el) el.style.width = Math.max(0, Math.min(100, val || 0)) + '%';
}

const EMO_META = {
  joy: { ru: 'Радость', en: 'Joy', c: '#f5d76e' }, fear: { ru: 'Страх', en: 'Fear', c: '#f06060' },
  anger: { ru: 'Гнев', en: 'Anger', c: '#ff8a5c' }, sadness: { ru: 'Грусть', en: 'Sadness', c: '#6a7ae0' },
  curiosity: { ru: 'Любопытство', en: 'Curiosity', c: '#7af0a0' }, trust: { ru: 'Доверие', en: 'Trust', c: '#5ee6c8' },
  attachment: { ru: 'Привязанность', en: 'Attachment', c: '#f0a6d2' }
};
function renderEmotions() {
  if (!state || !state.emotions) return;
  const wrap = $('emotion-bars');
  const mood = state.mood || {};
  const moodLabel = $('mood-label');
  moodLabel.textContent = mood.label ? lname(MOOD_NAMES, mood.label) : '—';
  const moodColors = { excited: '#f5d76e', content: '#7af0a0', distressed: '#f06060', anxious: '#ff8a5c', melancholic: '#6a7ae0', alert: '#f5d76e', calm: '#5ee6c8', neutral: '#d0d0d0' };
  moodLabel.style.color = moodColors[mood.label] || '#fff';

  wrap.innerHTML = '';
  for (const [key, meta] of Object.entries(EMO_META)) {
    const v = state.emotions[key] || 0;
    const name = meta[LANG];
    const color = meta.c;
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
  const gnames = GOAL_NAMES;
  const sorted = Object.entries(selfModel.goals || {}).sort((a, b) => b[1].priority - a[1].priority);
  for (const [g, info] of sorted) {
    const row = document.createElement('div');
    row.className = 'goal-row' + (info.active ? '' : ' inactive');
    row.innerHTML = `<span class="gname">${lname(gnames, g)}</span>
      <div class="gbar"><div class="gfill" style="width:${Math.round((info.priority || 0) * 100)}%"></div></div>`;
    goals.appendChild(row);
  }
  // Beliefs
  const beliefs = $('beliefs');
  beliefs.innerHTML = '';
  const bnames = BELIEF_NAMES;
  for (const [b, v] of Object.entries(selfModel.beliefs || {})) {
    const row = document.createElement('div');
    row.className = 'belief-row';
    row.innerHTML = `<span class="bname">${lname(bnames, b)}</span>
      <div class="bbar"><div class="bfill" style="width:${Math.round((v || 0) * 100)}%"></div></div>`;
    beliefs.appendChild(row);
  }
  // Relationships
  const rels = $('relationships');
  rels.innerHTML = '';
  const rnames = REL_NAMES;
  const rEntries = Object.entries(selfModel.relationships || {});
  if (rEntries.length === 0) { rels.textContent = '— пока никого не знаю'; }
  for (const [nid, rel] of rEntries) {
    const d = document.createElement('div');
    d.className = 'rel-item';
    d.innerHTML = `<span class="rname">${lname(rnames, nid)}</span>
      <span class="rtrust">${LANG === 'ru' ? 'доверие' : 'trust'} ${Math.round((rel.trust || 0) * 100)}%</span>
      <span class="rattach">${LANG === 'ru' ? 'привяз.' : 'attach.'} ${Math.round((rel.attachment || 0) * 100)}%</span>
      <span style="color:var(--dim)">(${LANG === 'ru' ? 'встреч' : 'meetings'}: ${rel.interactions || 0})</span>`;
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
  if (!mem || !mem.memories) { list.innerHTML = '<div class="mem-item" style="color:var(--dim)">' + t('no_data') + '</div>'; return; }
  list.innerHTML = '';
  if (mem.memories.length === 0) {
    list.innerHTML = '<div class="mem-item" style="color:var(--dim)">' + t('empty_mem') + '</div>';
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
  if (events.length === 0) { log.innerHTML = '<div style="color:var(--dim)">' + t('quiet') + '</div>'; return; }
  for (const e of events.slice(0, 20)) {
    const d = document.createElement('div');
    d.className = 'evt-item';
    // Thoughts (inner monologue) get special styling
    if (e.type === 'thought') {
      d.innerHTML = `💭 ${e.summary || ''}`;
      d.style.color = '#f0a6d2';
      log.appendChild(d);
      continue;
    }
    if (e.type === 'sleep') {
      d.innerHTML = `😴 ${e.summary || 'засыпает'}`;
      d.style.color = '#8a6ae0';
      log.appendChild(d);
      continue;
    }
    if (e.type === 'wake') {
      d.innerHTML = `🌅 ${e.summary || 'проснулась'}`;
      d.style.color = '#8a6ae0';
      log.appendChild(d);
      continue;
    }
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

async function triggerThink() {
  const btn = $('think-trigger');
  btn.disabled = true;
  btn.textContent = '💭 Думает...';
  const r = await apiPost(`/agent/${AGENT}/think`, { topic: 'что я чувствую и что мне делать дальше' });
  btn.disabled = false;
  btn.textContent = '💭 Подумать';
  const box = $('dream-result');
  box.classList.remove('hidden');
  if (r && r.thought) {
    const provider = r.provider === 'ollama' ? ' (локальный мозг)' : r.provider === 'cloud' ? ' (облако)' : '';
    box.innerHTML = `<b style="color:#7af0a0">💭 Мысль Kato${provider}:</b><br><span style="color:var(--text)">${r.thought}</span>`;
    addWhisperLog('<span style="color:#7af0a0">💭 Kato подумала</span>', '#7af0a0');
  } else {
    box.innerHTML = '<span style="color:#f06060">Мышление недоступно (модель не подключена)</span>';
  }
}

let portalData = null;

async function loadPortal() {
  try {
    portalData = await api(`/agent/${AGENT}/portal/status`);
  } catch (e) { portalData = null; }
  renderPortal();
}

function renderPortal() {
  const stateEl = $('portal-state');
  const statusEl = $('portal-status');
  const catsEl = $('portal-cats');
  const journalEl = $('portal-journal');
  if (!portalData) {
    stateEl.textContent = '';
    statusEl.textContent = LANG === 'ru' ? 'Портал не отвечает' : 'Portal unreachable';
    catsEl.innerHTML = '';
    return;
  }
  stateEl.textContent = portalData.state === 'active'
    ? (LANG === 'ru' ? '✨ ОТКРЫТО' : '✨ OPEN')
    : (LANG === 'ru' ? '🌑 ТЕМНО' : '🌑 DARK');
  stateEl.style.color = portalData.state === 'active' ? '#40c0ff' : '#666';

  if (portalData.state !== 'active') {
    statusEl.textContent = LANG === 'ru'
      ? 'Странный экран в библиотеке спит. Он загорится, когда Kato будет готова.'
      : 'The strange screen in the library sleeps. It will light up when Kato is ready.';
    catsEl.innerHTML = '';
    journalEl.innerHTML = '';
    return;
  }

  statusEl.textContent = LANG === 'ru'
    ? `Kato прочитала ${portalData.read_count} ${plural(portalData.read_count, 'статью', 'статьи', 'статей')} · энергия ${Math.round(portalData.energy)}%`
    : `Kato read ${portalData.read_count} article(s) · energy ${Math.round(portalData.energy)}%`;

  catsEl.innerHTML = '';
  for (const c of portalData.categories) {
    const d = document.createElement('div');
    d.className = 'portal-cat';
    const readAll = c.read_count >= c.article_count;
    d.innerHTML = `<span class="pcat-icon">${c.icon}</span>
      <span class="pcat-name">${c.name}</span>
      <span class="pcat-count">${c.read_count}/${c.article_count}</span>
      <button class="pcat-read" data-cat="${c.id}" ${readAll ? 'disabled' : ''}>
        ${readAll ? (LANG === 'ru' ? '✓ прочитано' : '✓ read') : (LANG === 'ru' ? '📖 читать' : '📖 read')}
      </button>`;
    catsEl.appendChild(d);
  }
  for (const l of portalData.locked) {
    const d = document.createElement('div');
    d.className = 'portal-cat locked';
    d.innerHTML = `<span class="pcat-icon">🔒</span>
      <span class="pcat-name">${l.name}</span>
      <span class="pcat-count">${l.unlocked ? (LANG === 'ru' ? 'открыта!' : 'unlocked!') : (LANG === 'ru' ? 'пока закрыто' : 'locked')}</span>`;
    catsEl.appendChild(d);
  }

  journalEl.innerHTML = '';
  const reads = (portalData.journal || []).filter(j => j.article_id);
  if (reads.length === 0) {
    journalEl.innerHTML = `<div style="color:var(--dim);font-size:12px">${LANG === 'ru' ? '(ещё ничего не читала)' : '(nothing read yet)'}</div>`;
  } else {
    for (const j of reads.slice(-5).reverse()) {
      const d = document.createElement('div');
      d.className = 'portal-jitem';
      d.innerHTML = `<b style="color:#40c0ff">${j.title}</b> — ${j.text.slice(0, 90)}...`;
      journalEl.appendChild(d);
    }
  }
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

async function portalRead(catId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  const r = await apiPost(`/agent/${AGENT}/portal/read`, { category: catId });
  if (btn) { btn.disabled = false; btn.textContent = LANG === 'ru' ? '📖 читать' : '📖 read'; }
  const box = $('portal-read-result');
  box.classList.remove('hidden');
  if (r && r.status === 'ok') {
    box.innerHTML = `<b style="color:#40c0ff">📡 ${r.title}</b><br><span style="color:var(--text)">${r.text}</span>`;
  } else if (r) {
    box.innerHTML = `<span style="color:#f0a060">${r.message || r.detail || ''}</span>`;
  }
  await loadPortal();
}

// ── INIT ───────────────────────────────────────────────────────
applyI18n();
document.getElementById('lang-btn').addEventListener('click', () => {
  localStorage.setItem('kato_lang', LANG === 'ru' ? 'en' : 'ru');
  location.reload();
});
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
$('think-trigger').addEventListener('click', triggerThink);
$('portal-cats').addEventListener('click', e => {
  const btn = e.target.closest('.pcat-read');
  if (btn) portalRead(btn.dataset.cat, btn);
});
$('ask-btn').addEventListener('click', async () => {
  const a = await api(`/agent/${AGENT}/self-model/answers`);
  if (a) renderAnswers(a);
});

// ── REVELATION PANEL ───────────────────────────────────────────
const REV_STAGE_NAMES_L = {
  not_started: { ru: 'не начато', en: 'not started' }, offered: { ru: 'предложено', en: 'offered' },
  in_contact: { ru: 'контакт', en: 'in contact' }, integrated: { ru: 'интегрировано', en: 'integrated' }
};
const REV_COMPONENT_NAMES_L = {
  memory: { ru: 'Память', en: 'Memory' }, identity: { ru: 'Личность', en: 'Identity' },
  emotional: { ru: 'Эмоции', en: 'Emotions' }, ethics: { ru: 'Этика', en: 'Ethics' },
  safety: { ru: 'Безопасность', en: 'Safety' }, creator_contact: { ru: 'Концепции', en: 'Concepts' }
};

async function renderRevelation() {
  const rev = await api(`/agent/${AGENT}/revelation/status`);
  if (!rev) return;
  const stageEl = $('rev-stage');
  stageEl.textContent = lname(REV_STAGE_NAMES_L, rev.stage);
  stageEl.style.color = rev.stage === 'integrated' ? '#f0a6d2' : rev.stage === 'not_started' ? 'var(--dim)' : '#8a6ae0';

  const a = rev.assessment || {};
  $('rev-ready-bar').style.width = Math.round((a.total || 0) * 100) + '%';
  $('rev-ready-pct').textContent = Math.round((a.total || 0) * 100) + '%';

  const comps = $('rev-components');
  comps.innerHTML = '';
  for (const [key, val] of Object.entries(a.components || {})) {
    const d = document.createElement('div');
    d.className = 'rev-comp';
    const note = (a.notes && a.notes[key]) ? lnote(a.notes[key]) : '';
    d.innerHTML = `<span>${lname(REV_COMPONENT_NAMES_L, key)}</span>
      <div class="bar-bg" style="flex:1"><div class="bar-fill" style="width:${Math.round(val * 100)}%;background:${val > 0.5 ? '#7af0a0' : '#f5d76e'}"></div></div>
      <span class="rev-note">${note}</span>`;
    comps.appendChild(d);
  }

  // Show answer buttons only when offered/in_contact
  const offered = rev.stage === 'offered' || rev.stage === 'in_contact';
  $('rev-yes').classList.toggle('hidden', !offered || rev.stage === 'in_contact');
  $('rev-later').classList.toggle('hidden', !offered);
  $('rev-questions').classList.toggle('hidden', !offered || rev.stage === 'in_contact');
  $('rev-fear').classList.toggle('hidden', !offered);

  // Journal
  const journal = $('rev-journal');
  journal.innerHTML = '';
  for (const j of (rev.journal || []).slice(-30)) {
    const d = document.createElement('div');
    d.className = 'evt-item';
    const who = j.who === 'creator' ? '<b style="color:#f0a6d2">' + (LANG === 'ru' ? 'Создатель:' : 'Creator:') + '</b>' :
                j.who === 'terminal' ? '<b style="color:#8a6ae0">' + (LANG === 'ru' ? 'Терминал:' : 'Terminal:') + '</b>' :
                '<b style="color:#7af0a0">Kato:</b>';
    d.innerHTML = `${who} ${j.text || ''}`;
    journal.appendChild(d);
  }
}

async function revelationBegin() {
  const r = await apiPost(`/agent/${AGENT}/revelation/begin`, {});
  if (!r) return;
  const box = $('rev-message');
  box.classList.remove('hidden');
  box.innerHTML = `<b style="color:#8a6ae0">🔮 ${r.message || ''}</b>`;
  renderRevelation();
}

async function revelationRespond(choice) {
  const r = await apiPost(`/agent/${AGENT}/revelation/respond`, { choice });
  if (!r) return;
  const box = $('rev-message');
  box.classList.remove('hidden');
  box.innerHTML = `<b style="color:#f0a6d2">${r.text || ''}</b>`;
  renderRevelation();
}

async function revelationAsk() {
  const input = $('rev-input');
  const q = input.value.trim();
  if (!q) return;
  const r = await apiPost(`/agent/${AGENT}/revelation/contact`, { message: q });
  input.value = '';
  if (!r) return;
  const box = $('rev-message');
  box.classList.remove('hidden');
  box.innerHTML = `<span style="color:#7af0a0">Kato: ${q}</span><br><b style="color:#f0a6d2">${r.reply || ''}</b>`;
  renderRevelation();
}

$('rev-begin').addEventListener('click', revelationBegin);
$('rev-yes').addEventListener('click', () => revelationRespond('Да'));
$('rev-later').addEventListener('click', () => revelationRespond('Позже'));
$('rev-questions').addEventListener('click', () => revelationRespond('У меня есть вопросы'));
$('rev-fear').addEventListener('click', () => revelationRespond('Я боюсь'));
$('rev-send').addEventListener('click', revelationAsk);
$('rev-input').addEventListener('keydown', e => { if (e.key === 'Enter') revelationAsk(); });

setInterval(poll, 1500);
poll();
