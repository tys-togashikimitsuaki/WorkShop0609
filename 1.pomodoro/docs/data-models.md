# データモデル仕様

---

## タイマードメインモデル（`pomodoro/timer.py`）

### `TimerMode` 列挙型

| 値 | 説明 |
|---|---|
| `"work"` | 作業モード |
| `"break"` | 休憩モード |

### `TimerState` 列挙型

| 値 | 説明 |
|---|---|
| `"idle"` | 停止中（初期状態・リセット後・セッション完了後） |
| `"running"` | 実行中 |
| `"paused"` | 一時停止中 |

### `PomodoroTimer` クラス

タイマーの状態機械。`clock_fn` を依存性注入で受け取ることでテスト可能な設計になっている。

#### デフォルト設定値

| 定数 | 値 | 説明 |
|---|---|---|
| `WORK_DURATION` | `1500`（秒） | 作業時間のデフォルト（25 分） |
| `BREAK_DURATION` | `300`（秒） | 休憩時間のデフォルト（5 分） |
| `ALLOWED_WORK_DURATIONS_MINUTES` | `(15, 25, 35, 45)` | 選択可能な作業時間（分） |
| `ALLOWED_BREAK_DURATIONS_MINUTES` | `(5, 10, 15)` | 選択可能な休憩時間（分） |

#### `to_dict()` シリアライズ形式

```python
{
    "mode": "work",          # TimerMode.value
    "state": "idle",         # TimerState.value
    "remaining_seconds": 1500,
    "total_duration": 1500,
}
```

#### 状態遷移

```
         start()          pause()
  idle ──────────> running ────────> paused
   ↑                                    |
   |  reset() / complete_session()      | start()
   └──────────────────────────────────--┘
```

- `start()`: `idle` / `paused` → `running`（`running` 時は何もしない）
- `pause()`: `running` → `paused`（`running` 以外は何もしない）
- `reset()`: 任意 → `idle`（WORKモード・残り時間を全長に戻す）
- `complete_session()`: 任意 → `idle`（モードをトグル）

---

## 統計モデル（`pomodoro/stats.py`）

### `StatsRepository` プロトコル

永続化の抽象インターフェース。

```python
class StatsRepository(Protocol):
    def record_session(self, session_date: date, duration_seconds: int, mode: str) -> None: ...
    def get_stats(self, session_date: date) -> dict: ...
    def get_all_records(self) -> list[dict]: ...
```

### レコード形式（JSON ストレージ）

`stats.json` に JSON 配列として保存される。各レコードの形式:

```json
{
  "date": "2026-06-09",
  "duration_seconds": 1500,
  "mode": "work"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `date` | `string` (ISO 8601) | セッション実施日 |
| `duration_seconds` | `integer` | セッション時間（秒） |
| `mode` | `"work"` \| `"break"` | セッション種別 |

### `StatsService` — ゲーミフィケーション計算

| 定数 | 値 | 説明 |
|---|---|---|
| `XP_PER_WORK_SESSION` | `100` | 作業セッション 1 回あたりの XP |
| `LEVEL_STEP_XP` | `500` | 1 レベルアップに必要な XP |
| `WEEKLY_TARGET_SESSIONS` | `10` | 週間目標セッション数 |
| `MONTHLY_TARGET_SESSIONS` | `40` | 月間目標セッション数 |

#### レベル計算

```
level = (cumulative_xp // 500) + 1
xp_in_level = cumulative_xp % 500
xp_to_next_level = 500 - xp_in_level
```

#### ストリーク計算

今日から過去に向かって連続して作業セッションが存在する日数を数える。今日の記録がない場合は `0`。

#### バッジ一覧

| バッジ ID | 名前 | 達成条件 |
|---|---|---|
| `streak_3` | 3日連続 | 連続作業日数 ≥ 3 |
| `weekly_10` | 週10回 | 週間セッション数 ≥ 10 |

---

## フロントエンドの設定モデル（`localStorage`）

キー: `pomodoro.preferences.v1`

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

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `work_duration_minutes` | `integer` | `25` | 作業時間（分） |
| `break_duration_minutes` | `integer` | `5` | 休憩時間（分） |
| `theme` | `"light"` \| `"dark"` \| `"focus"` | `"light"` | テーマ |
| `sounds.start` | `boolean` | `true` | 開始音の有効/無効 |
| `sounds.end` | `boolean` | `true` | 終了音の有効/無効 |
| `sounds.tick` | `boolean` | `false` | tick 音の有効/無効 |
