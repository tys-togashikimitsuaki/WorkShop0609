# アーキテクチャ概要

## 概要

ポモドーロタイマーは Flask を使用したシンプルな Web アプリケーションです。  
サーバーサイドはレイヤードアーキテクチャを採用し、各層の責務を分離しています。

---

## ディレクトリ構成

```
1.pomodoro/
├── app.py                  # Flask アプリケーションファクトリ・ルート定義
├── pomodoro/
│   ├── __init__.py
│   ├── timer.py            # タイマードメインモデル
│   └── stats.py            # 統計サービス・リポジトリ
├── static/
│   ├── js/app.js           # クライアントサイド JavaScript
│   └── css/style.css       # スタイルシート
├── templates/
│   └── index.html          # メイン HTML テンプレート
├── tests/
│   ├── test_app.py         # Flask ルートのテスト
│   ├── test_timer.py       # タイマードメインモデルのテスト
│   └── test_stats.py       # 統計サービスのテスト
├── requirements.txt
└── docs/                   # ドキュメント
```

---

## レイヤー構成

```
┌─────────────────────────────────────────┐
│           HTTP / ルート層               │
│   app.py（Flask ルートハンドラー）       │
└──────────────┬──────────────────────────┘
               │ 依存性注入（create_app() ファクトリ）
               ▼
┌─────────────────────────────────────────┐
│            ドメイン層                   │
│   PomodoroTimer (pomodoro/timer.py)     │
│   StatsService  (pomodoro/stats.py)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│          リポジトリ層                   │
│   JsonStatsRepository — ファイル永続化  │
│   InMemoryStatsRepository — テスト用    │
└─────────────────────────────────────────┘
```

---

## 主要設計パターン

### アプリケーションファクトリ（`create_app()`）

`app.py` の `create_app()` は `PomodoroTimer` と `StatsService` を引数で受け取ります。  
本番時は省略（新規インスタンスを自動生成）、テスト時にはモックを注入できます。

```python
# 本番
app = create_app()

# テスト
app = create_app(timer=mock_timer, stats_service=mock_stats)
```

### 依存性注入（DI）

- `PomodoroTimer` は `clock_fn` を受け取ります。本番は `time.time`、テストは固定値ラムダを注入することで時刻依存ロジックを確定的にテストできます。
- `StatsService` は `StatsRepository` Protocol を実装した任意のリポジトリを受け取ります。

### Repository パターン

`StatsRepository` は Python の `Protocol` として定義されており、以下のメソッドを持ちます：

| メソッド | 説明 |
|---|---|
| `record_session(session_date, duration_seconds, mode)` | セッションを記録する |
| `get_stats(session_date)` | 指定日の統計を取得する |

実装は2種類：
- `JsonStatsRepository`: `stats.json` ファイルへの永続化（本番用）
- `InMemoryStatsRepository`: メモリ上のリスト（テスト用）

---

## タイマー状態遷移

```
        start()
  IDLE ──────────► RUNNING
   ▲                  │
   │   reset()        │ pause()
   │◄─────────────────┤
   │                  ▼
   │              PAUSED
   │                  │
   │   start()        │
   │◄─────────────────┘
   │
   │  complete_session()
   └───────────────────── モード切替（WORK ↔ BREAK）→ IDLE
```

---

## モード遷移

```
WORK ──complete_session()──► BREAK
BREAK ──complete_session()──► WORK
```

`reset()` は常に WORK モード・IDLE 状態に戻します。

---

## データ永続化

タイマー状態はサーバーメモリ上に保持され、**再起動するとリセット**されます。  
統計データのみ `stats.json` ファイルに永続化されます。

---

## フロントエンドとの通信

クライアント（`static/js/app.js`）はポーリングではなく **クライアント主導のカウントダウン** を採用しています。

- `setInterval` で毎秒カウントダウン
- タイマー開始・停止・リセット時にのみサーバー API を呼び出して状態を同期
- 残り秒数が 0 になると `/api/complete` を呼び出して統計記録とモード切替を行う
- セッション完了後は自動的に `/api/start` を呼び出して次のセッションを開始する
