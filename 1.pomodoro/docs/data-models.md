# データモデル仕様

---

## タイマー関連

### `TimerMode`（Enum）

タイマーのモードを表す文字列列挙型です。

| 値 | 説明 |
|---|---|
| `"work"` | 作業セッション |
| `"break"` | 休憩セッション |

### `TimerState`（Enum）

タイマーの動作状態を表す文字列列挙型です。

| 値 | 説明 |
|---|---|
| `"idle"` | 停止中（初期状態・リセット後・セッション完了後） |
| `"running"` | カウントダウン実行中 |
| `"paused"` | 一時停止中 |

### `PomodoroTimer`

タイマーのドメインモデルです。

**定数**

| 定数名 | 値 | 説明 |
|---|---|---|
| `WORK_DURATION` | `1500`（25分） | 作業セッションのデフォルト秒数 |
| `BREAK_DURATION` | `300`（5分） | 休憩セッションのデフォルト秒数 |
| `ALLOWED_WORK_DURATIONS_MINUTES` | `(15, 25, 35, 45)` | 設定可能な作業時間（分） |
| `ALLOWED_BREAK_DURATIONS_MINUTES` | `(5, 10, 15)` | 設定可能な休憩時間（分） |

**プロパティ**

| プロパティ | 型 | 説明 |
|---|---|---|
| `mode` | `TimerMode` | 現在のモード |
| `state` | `TimerState` | 現在の状態 |
| `remaining_seconds` | `int` | 残り秒数（RUNNING 中は経過時間を考慮して動的に計算） |
| `total_duration` | `int` | 現在モードの総秒数 |
| `settings` | `dict` | 現在の設定（`work_duration_minutes`, `break_duration_minutes`） |

**メソッド**

| メソッド | 説明 |
|---|---|
| `start()` | タイマーを開始または再開する（RUNNING 中は何もしない） |
| `pause()` | タイマーを一時停止する（RUNNING 以外は何もしない） |
| `reset()` | WORK モード・IDLE 状態・フル秒数に戻す |
| `complete_session()` | セッションを完了し次のモードへ切り替える |
| `set_durations(work_duration_minutes, break_duration_minutes)` | 作業/休憩時間を設定する（許可値以外は `ValueError`） |
| `to_dict()` | API レスポンス用の辞書を返す |
| `from_dict(data, clock_fn)` | 辞書から `PomodoroTimer` インスタンスを復元する |

**`to_dict()` の返り値**

```python
{
    "mode": "work",          # TimerMode の値
    "state": "idle",         # TimerState の値
    "remaining_seconds": 1500,
    "total_duration": 1500,
}
```

---

## 統計関連

### `StatsRepository`（Protocol）

ストレージ実装の抽象インターフェースです。

| メソッド | シグネチャ | 説明 |
|---|---|---|
| `record_session` | `(session_date: date, duration_seconds: int, mode: str) -> None` | セッションを記録する |
| `get_stats` | `(session_date: date) -> dict` | 指定日の統計を返す |

**`get_stats()` の返り値形式**

```python
{
    "completed": 3,       # 作業セッション完了数
    "focus_seconds": 4500, # 合計集中秒数
}
```

### `JsonStatsRepository`

ファイルシステムへの永続化実装です（本番用）。

| 属性 | 説明 |
|---|---|
| `filepath` | JSONファイルのパス（デフォルト: `"stats.json"`） |

保存されるJSONの形式:

```json
[
  {
    "date": "2026-06-09",
    "duration_seconds": 1500,
    "mode": "work"
  }
]
```

### `InMemoryStatsRepository`

メモリ上に記録するテスト用実装です。アプリ再起動でデータは消えます。

### `StatsService`

リポジトリを利用して統計ロジックを提供するサービスクラスです。

| メソッド | 説明 |
|---|---|
| `record_work_session(duration_seconds)` | 今日の作業セッションを記録する |
| `record_break_session(duration_seconds)` | 今日の休憩セッションを記録する |
| `get_today_stats()` | 今日の統計を取得する |

**`get_today_stats()` の返り値**

```python
{
    "completed": 3,
    "focus_seconds": 4500,
    "focus_label": "1時間15分",  # 60分未満は "XX分"、以上は "X時間XX分"
}
```

---

## ユーザー設定（クライアントサイド）

設定は `localStorage` のキー `"pomodoro.preferences.v1"` に保存されます。  
サーバーには保存されません。

```json
{
  "work_duration_minutes": 25,
  "break_duration_minutes": 5,
  "theme": "light",
  "sounds": {
    "start": true,
    "end": true,
    "tick": false
  }
}
```

| フィールド | 型 | デフォルト | 許可値 |
|---|---|---|---|
| `work_duration_minutes` | `integer` | `25` | `15`, `25`, `35`, `45` |
| `break_duration_minutes` | `integer` | `5` | `5`, `10`, `15` |
| `theme` | `string` | `"light"` | `"light"`, `"dark"`, `"focus"` |
| `sounds.start` | `boolean` | `true` | — |
| `sounds.end` | `boolean` | `true` | — |
| `sounds.tick` | `boolean` | `false` | — |
