# アーキテクチャ概要

## 全体構成

ポモドーロタイマーは **Flask** ベースの Web アプリケーションで、サーバーサイドとクライアントサイドに分かれる。

```
1.pomodoro/
├── app.py                  # Flask アプリケーションファクトリ・ルート定義
├── pomodoro/
│   ├── timer.py            # タイマードメインモデル
│   └── stats.py            # 統計リポジトリ・サービス
├── static/
│   ├── js/app.js           # フロントエンド JavaScript
│   └── css/style.css       # スタイルシート
├── templates/
│   └── index.html          # HTML テンプレート（シングルページ）
└── tests/
    ├── test_app.py         # Flask ルートのテスト
    ├── test_timer.py       # PomodoroTimer のテスト
    └── test_stats.py       # StatsService のテスト
```

---

## レイヤー構成

### 1. プレゼンテーション層（`app.py`）

- Flask のルートハンドラのみを定義する「薄い層」
- ビジネスロジックはドメイン層に委譲する
- `create_app(timer, stats_service)` ファクトリ関数で依存性注入を実現

### 2. ドメイン層（`pomodoro/`）

#### `pomodoro/timer.py` — タイマードメインモデル

- `PomodoroTimer`: タイマーの状態機械
- `TimerMode`: `work` / `break` の 2 モード
- `TimerState`: `idle` / `running` / `paused` の 3 状態
- `clock_fn` の DI により、テスト時に時刻を固定して決定的なテストが可能

#### `pomodoro/stats.py` — 統計サービス・リポジトリ

- **Repository パターン**で永続化をビジネスロジックから分離
  - `StatsRepository`（Protocol）: リポジトリの抽象インターフェース
  - `JsonStatsRepository`: JSON ファイルへの永続化実装（本番用）
  - `InMemoryStatsRepository`: メモリ上の実装（テスト用）
- `StatsService`: 統計の記録・集計・ゲーミフィケーション計算を担当

### 3. フロントエンド層（`static/js/app.js`）

- シングルファイル構成
- `setInterval` で 1 秒ごとにカウントダウン（サーバーとは起動時および完了時に同期）
- SVG `stroke-dashoffset` でプログレスリングをアニメーション
- Web Audio API でサウンド通知（外部音声ファイル不要）
- Notification API でブラウザ通知
- ユーザー設定は `localStorage` に保存（キー: `pomodoro.preferences.v1`）

---

## 依存関係

```
app.py
 ├── pomodoro.timer.PomodoroTimer
 └── pomodoro.stats.StatsService
        └── pomodoro.stats.StatsRepository (Protocol)
               ├── JsonStatsRepository   (本番)
               └── InMemoryStatsRepository (テスト)
```

---

## テスト戦略

| テストファイル | 対象 | モック方針 |
|---|---|---|
| `tests/test_timer.py` | `PomodoroTimer` | `clock_fn` にラムダを注入して時刻固定 |
| `tests/test_stats.py` | `StatsService` | `InMemoryStatsRepository` を注入してファイル I/O を排除 |
| `tests/test_app.py` | Flask ルート | `create_app()` に上記のモックを注入して HTTP レイヤーをテスト |

---

## 依存パッケージ

| パッケージ | 用途 |
|---|---|
| `flask>=3.0` | Web フレームワーク |
| `pytest>=8.0` | テストランナー |
