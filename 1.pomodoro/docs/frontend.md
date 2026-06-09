# フロントエンドドキュメント

---

## 概要

フロントエンドはシングルファイル構成（`static/js/app.js`）で実装されており、外部ライブラリに依存しない。

| ファイル | 役割 |
|---|---|
| `templates/index.html` | アプリケーションの HTML 構造 |
| `static/js/app.js` | タイマー・UI・API 通信・設定管理のすべてのロジック |
| `static/css/style.css` | スタイルシート（テーマ対応） |

---

## HTML 構造（`templates/index.html`）

シングルページアプリケーション。主要な要素の ID:

| 要素 ID | 説明 |
|---|---|
| `timerCard` | メインカード（`.focus-mode` クラスで集中エフェクトが有効化） |
| `statusLabel` | 「作業中」/「休憩中」のステータスラベル |
| `timeDisplay` | 残り時間表示（`MM:SS` 形式） |
| `ringProgress` | SVG プログレスリングの `<circle>` 要素 |
| `startPauseBtn` | 開始/一時停止/再開ボタン |
| `resetBtn` | リセットボタン |
| `completedCount` | 今日の完了セッション数 |
| `focusLabel` | 今日の集中時間ラベル |
| `levelValue` | レベル表示（例: `Lv.1`） |
| `xpValue` | XP 表示（例: `100 XP`） |
| `streakValue` | ストリーク表示（例: `3日`） |
| `badgeList` | バッジ一覧コンテナ |
| `weeklyRate` / `weeklyRateFill` | 週間完了率テキストとプログレスバー |
| `weeklyAvg` | 週間平均集中時間 |
| `monthlyRate` / `monthlyRateFill` | 月間完了率テキストとプログレスバー |
| `monthlyAvg` | 月間平均集中時間 |
| `workDurationSelect` | 作業時間セレクト（15/25/35/45分） |
| `breakDurationSelect` | 休憩時間セレクト（5/10/15分） |
| `themeSelect` | テーマセレクト（light/dark/focus） |
| `soundStartToggle` | 開始音チェックボックス |
| `soundEndToggle` | 終了音チェックボックス |
| `soundTickToggle` | tick 音チェックボックス |

---

## JavaScript モジュール（`static/js/app.js`）

### 定数

| 定数 | 値 | 説明 |
|---|---|---|
| `RING_RADIUS` | `96` | プログレスリングの半径（px） |
| `RING_CIRCUMFERENCE` | `≈ 603.2` | リングの円周（`2π × 96`） |
| `WORK_RING_COLOR_BLUE` | `[59, 130, 246]` | 作業リング: 開始色（青） |
| `WORK_RING_COLOR_YELLOW` | `[250, 204, 21]` | 作業リング: 中間色（黄） |
| `WORK_RING_COLOR_RED` | `[239, 68, 68]` | 作業リング: 終了色（赤） |
| `SETTINGS_STORAGE_KEY` | `"pomodoro.preferences.v1"` | localStorage キー |

### 状態変数

| 変数 | 型 | 説明 |
|---|---|---|
| `timerState` | `object` | サーバーから取得した最新のタイマー状態 |
| `intervalId` | `number \| null` | `setInterval` の ID（null = 停止中） |
| `sessionStartTime` | `number \| null` | セッション開始時の `Date.now()`（経過時間計算用） |
| `isCompletingSession` | `boolean` | `handleSessionComplete` の再入防止フラグ |
| `userSettings` | `object` | ユーザー設定（localStorage に永続化） |

### 主要関数

#### UI 更新

| 関数 | 説明 |
|---|---|
| `updateUI(data)` | タイマー状態オブジェクトを受け取り、時刻表示・ステータス・リング・ボタンラベルを更新 |
| `updateStats(data)` | 統計 API レスポンスを受け取り、セッション数・XP・バッジ等の統計 UI を更新 |
| `updateRingVisuals(remaining, total, mode)` | `stroke-dashoffset` を更新してリングアニメーション。作業モードは青→黄→赤でグラデーション、休憩モードは緑（`#56C8A0`） |
| `getWorkRingColor(progress)` | 作業モードのプログレス（0.0〜1.0）に応じた RGB 文字列を返す |

#### API 通信

| 関数 | 説明 |
|---|---|
| `apiPost(path, body)` | `fetch` で POST リクエストを送信し、JSON レスポンスを返す |
| `fetchState()` | `GET /api/state` を呼び出し `updateUI` を実行 |
| `fetchStats()` | `GET /api/stats` を呼び出し `updateStats` を実行 |

#### タイマー制御

| 関数 | 説明 |
|---|---|
| `tick()` | 1 秒ごとに呼ばれる。残り時間をデクリメントし UI を更新。`0` になったら `handleSessionComplete` を呼ぶ |
| `handleSessionComplete()` | セッション完了処理。`/api/complete` → `/api/start` を呼び出し、統計更新・通知表示・次セッションの自動開始を行う。`isCompletingSession` フラグで再入防止 |

#### 設定管理

| 関数 | 説明 |
|---|---|
| `loadSettings()` | localStorage から設定を読み込む。破損時はデフォルト値を使用 |
| `saveSettings()` | `userSettings` を localStorage に保存 |
| `applyTheme(theme)` | `body` のクラス（`theme-light` / `theme-dark` / `theme-focus`）を切り替え |
| `syncSettingsControls()` | `userSettings` の値でフォームコントロールを初期化 |
| `syncTimerSettings()` | `POST /api/settings` を呼び出してサーバー側のタイマー設定を同期 |

#### サウンド通知（Web Audio API）

外部音声ファイルを使用せず、`AudioContext` でサイン波を生成する。

| 関数 | 説明 |
|---|---|
| `playTones(tones)` | 周波数・開始時刻・継続時間の配列を受け取り、Web Audio API で再生 |
| `playStartSound()` | 開始音（740Hz、0.12秒）。`userSettings.sounds.start` が `false` の場合はスキップ |
| `playEndSound()` | 終了音（880Hz → 880Hz → 1100Hz の 3 音）。`userSettings.sounds.end` が `false` の場合はスキップ |
| `playTickSound()` | tick 音（660Hz、0.04秒、音量小）。`userSettings.sounds.tick` が `true` の場合のみ再生 |

#### ブラウザ通知（Notification API）

| 関数 | 説明 |
|---|---|
| `requestNotificationPermission()` | 通知権限がデフォルト状態の場合に許可をリクエスト |
| `showNotification(title, body)` | 通知権限が `granted` の場合にブラウザ通知を表示 |

### 初期化フロー

```
ページ読み込み
  ↓
loadSettings()           — localStorage から設定を復元
applyTheme()             — テーマを適用
syncSettingsControls()   — フォームコントロールを更新
syncTimerSettings()      — POST /api/settings でサーバーと同期
fetchStats()             — GET /api/stats で統計を取得・表示
```

### セッション完了フロー

```
tick() で remaining_seconds === 0 を検知
  ↓
handleSessionComplete()
  ├── clearInterval()
  ├── POST /api/complete  — 統計記録・モード切替
  ├── fetchStats()        — 統計 UI を更新
  ├── showNotification()  — ブラウザ通知
  └── POST /api/start     — 次セッションを自動開始
        ↓
      setInterval(tick, 1000) を再開
```

---

## CSS（`static/css/style.css`）

### テーマ

CSS カスタムプロパティで 3 テーマをサポート:

| テーマ | クラス | 背景色 |
|---|---|---|
| ライト（デフォルト） | `theme-light`（`:root`） | `#6B63D5`（紫） |
| ダーク | `theme-dark` | `#12121b`（濃紺） |
| フォーカス | `theme-focus` | `#111418`（ほぼ黒） |

### 集中エフェクト

タイマーが `running` かつ `work` モードの場合、`timerCard` に `.focus-mode` クラスが付与され、以下のアニメーションが有効化される:

- **パーティクル** (`.particle`): 4 個の円形要素が上下に漂う（`particleDrift` アニメーション）
- **リップル** (`.ripple`): 2 個の円形枠が拡散・フェードアウト（`ripplePulse` アニメーション）

### レスポンシブ

`@media (max-width: 420px)` でモバイル表示に対応。カードが画面全体に広がり、角丸を除去。
