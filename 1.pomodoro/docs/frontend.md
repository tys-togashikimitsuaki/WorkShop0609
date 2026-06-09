# フロントエンド ドキュメント

ポモドーロタイマーのフロントエンド実装（`static/js/app.js`、`static/css/style.css`、`templates/index.html`）を説明します。

---

## 概要

フロントエンドは単一のJavaScriptファイル（`app.js`）で構成され、以下の機能を担う:

- サーバーAPIとのHTTP通信（`fetch`）
- `setInterval` によるクライアントサイドのカウントダウン
- SVG `stroke-dashoffset` による円形プログレスリングアニメーション
- Web Audio API によるサウンド通知（外部ファイル不要）
- Notification API によるブラウザ通知

---

## 定数

| 定数 | 値 | 説明 |
|---|---|---|
| `RING_RADIUS` | `96` | SVGリングの半径（px） |
| `RING_CIRCUMFERENCE` | `2π × 96 ≈ 603.2` | リングの全周長（`stroke-dasharray` に設定） |
| `WORK_RING_COLOR_BLUE` | `[59, 130, 246]` | 作業リングの開始色（青） |
| `WORK_RING_COLOR_YELLOW` | `[250, 204, 21]` | 作業リングの中間色（黄） |
| `WORK_RING_COLOR_RED` | `[239, 68, 68]` | 作業リングの終了色（赤） |

---

## 状態管理

グローバル変数でタイマーの状態を管理する:

```javascript
let timerState = {
  mode: 'work',          // 'work' | 'break'
  state: 'idle',         // 'idle' | 'running' | 'paused'
  remaining_seconds: 1500,
  total_duration: 1500,
};

let intervalId = null;           // setInterval の ID
let sessionStartTime = null;     // セッション開始時刻（Date.now()）
let isCompletingSession = false; // 完了処理の再入防止フラグ
```

---

## 主な関数

### UI更新

#### `updateUI(data)`

サーバーから受け取った状態オブジェクトでUIを更新する。

- `timerState` を更新
- 残り時間を `MM:SS` 形式で `#timeDisplay` に表示
- `#statusLabel` を `"作業中"` または `"休憩中"` に更新
- `updateRingVisuals()` を呼び出してリングを更新
- `#timerCard` に `.focus-mode` クラスをトグル（`work` モードかつ `running` 時のみ付与）
- `#startPauseBtn` のラベルを `"開始"` / `"再開"` / `"一時停止"` に切り替え

#### `updateStats(data)`

統計データを `#completedCount` と `#focusLabel` に反映する。

#### `updateRingVisuals(remainingSeconds, totalDuration, mode)`

SVGリングの `stroke-dashoffset` と `stroke` カラーを更新する。

- 進捗率: `progress = 1 - remaining / total`
- `stroke-dashoffset = RING_CIRCUMFERENCE × progress`（0でリング全体が表示、1で非表示）
- `work` モード: `getWorkRingColor(progress)` で青→黄→赤のグラデーション
- `break` モード: 固定色 `#56C8A0`（緑）

#### `getWorkRingColor(progress)`

`progress`（0〜1）に応じてリングカラーをRGB補間で返す:

- `0.0〜0.5`: 青 → 黄（`interpolateColor`）
- `0.5〜1.0`: 黄 → 赤（`interpolateColor`）

---

### API通信

#### `apiPost(path, body?)`

`fetch` を使ったPOSTリクエストのヘルパー。レスポンスのJSONを返す。

#### `fetchState()`

`GET /api/state` を呼び出して `updateUI()` に渡す。

#### `fetchStats()`

`GET /api/stats` を呼び出して `updateStats()` に渡す。

---

### タイマー制御

#### `tick()`

`setInterval` に渡す1秒ごとのコールバック。

- `remaining_seconds` をデクリメントして表示を更新
- `remaining_seconds <= 0` になったとき `handleSessionComplete()` を呼び出す
- `isCompletingSession` が `true` の間はスキップして二重実行を防ぐ

#### `handleSessionComplete()`

セッション完了時の非同期処理:

1. `isCompletingSession = true` で再入防止
2. `intervalId` をクリア
3. 経過時間を計算（`sessionStartTime` または `total - remaining`）
4. `playNotificationSound()` でサウンド再生
5. `POST /api/complete` でサーバーに通知・統計記録
6. `updateUI()` と `fetchStats()` でUI更新
7. ブラウザ通知（`showNotification()`）
8. `POST /api/start` で次のセッションを自動開始
9. `intervalId` を再設定してカウントダウン再開

---

### 通知

#### `playNotificationSound()`

Web Audio API（`AudioContext`）を使って以下の3音シーケンスを再生する:

| タイミング | 周波数 | 長さ |
|---|---|---|
| 0秒 | 880Hz | 0.12秒 |
| 0.18秒 | 880Hz | 0.12秒 |
| 0.36秒 | 1100Hz | 0.25秒 |

Web Audio 非対応環境ではエラーを無視する。

#### `requestNotificationPermission()`

Notification API の権限が `"default"` の場合にリクエストする。開始ボタン押下時に呼び出す。

#### `showNotification(title, body)`

権限が `"granted"` の場合にブラウザ通知を表示する。

---

## イベントハンドラ

### `#startPauseBtn` クリック

- `state === 'running'` のとき: `clearInterval` → `POST /api/pause` → `updateUI()`
- それ以外のとき: `requestNotificationPermission` → `POST /api/start` → `updateUI()` → `setInterval(tick, 1000)`

### `#resetBtn` クリック

`clearInterval` → `sessionStartTime = null` → `POST /api/reset` → `updateUI()`

---

## 初期化

ページロード時に即時実行関数（IIFE）で `fetchState()` と `fetchStats()` を呼び出してUIを初期状態に設定する。

---

## HTMLテンプレート（index.html）

主なDOM要素:

| 要素ID | 説明 |
|---|---|
| `timerCard` | メインカード。`focus-mode` クラスで作業中エフェクトをトグル |
| `focusEffects` | パーティクル・リップルエフェクトのコンテナ（`aria-hidden`） |
| `statusLabel` | モード表示ラベル（`"作業中"` / `"休憩中"`） |
| `ringProgress` | SVGプログレスリング |
| `timeDisplay` | 残り時間テキスト（`MM:SS`形式） |
| `startPauseBtn` | 開始/再開/一時停止ボタン |
| `resetBtn` | リセットボタン |
| `completedCount` | 本日の完了セッション数 |
| `focusLabel` | 本日の集中時間ラベル |

フォーカスエフェクトとして `.particle-1`〜`.particle-4` および `.ripple-1`〜`.ripple-2` の要素を含む。

---

## スタイル（style.css）

- **レイアウト**: flexboxで中央寄せ。最大幅380px
- **カラースキーム**: 背景色 `#6B63D5`（紫）、カード背景 `#fff`
- **タイトルバー**: macOSライクなウィンドウコントロールボタンを装飾
- **フォーカスモード**: `.focus-mode` クラス付与時にパーティクル・リップルアニメーションを有効化
