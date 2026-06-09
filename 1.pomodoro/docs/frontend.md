# フロントエンドドキュメント

ポモドーロタイマーのフロントエンド実装を説明します。

---

## ファイル構成

```
static/
  css/
    style.css      — スタイルシート
  js/
    app.js         — クライアントサイドの全ロジック
templates/
  index.html       — ベース HTML テンプレート
```

---

## `static/js/app.js`

クライアントサイドのすべてのロジックを担う単一モジュールです。

### 定数

| 定数 | 値 | 説明 |
|---|---|---|
| `RING_RADIUS` | `96` | SVG プログレスリングの半径（px） |
| `RING_CIRCUMFERENCE` | `≈ 603.2` | リングの円周（`2π × 96`）。`stroke-dashoffset` 計算に使用 |

---

### 状態管理

```javascript
let timerState = {
  mode: 'work',
  state: 'idle',
  remaining_seconds: 1500,
  total_duration: 1500,
};

let intervalId = null;           // setInterval の ID
let sessionStartTime = null;     // セッション開始時刻（経過時間計算用）
let isCompletingSession = false; // handleSessionComplete の再入防止フラグ
```

---

### 主要関数

#### `updateUI(data)`

タイマーレスポンスを受け取り、以下の UI 要素を更新します。

- **残り時間表示** (`#timeDisplay`): `MM:SS` 形式
- **ステータスラベル** (`#statusLabel`): `work` → `作業中`、`break` → `休憩中`
- **リングカラー** (`#ringProgress`): `work` → `#6B63D5`（パープル）、`break` → `#56C8A0`（グリーン）
- **リング進捗**: `remaining_seconds / total_duration` の比率を `stroke-dashoffset` で表現
- **ボタンラベル** (`#startPauseBtn`): `running` → `一時停止`、`paused` → `再開`、`idle` → `開始`

#### `updateStats(data)`

統計レスポンスを受け取り、以下を更新します。

- `#completedCount`: 完了セッション数
- `#focusLabel`: 集中時間ラベル

#### `tick()`

`setInterval` から毎秒呼び出されます。

- `remaining_seconds` をデクリメントして時間表示・リングを更新します。
- `remaining_seconds === 0` になると `handleSessionComplete()` を呼び出します。
- `isCompletingSession` フラグで二重呼び出しを防止します。

#### `handleSessionComplete()`

セッション完了時の非同期処理です。

1. `setInterval` を停止
2. 経過時間を計算（`sessionStartTime` から算出、またはフォールバック値を使用）
3. `playNotificationSound()` でサウンド通知
4. `POST /api/complete` でサーバーに通知・統計記録
5. `fetchStats()` で統計更新
6. `showNotification()` でブラウザ通知（作業完了または休憩終了）
7. `POST /api/start` で次のセッションを**自動開始**
8. 新しい `setInterval` でカウントダウン再開

#### `playNotificationSound()`

Web Audio API を使ってビープ音を生成します（外部音声ファイル不要）。

- 880Hz × 2 回 → 1100Hz × 1 回のビープシーケンス
- `sine` 波形、`exponentialRampToValueAtTime` でフェードアウト
- 非対応環境では無視（try-catch で握りつぶし）

#### `requestNotificationPermission()`

ブラウザ通知の許可を要求します。初回の「開始」ボタンクリック時に呼び出されます。

#### `showNotification(title, body)`

`Notification.permission === 'granted'` の場合にブラウザ通知を表示します。

---

### API 呼び出しヘルパー

#### `apiPost(path, body?)`

JSON ボディで POST リクエストを送信し、レスポンス JSON を返します。

```javascript
async function apiPost(path, body = null)
```

#### `fetchState()`

`GET /api/state` でサーバーから最新状態を取得して UI を更新します。

#### `fetchStats()`

`GET /api/stats` で今日の統計を取得して統計 UI を更新します。

---

### ボタンイベント

| ボタン | ID | 動作 |
|---|---|---|
| 開始 / 一時停止 / 再開 | `#startPauseBtn` | 現在状態に応じて `POST /api/pause` または `POST /api/start` を呼び出し |
| リセット | `#resetBtn` | `setInterval` 停止 → `POST /api/reset` → UI 更新 |

**開始ボタンの動作詳細:**

- `state === 'running'` の場合: 一時停止（インターバル停止 → `POST /api/pause`）
- それ以外の場合: 開始 / 再開（`POST /api/start` → インターバル開始）

---

### 初期化

ページ読み込み時に即時実行される非同期 IIFE で `fetchState()` と `fetchStats()` を呼び出し、サーバーの最新状態を反映します。

```javascript
(async () => {
  await fetchState();
  await fetchStats();
})();
```

---

## `static/css/style.css`

### レイアウト概要

| クラス | 説明 |
|---|---|
| `.app-wrapper` | 最大幅 380px のカード全体のラッパー |
| `.titlebar` | タイトルバー（タイトル + macOS 風コントロールボタン） |
| `.card` | メインコンテンツカード |

### カラーパレット

| 用途 | カラーコード |
|---|---|
| 背景（ページ） | `#6B63D5`（パープル） |
| カード背景 | `#ffffff` |
| 作業リング | `#6B63D5` |
| 休憩リング | `#56C8A0` |
| プライマリボタン | `#5E56C8` |
| 統計パネル背景 | `#EEF0FF` |

### レスポンシブ対応

画面幅 420px 以下でフルスクリーン表示（`border-radius` を除去）します。

---

## `templates/index.html`

### DOM 構造

```
.app-wrapper
  .titlebar
    .titlebar-title
    .titlebar-controls
  .card
    #statusLabel      ← ステータスラベル（作業中 / 休憩中）
    .ring-container
      svg.ring-svg
        circle.ring-track     ← トラック（背景リング）
        circle#ringProgress   ← 進捗リング
      #timeDisplay    ← 残り時間（MM:SS）
    .btn-row
      #startPauseBtn  ← 開始 / 一時停止 / 再開ボタン
      #resetBtn       ← リセットボタン
    .stats-panel
      #completedCount ← 完了セッション数
      #focusLabel     ← 集中時間ラベル
```

SVG プログレスリングは `viewBox="0 0 220 220"`、半径 96、中心 (110, 110)、`transform="rotate(-90 110 110)"` で 12 時方向から開始します。
