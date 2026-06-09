/**
 * ポモドーロタイマー クライアントサイド
 *
 * - setInterval でカウントダウン（サーバーと定期同期）
 * - SVG stroke-dashoffset でリングアニメーション
 * - Notification API でブラウザ通知
 * - Web Audio API (AudioContext) でサウンド通知（外部ファイル不要）
 */

'use strict';

// ============================================================
// 定数
// ============================================================
const RING_RADIUS = 96;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS; // ≈ 603.2
const WORK_RING_COLOR_BLUE = [59, 130, 246];
const WORK_RING_COLOR_YELLOW = [250, 204, 21];
const WORK_RING_COLOR_RED = [239, 68, 68];

// ============================================================
// DOM 参照
// ============================================================
const statusLabel    = document.getElementById('statusLabel');
const timeDisplay    = document.getElementById('timeDisplay');
const ringProgress   = document.getElementById('ringProgress');
const timerCard      = document.getElementById('timerCard');
const startPauseBtn  = document.getElementById('startPauseBtn');
const resetBtn       = document.getElementById('resetBtn');
const completedCount = document.getElementById('completedCount');
const focusLabel     = document.getElementById('focusLabel');
const levelValue     = document.getElementById('levelValue');
const xpValue        = document.getElementById('xpValue');
const streakValue    = document.getElementById('streakValue');
const badgeList      = document.getElementById('badgeList');
const weeklyRate     = document.getElementById('weeklyRate');
const weeklyRateFill = document.getElementById('weeklyRateFill');
const weeklyAvg      = document.getElementById('weeklyAvg');
const monthlyRate    = document.getElementById('monthlyRate');
const monthlyRateFill = document.getElementById('monthlyRateFill');
const monthlyAvg     = document.getElementById('monthlyAvg');
const workDurationSelect = document.getElementById('workDurationSelect');
const breakDurationSelect = document.getElementById('breakDurationSelect');
const themeSelect = document.getElementById('themeSelect');
const soundStartToggle = document.getElementById('soundStartToggle');
const soundEndToggle = document.getElementById('soundEndToggle');
const soundTickToggle = document.getElementById('soundTickToggle');

// ============================================================
// 状態
// ============================================================
let timerState = {
  mode: 'work',
  state: 'idle',
  remaining_seconds: 1500,
  total_duration: 1500,
};

let intervalId = null;
let sessionStartTime = null; // セッション開始時刻（経過時間計算用）
let isCompletingSession = false; // handleSessionComplete の再入防止フラグ
const SETTINGS_STORAGE_KEY = 'pomodoro.preferences.v1';
let userSettings = {
  work_duration_minutes: 25,
  break_duration_minutes: 5,
  theme: 'light',
  sounds: {
    start: true,
    end: true,
    tick: false,
  },
};

// ============================================================
// リング初期化
// ============================================================
ringProgress.style.strokeDasharray = RING_CIRCUMFERENCE;
ringProgress.style.strokeDashoffset = 0;

// ============================================================
// UI 更新
// ============================================================
function interpolateColor(from, to, t) {
  return from.map((value, i) => Math.round(value + (to[i] - value) * t));
}

function getWorkRingColor(progress) {
  const clamped = Math.max(0, Math.min(1, progress));

  const rgb = clamped <= 0.5
    ? interpolateColor(WORK_RING_COLOR_BLUE, WORK_RING_COLOR_YELLOW, clamped * 2)
    : interpolateColor(WORK_RING_COLOR_YELLOW, WORK_RING_COLOR_RED, (clamped - 0.5) * 2);

  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function updateRingVisuals(remainingSeconds, totalDuration, mode) {
  const ratio = totalDuration > 0 ? remainingSeconds / totalDuration : 0;
  const progress = 1 - ratio;
  ringProgress.style.strokeDashoffset = RING_CIRCUMFERENCE * progress;
  ringProgress.style.stroke = mode === 'work' ? getWorkRingColor(progress) : '#56C8A0';
}

function updateUI(data) {
  timerState = data;

  // 残り時間表示
  const m = Math.floor(data.remaining_seconds / 60);
  const s = data.remaining_seconds % 60;
  timeDisplay.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

  // ステータスラベル
  statusLabel.textContent = data.mode === 'work' ? '作業中' : '休憩中';

  updateRingVisuals(data.remaining_seconds, data.total_duration, data.mode);
  timerCard.classList.toggle('focus-mode', data.mode === 'work' && data.state === 'running');

  // ボタンラベル
  if (data.state === 'running') {
    startPauseBtn.textContent = '一時停止';
  } else {
    startPauseBtn.textContent = data.state === 'paused' ? '再開' : '開始';
  }
}

function updateStats(data) {
  completedCount.textContent = data.completed ?? 0;
  focusLabel.textContent     = data.focus_label ?? '0分';
  const gamification = data.gamification ?? {};
  levelValue.textContent = `Lv.${gamification.level ?? 1}`;
  xpValue.textContent = `${gamification.xp ?? 0} XP`;
  streakValue.textContent = `${gamification.streak_days ?? 0}日`;

  const badges = gamification.badges ?? [];
  badgeList.innerHTML = badges.map((badge) => {
    const earnedClass = badge.earned ? ' badge-earned' : '';
    return `<div class="badge-item${earnedClass}">${badge.name} (${badge.progress}/${badge.target})</div>`;
  }).join('');

  const weekly = gamification.weekly ?? {};
  const monthly = gamification.monthly ?? {};
  const weeklyCompletionRate = weekly.completion_rate ?? 0;
  const monthlyCompletionRate = monthly.completion_rate ?? 0;
  weeklyRate.textContent = `${Number(weeklyCompletionRate).toFixed(1)}%`;
  weeklyRateFill.style.width = `${weeklyCompletionRate}%`;
  monthlyRate.textContent = `${Number(monthlyCompletionRate).toFixed(1)}%`;
  monthlyRateFill.style.width = `${monthlyCompletionRate}%`;
  weeklyAvg.textContent = `${Math.floor((weekly.average_focus_seconds ?? 0) / 60)}分`;
  monthlyAvg.textContent = `${Math.floor((monthly.average_focus_seconds ?? 0) / 60)}分`;
}

// ============================================================
// API 呼び出し
// ============================================================
async function apiPost(path, body = null) {
  const opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

async function fetchState() {
  const res = await fetch('/api/state');
  const data = await res.json();
  updateUI(data);
}

async function fetchStats() {
  const res = await fetch('/api/stats');
  const data = await res.json();
  updateStats(data);
}

// ============================================================
// 設定
// ============================================================
function clampWorkDuration(value) {
  const allowed = [15, 25, 35, 45];
  return allowed.includes(value) ? value : 25;
}

function clampBreakDuration(value) {
  const allowed = [5, 10, 15];
  return allowed.includes(value) ? value : 5;
}

function loadSettings() {
  try {
    const parsed = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}');
    userSettings = {
      work_duration_minutes: clampWorkDuration(Number(parsed.work_duration_minutes) || 25),
      break_duration_minutes: clampBreakDuration(Number(parsed.break_duration_minutes) || 5),
      theme: ['light', 'dark', 'focus'].includes(parsed.theme) ? parsed.theme : 'light',
      sounds: {
        start: parsed.sounds?.start !== false,
        end: parsed.sounds?.end !== false,
        tick: parsed.sounds?.tick === true,
      },
    };
  } catch (err) {
    // 破損時はデフォルト値を使用
    console.warn('保存済み設定の読み込みに失敗しました:', err);
  }
}

function saveSettings() {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(userSettings));
}

function applyTheme(theme) {
  document.body.classList.remove('theme-light', 'theme-dark', 'theme-focus');
  document.body.classList.add(`theme-${theme}`);
}

function syncSettingsControls() {
  workDurationSelect.value = String(userSettings.work_duration_minutes);
  breakDurationSelect.value = String(userSettings.break_duration_minutes);
  themeSelect.value = userSettings.theme;
  soundStartToggle.checked = userSettings.sounds.start;
  soundEndToggle.checked = userSettings.sounds.end;
  soundTickToggle.checked = userSettings.sounds.tick;
}

async function syncTimerSettings() {
  try {
    const res = await apiPost('/api/settings', {
      work_duration_minutes: userSettings.work_duration_minutes,
      break_duration_minutes: userSettings.break_duration_minutes,
    });
    if (!res?.timer) throw new Error('settings sync failed');
    updateUI(res.timer);
  } catch (err) {
    console.error('設定の同期に失敗しました:', err);
    await fetchState();
  }
}

// ============================================================
// サウンド通知（Web Audio API — 外部ファイル不要）
// ============================================================
function playTones(tones) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    tones.forEach(({ freq, start, dur, gain = 0.4 }) => {
      const osc  = ctx.createOscillator();
      const gainNode = ctx.createGain();
      osc.connect(gainNode);
      gainNode.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      gainNode.gain.setValueAtTime(gain, ctx.currentTime + start);
      gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
      osc.start(ctx.currentTime + start);
      osc.stop(ctx.currentTime + start + dur + 0.05);
    });
  } catch (err) {
    // Web Audio 非対応環境や再生失敗時は警告のみ出して継続する
    console.warn('サウンド再生に失敗しました:', err);
  }
}

function playStartSound() {
  if (!userSettings.sounds.start) return;
  playTones([{ freq: 740, start: 0, dur: 0.12 }]);
}

function playEndSound() {
  if (!userSettings.sounds.end) return;
  playTones([
    { freq: 880, start: 0, dur: 0.12 },
    { freq: 880, start: 0.18, dur: 0.12 },
    { freq: 1100, start: 0.36, dur: 0.25 },
  ]);
}

function playTickSound() {
  if (!userSettings.sounds.tick) return;
  playTones([{ freq: 660, start: 0, dur: 0.04, gain: 0.1 }]);
}

// ============================================================
// ブラウザ通知
// ============================================================
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function showNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body, icon: '' });
  }
}

// ============================================================
// セッション完了処理
// ============================================================
async function handleSessionComplete() {
  // 多重呼び出しを防ぐ（非同期処理中に tick が再度 0 を検知した場合）
  if (isCompletingSession) return;
  isCompletingSession = true;

  clearInterval(intervalId);
  intervalId = null;

  try {
    const durationSeconds = sessionStartTime
      ? Math.round((Date.now() - sessionStartTime) / 1000)
      : (timerState.total_duration - timerState.remaining_seconds);
    sessionStartTime = null;

    playEndSound();

    const wasWork = timerState.mode === 'work';
    const data = await apiPost('/api/complete', { duration_seconds: durationSeconds });
    updateUI(data);
    await fetchStats();

    if (wasWork) {
      showNotification('作業完了！', `${userSettings.break_duration_minutes}分間の休憩を取りましょう。`);
    } else {
      showNotification('休憩終了！', '次の作業セッションを始めましょう。');
    }

    // セッション完了後、次のタイマーを自動開始する
    const nextData = await apiPost('/api/start');
    updateUI(nextData);
    sessionStartTime = Date.now();
    intervalId = setInterval(tick, 1000);
  } catch (err) {
    // API エラー等で途中失敗した場合、サーバー状態を再取得して UI を復元する
    console.error('セッション完了処理中にエラーが発生しました:', err);
    try { await fetchState(); } catch (_) {}
    try { await fetchStats(); } catch (_) {}
  } finally {
    isCompletingSession = false;
  }
}

// ============================================================
// カウントダウン tick
// ============================================================
function tick() {
  if (timerState.remaining_seconds <= 0) {
    // isCompletingSession が true の間は呼び出しをスキップ（二重実行防止）
    if (!isCompletingSession) {
      handleSessionComplete();
    }
    return;
  }
  timerState.remaining_seconds -= 1;
  playTickSound();
  const m = Math.floor(timerState.remaining_seconds / 60);
  const s = timerState.remaining_seconds % 60;
  timeDisplay.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

  updateRingVisuals(timerState.remaining_seconds, timerState.total_duration, timerState.mode);
}

// ============================================================
// ボタンイベント
// ============================================================
startPauseBtn.addEventListener('click', async () => {
  if (timerState.state === 'running') {
    // 一時停止
    clearInterval(intervalId);
    intervalId = null;
    const data = await apiPost('/api/pause');
    updateUI(data);
  } else {
    // 開始 or 再開
    requestNotificationPermission();
    playStartSound();
    const data = await apiPost('/api/start');
    updateUI(data);
    if (sessionStartTime === null) {
      sessionStartTime = Date.now() - ((timerState.total_duration - timerState.remaining_seconds) * 1000);
    }
    clearInterval(intervalId);
    intervalId = setInterval(tick, 1000);
  }
});

resetBtn.addEventListener('click', async () => {
  clearInterval(intervalId);
  intervalId = null;
  sessionStartTime = null;
  const data = await apiPost('/api/reset');
  updateUI(data);
});

workDurationSelect.addEventListener('change', async () => {
  userSettings.work_duration_minutes = clampWorkDuration(Number(workDurationSelect.value));
  saveSettings();
  await syncTimerSettings();
});

breakDurationSelect.addEventListener('change', async () => {
  userSettings.break_duration_minutes = clampBreakDuration(Number(breakDurationSelect.value));
  saveSettings();
  await syncTimerSettings();
});

themeSelect.addEventListener('change', () => {
  userSettings.theme = ['light', 'dark', 'focus'].includes(themeSelect.value) ? themeSelect.value : 'light';
  applyTheme(userSettings.theme);
  saveSettings();
});

soundStartToggle.addEventListener('change', () => {
  userSettings.sounds.start = soundStartToggle.checked;
  saveSettings();
});

soundEndToggle.addEventListener('change', () => {
  userSettings.sounds.end = soundEndToggle.checked;
  saveSettings();
});

soundTickToggle.addEventListener('change', () => {
  userSettings.sounds.tick = soundTickToggle.checked;
  saveSettings();
});

// ============================================================
// 初期化
// ============================================================
(async () => {
  loadSettings();
  applyTheme(userSettings.theme);
  syncSettingsControls();
  await syncTimerSettings();
  await fetchStats();
})();
