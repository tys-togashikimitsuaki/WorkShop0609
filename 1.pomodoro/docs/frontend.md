# フロントエンド モジュール ドキュメント

---

## 概要

フロントエンドは単一の JavaScript ファイル `static/js/app.js` で構成されています。  
フレームワークは使用せず、ブラウザ標準 API（Fetch API、Web Audio API、Notification API）のみを使用しています。

---

## ファイル構成

| ファイル | 説明 |
|---|---|
| `static/js/app.js` | タイマーロジック・UI操作・API通信 |
| `static/css/style.css` | スタイルシート（テーマ変数・レイアウト・アニメーション） |
| `templates/index.html` | メイン HTML テンプレート（Jinja2） |

---

## `static/js/app.js`

### 定数

| 定数名 | 値 | 説明 |
|---|---|---|
| `RING_RADIUS` | `96` | SVGプログレスリングの半径（px） |
| `RING_CIRCUMFERENCE` | `2π × 96 ≈ 603.2` | リングの全周長（px） |
| `WORK_RING_COLOR_BLUE` | `[59, 130, 246]` | 作業リング開始色（青） |
| `WORK_RING_COLOR_YELLOW` | `[250, 204, 21]` | 作業リング中間色（黄） |
| `WORK_RING_COLOR_RED` | `[239, 68, 68]` | 作業リング終了色（赤） |
| `SETTINGS_STORAGE_KEY` | `"pomodoro.preferences.v1"` | localStorage のキー |

### 状態変数

| 変数名 | 型 | 説明 |
|---|---|---|
| `timerState` | `object` | サーバーから取得したタイマー状態（`mode`, `state`, `remaining_seconds`, `total_duration`） |
| `intervalId` | `number \| null` | `setInterval` のID（null = タイマー停止中） |
| `sessionStartTime` | `number \| null` | セッション開始の `Date.now()` 値（経過秒数計算用） |
| `isCompletingSession` | `boolean` | `handleSessionComplete` の再入防止フラグ |
| `userSettings` | `object` | ユーザー設定（localStorage から読み込み） |

### 主要関数

#### UI 更新

| 関数 | 説明 |
|---|---|
| `updateUI(data)` | サーバーレスポンスを元に時間表示・ステータスラベル・ボタンテキスト・リングを更新する |
| `updateStats(data)` | 完了数・集中時間ラベルを更新する |
| `updateRingVisuals(remainingSeconds, totalDuration, mode)` | SVGリングの `stroke-dashoffset` と色を更新する |
| `getWorkRingColor(progress)` | 進行度（0〜1）に応じて青→黄→赤の補間色を返す |
| `interpolateColor(from, to, t)` | 2色間をt（0〜1）で線形補間する |

#### API 通信

| 関数 | 説明 |
|---|---|
| `apiPost(path, body)` | JSON ボディ付き POST リクエストを送信し、レスポンスを返す |
| `fetchState()` | `GET /api/state` を呼び出し UI を更新する |
| `fetchStats()` | `GET /api/stats` を呼び出し統計 UI を更新する |

#### タイマー制御

| 関数 | 説明 |
|---|---|
| `tick()` | 毎秒呼び出され、`remaining_seconds` をデクリメントして表示を更新する。残り0秒で `handleSessionComplete()` を呼び出す |
| `handleSessionComplete()` | セッション完了時の一連の処理（統計送信→モード切替→通知→次セッション自動開始）を行う。`isCompletingSession` フラグで多重呼び出しを防ぐ |

#### 設定管理

| 関数 | 説明 |
|---|---|
| `loadSettings()` | localStorage から設定を読み込む。破損時はデフォルト値を使用 |
| `saveSettings()` | `userSettings` を localStorage に保存する |
| `syncSettingsControls()` | `userSettings` の値を各フォームコントロールに反映する |
| `syncTimerSettings()` | `POST /api/settings` でサーバー側の設定を同期する |
| `applyTheme(theme)` | `body` に `theme-{theme}` クラスを付与してテーマを切り替える |
| `clampWorkDuration(value)` | 許可値以外の場合 `25` にフォールバックする |
| `clampBreakDuration(value)` | 許可値以外の場合 `5` にフォールバックする |

#### サウンド通知

Web Audio API を使用。外部ファイル不要でトーンを生成します。

| 関数 | 説明 |
|---|---|
| `playTones(tones)` | `AudioContext` でサイン波トーンを再生する |
| `playStartSound()` | タイマー開始時のビープ音（740 Hz、0.12秒）を再生する |
| `playEndSound()` | セッション完了時の3音ビープ（880→880→1100 Hz）を再生する |
| `playTickSound()` | 毎秒の tick 音（660 Hz、小音量）を再生する |

各サウンドは `userSettings.sounds.{start|end|tick}` が `false` の場合スキップされます。

#### ブラウザ通知

| 関数 | 説明 |
|---|---|
| `requestNotificationPermission()` | Notification API の権限をリクエストする |
| `showNotification(title, body)` | 権限が `granted` の場合にブラウザ通知を表示する |

---

## `templates/index.html`

Flask Jinja2 テンプレートです。主要な DOM 要素は以下の通りです。

| ID | 要素 | 説明 |
|---|---|---|
| `timerCard` | `div.card` | タイマーカード全体。作業中は `.focus-mode` クラスが付与される |
| `statusLabel` | `div` | 現在のモード表示（「作業中」/「休憩中」） |
| `ringProgress` | `circle` (SVG) | プログレスリングの進捗部分 |
| `focusEffects` | `div` | フォーカスモード時のパーティクル・リップルエフェクトコンテナ |
| `timeDisplay` | `div` | 残り時間の表示（`MM:SS` 形式） |
| `startPauseBtn` | `button` | 開始/一時停止/再開ボタン |
| `resetBtn` | `button` | リセットボタン |
| `completedCount` | `span` | 今日の完了セッション数 |
| `focusLabel` | `span` | 今日の集中時間ラベル |
| `workDurationSelect` | `select` | 作業時間設定セレクトボックス |
| `breakDurationSelect` | `select` | 休憩時間設定セレクトボックス |
| `themeSelect` | `select` | テーマ設定セレクトボックス |
| `soundStartToggle` | `input[checkbox]` | 開始音のオン/オフ |
| `soundEndToggle` | `input[checkbox]` | 終了音のオン/オフ |
| `soundTickToggle` | `input[checkbox]` | tick音のオン/オフ |

---

## `static/css/style.css`

CSS カスタムプロパティ（変数）によるテーマ切り替えを実装しています。

### CSS 変数（`:root` デフォルト = ライトテーマ）

| 変数名 | デフォルト値 | 説明 |
|---|---|---|
| `--bg-color` | `#6B63D5` | 背景色 |
| `--card-bg` | `#fff` | カード背景色 |
| `--text-color` | `#2d2d3a` | テキスト色 |
| `--panel-bg` | `#EEF0FF` | パネル背景色 |

### テーマクラス

`body` に付与されるクラスによってテーマが切り替わります：

| クラス | テーマ |
|---|---|
| `theme-light` | ライトテーマ |
| `theme-dark` | ダークテーマ |
| `theme-focus` | フォーカステーマ |

### フォーカスモード

タイマーが作業中（`mode === "work"` かつ `state === "running"`）の間、`timerCard` に `.focus-mode` クラスが付与されます。  
このクラスにより `focusEffects` コンテナ内のパーティクル・リップルアニメーションが表示されます。

---

## 初期化フロー

アプリ起動時（IIFE）に以下の順序で処理が実行されます：

1. `loadSettings()` — localStorage から設定を読み込む
2. `applyTheme(userSettings.theme)` — テーマを適用する
3. `syncSettingsControls()` — フォームコントロールに設定値を反映する
4. `syncTimerSettings()` — サーバーにタイマー設定を同期し、UI を更新する
5. `fetchStats()` — 今日の統計を取得し表示する

---

## セッション完了フロー

1. `tick()` が `remaining_seconds === 0` を検知
2. `handleSessionComplete()` が呼び出される（`isCompletingSession` フラグで多重実行を防止）
3. `intervalId` をクリアしカウントダウンを停止
4. `playEndSound()` でセッション完了音を再生
5. `POST /api/complete` で統計を記録しモードを切り替える
6. `fetchStats()` で統計 UI を更新
7. `showNotification()` でブラウザ通知を表示
8. `POST /api/start` で次のセッションを自動開始
9. `setInterval(tick, 1000)` で次のカウントダウンを開始
