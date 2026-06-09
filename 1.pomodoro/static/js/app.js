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
// サウンド通知（Web Audio API — 外部ファイル不要）
// ============================================================
function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const beepSequence = [
      { freq: 880, start: 0,    dur: 0.12 },
      { freq: 880, start: 0.18, dur: 0.12 },
      { freq: 1100, start: 0.36, dur: 0.25 },
    ];
    beepSequence.forEach(({ freq, start, dur }) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.4, ctx.currentTime + start);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
      osc.start(ctx.currentTime + start);
      osc.stop(ctx.currentTime + start + dur + 0.05);
    });
  } catch (_) {
    // Web Audio 非対応環境では無視
  }
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

    playNotificationSound();

    const wasWork = timerState.mode === 'work';
    const data = await apiPost('/api/complete', { duration_seconds: durationSeconds });
    updateUI(data);
    await fetchStats();

    if (wasWork) {
      showNotification('作業完了！', '5分間の休憩を取りましょう。');
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

// ============================================================
// 初期化
// ============================================================
(async () => {
  await fetchState();
  await fetchStats();
})();
