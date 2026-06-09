# データモデル仕様

ポモドーロタイマーで使用するデータモデルを説明します。

---

## タイマーモデル

### `TimerMode` (Enum)

タイマーのモードを表します。

| 値 | 意味 |
|---|---|
| `"work"` | 作業セッション（25 分） |
| `"break"` | 休憩セッション（5 分） |

### `TimerState` (Enum)

タイマーの動作状態を表します。

| 値 | 意味 |
|---|---|
| `"idle"` | 停止中（初期状態またはリセット後） |
| `"running"` | 動作中 |
| `"paused"` | 一時停止中 |

### `PomodoroTimer`

タイマーのドメインモデルクラスです。

**内部フィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `_mode` | `TimerMode` | 現在のモード |
| `_state` | `TimerState` | 現在の状態 |
| `_paused_remaining` | `int` | 一時停止時点の残り秒数 |
| `_start_time` | `float \| None` | タイマー開始時刻（`clock_fn` の値） |
| `_clock_fn` | `Callable[[], float]` | 時刻取得関数（DI 可能） |

**シリアライズ形式 (`to_dict()`):**

```json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

**デシリアライズ (`from_dict()`):**

```python
data = {
    "mode": "break",
    "state": "idle",
    "remaining_seconds": 200
}
timer = PomodoroTimer.from_dict(data)
```

---

## 統計モデル

### セッションレコード

`JsonStatsRepository` が `stats.json` に保存するレコード形式です。

```json
{
  "date": "2026-06-09",
  "duration_seconds": 1500,
  "mode": "work"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `date` | `string` | セッション日（ISO 8601 形式: `YYYY-MM-DD`） |
| `duration_seconds` | `integer` | セッションの継続時間（秒） |
| `mode` | `"work"` \| `"break"` | セッションのモード |

**`stats.json` 全体の形式（配列）:**

```json
[
  { "date": "2026-06-09", "duration_seconds": 1500, "mode": "work" },
  { "date": "2026-06-09", "duration_seconds": 300,  "mode": "break" },
  { "date": "2026-06-09", "duration_seconds": 1500, "mode": "work" }
]
```

### 統計レスポンス

`StatsService.get_today_stats()` の返却形式です。

```json
{
  "completed": 2,
  "focus_seconds": 3000,
  "focus_label": "50分"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `completed` | `integer` | 今日完了した `work` セッション数 |
| `focus_seconds` | `integer` | 今日の `work` セッション合計時間（秒） |
| `focus_label` | `string` | 集中時間の表示文字列 |

**`focus_label` のフォーマット規則:**

| 条件 | 形式 | 例 |
|---|---|---|
| 60 分未満 | `"N分"` | `"25分"` |
| 60 分以上 | `"N時間M分"` | `"1時間40分"` |
| ちょうど1時間 | `"N時間0分"` | `"1時間0分"` |
| 0 分 | `"0分"` | `"0分"` |

---

## `StatsRepository` プロトコル

リポジトリ実装が満たすべきインターフェースです。

```python
class StatsRepository(Protocol):
    def record_session(
        self,
        session_date: date,
        duration_seconds: int,
        mode: str
    ) -> None: ...

    def get_stats(self, session_date: date) -> dict: ...
```

`get_stats()` の返却形式:

```python
{
    "completed": int,   # 作業セッション数
    "focus_seconds": int,  # 作業時間合計（秒）
}
```
