# アーキテクチャ概要

ポモドーロタイマーアプリケーションのアーキテクチャを説明します。

---

## レイヤー構成

```
┌────────────────────────────────────────────────┐
│  プレゼンテーション層                            │
│  templates/index.html  static/css/style.css     │
│  static/js/app.js                               │
├────────────────────────────────────────────────┤
│  アプリケーション層（Flask ルーティング）         │
│  app.py（create_app ファクトリ）                 │
├────────────────────────────────────────────────┤
│  ドメイン層                                     │
│  pomodoro/timer.py     pomodoro/stats.py        │
│  PomodoroTimer         StatsService             │
├────────────────────────────────────────────────┤
│  インフラ層（リポジトリ）                         │
│  JsonStatsRepository（stats.json への永続化）    │
│  InMemoryStatsRepository（テスト用）             │
└────────────────────────────────────────────────┘
```

---

## 主要コンポーネント

### `app.py` — アプリケーションファクトリ

`create_app()` 関数でアプリケーションを生成します。`PomodoroTimer` と `StatsService` を引数として受け取ることで、テスト時に任意の実装へ差し替えられる依存性注入（DI）を実現しています。

```python
def create_app(
    timer: PomodoroTimer | None = None,
    stats_service: StatsService | None = None
) -> Flask:
    ...
```

**登録エンドポイント:**

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/` | UI ページ |
| `GET` | `/api/state` | タイマー状態取得 |
| `POST` | `/api/start` | タイマー開始 / 再開 |
| `POST` | `/api/pause` | タイマー一時停止 |
| `POST` | `/api/reset` | タイマーリセット |
| `POST` | `/api/complete` | セッション完了通知 |
| `GET` | `/api/stats` | 今日の統計取得 |

---

### `pomodoro/timer.py` — PomodoroTimer

ポモドーロタイマーのドメインモデルです。状態機械として動作します。

**状態遷移:**

```
IDLE ──start()──► RUNNING ──pause()──► PAUSED
 ▲                    │                   │
 │                    │                   │
 └──reset()──◄────────┘     start()──────►┘
              complete_session() で次モードへ切り替え
```

`clock_fn` を DI することで、テスト時に時刻を固定してタイムアウト待機なしにテストできます。

---

### `pomodoro/stats.py` — StatsService / Repository

Repository パターンでストレージ実装とビジネスロジックを分離しています。

```
StatsService ──uses──► StatsRepository (Protocol)
                              ▲
                   ┌──────────┴─────────────┐
                   │                         │
         JsonStatsRepository        InMemoryStatsRepository
         （stats.json に保存）        （テスト用・メモリ内）
```

**責務分担:**

| クラス | 責務 |
|---|---|
| `StatsService` | ビジネスロジック（今日の統計取得、セッション記録） |
| `JsonStatsRepository` | JSON ファイル（`stats.json`）への永続化 |
| `InMemoryStatsRepository` | テスト用インメモリストレージ |

---

## 設定値

| 定数 | 値 | 説明 |
|---|---|---|
| `WORK_DURATION` | 1500 秒（25 分） | 作業セッションの時間 |
| `BREAK_DURATION` | 300 秒（5 分） | 休憩セッションの時間 |

---

## 依存関係

```
flask>=3.0   — Web フレームワーク
pytest>=8.0  — テストフレームワーク（開発用）
```

---

## 本番起動

```bash
python app.py
# または
FLASK_DEBUG=1 python app.py
```

`FLASK_DEBUG` 環境変数に `1`, `true`, `yes`, `on` を設定するとデバッグモードで起動します。
