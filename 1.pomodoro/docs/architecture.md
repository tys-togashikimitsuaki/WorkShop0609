# アーキテクチャ概要

ポモドーロタイマーアプリの現在のアーキテクチャを説明します。

---

## 全体構成

```
1.pomodoro/
├── app.py                  # アプリケーションファクトリ（Flask ルート定義）
├── requirements.txt        # 依存ライブラリ
├── pomodoro/               # ドメイン層
│   ├── timer.py            # PomodoroTimer ドメインモデル
│   └── stats.py            # 統計サービス・リポジトリ
├── static/
│   ├── css/style.css       # スタイルシート
│   └── js/app.js           # フロントエンド JavaScript
├── templates/
│   └── index.html          # HTMLテンプレート
└── tests/                  # テストスイート
    ├── test_app.py
    ├── test_timer.py
    └── test_stats.py
```

---

## レイヤー構成

```
┌─────────────────────────────────────┐
│   フロントエンド（ブラウザ）            │
│   static/js/app.js                  │
│   templates/index.html              │
└──────────────┬──────────────────────┘
               │ HTTP (REST API)
┌──────────────▼──────────────────────┐
│   Flask ルート層（app.py）            │
│   GET /, GET/POST /api/*            │
└──────────┬───────────┬──────────────┘
           │           │
┌──────────▼──┐  ┌─────▼──────────────┐
│ PomodoroTimer│  │  StatsService      │
│ (timer.py)  │  │  (stats.py)        │
└─────────────┘  └─────┬──────────────┘
                       │
              ┌────────▼────────┐
              │ StatsRepository  │
              │ (Protocol)       │
              ├─────────────────┤
              │JsonStatsRepository│ ← 本番（stats.json）
              │InMemoryStats...  │ ← テスト用
              └─────────────────┘
```

---

## アプリケーションファクトリ（app.py）

`create_app()` ファクトリ関数でFlaskアプリを構築する。`PomodoroTimer` と `StatsService` をコンストラクタ引数として受け取ることで、テスト時に任意の実装を注入できる（依存性注入）。

```python
def create_app(
    timer: PomodoroTimer | None = None,
    stats_service: StatsService | None = None
) -> Flask
```

- `timer` 省略時: `PomodoroTimer()` を新規作成
- `stats_service` 省略時: `JsonStatsRepository(filepath="stats.json")` ベースの `StatsService` を作成

---

## ドメイン層（pomodoro/）

### PomodoroTimer（timer.py）

タイマーのすべての状態と遷移ロジックを持つドメインモデル。

- **状態管理**: `TimerMode`（`work`/`break`）と `TimerState`（`idle`/`running`/`paused`）の2軸で管理
- **時刻抽象化**: `clock_fn` (デフォルト: `time.time`) をDIで受け取るため、テストで時刻を制御可能
- **残り時間計算**: `running` 状態では `clock_fn()` からリアルタイムに計算（ポーリング不要）

定数:

| 定数 | 値 | 説明 |
|---|---|---|
| `WORK_DURATION` | `1500`秒（25分） | 作業セッション時間 |
| `BREAK_DURATION` | `300`秒（5分） | 休憩セッション時間 |

### 統計（stats.py）

Repositoryパターンで実装。`StatsRepository` プロトコルで抽象インターフェースを定義し、本番用とテスト用の実装を切り替え可能にしている。

| クラス | 用途 |
|---|---|
| `StatsRepository` | Protocolによる抽象インターフェース |
| `JsonStatsRepository` | `stats.json` ファイルへの永続化（本番用） |
| `InMemoryStatsRepository` | メモリ内ストレージ（テスト用） |
| `StatsService` | 統計記録・取得のビジネスロジック |

---

## 設計方針

- **薄いルート層**: `app.py` のルートハンドラはドメイン層を呼び出すだけで、ビジネスロジックを持たない
- **依存性注入**: `create_app()` / `PomodoroTimer` / `StatsService` はすべてDIに対応しており、テストで容易に差し替えられる
- **Protocolによる抽象化**: `StatsRepository` を `typing.Protocol` で定義することで、インターフェース継承なしに実装を差し替え可能
- **テスタビリティ**: `InMemoryStatsRepository` と `clock_fn` DIにより、外部依存（ファイルI/O・時刻）なしにすべてのロジックをユニットテスト可能
