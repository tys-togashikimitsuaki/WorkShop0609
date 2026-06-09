# データモデル仕様

ポモドーロタイマーアプリで使用するデータモデルを定義します。

---

## Enum: TimerMode

タイマーのモード（作業/休憩）を表す。

| 値 | 意味 |
|---|---|
| `"work"` | 作業セッション（25分） |
| `"break"` | 休憩セッション（5分） |

---

## Enum: TimerState

タイマーの動作状態を表す。

| 値 | 意味 |
|---|---|
| `"idle"` | 停止中（初期状態・リセット後・セッション完了直後） |
| `"running"` | カウントダウン中 |
| `"paused"` | 一時停止中 |

---

## タイマー状態オブジェクト

`PomodoroTimer.to_dict()` が返す辞書。API のタイマー系エンドポイントすべてで共通して使用する。

```json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `mode` | `string` | `TimerMode` の値（`"work"` または `"break"`） |
| `state` | `string` | `TimerState` の値（`"idle"`, `"running"`, `"paused"`） |
| `remaining_seconds` | `integer` | 現在の残り時間（秒）。`running` 状態では `clock_fn` からリアルタイム計算、それ以外は保存値を返す |
| `total_duration` | `integer` | 現在モードの合計時間（秒）。`work` = 1500、`break` = 300 |

---

## 統計レコード（stats.json の各要素）

`JsonStatsRepository` が `stats.json` に保存するセッション記録の形式。

```json
{
  "date": "2026-06-09",
  "duration_seconds": 1500,
  "mode": "work"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `date` | `string` | セッション日付（ISO 8601形式: `YYYY-MM-DD`） |
| `duration_seconds` | `integer` | セッションの経過時間（秒） |
| `mode` | `string` | セッションモード（`"work"` または `"break"`） |

`stats.json` はレコードの配列として保存される:

```json
[
  { "date": "2026-06-09", "duration_seconds": 1500, "mode": "work" },
  { "date": "2026-06-09", "duration_seconds": 300,  "mode": "break" }
]
```

---

## 統計レスポンスオブジェクト

`StatsService.get_today_stats()` が返す辞書。`GET /api/stats` エンドポイントで使用する。

```json
{
  "completed": 3,
  "focus_seconds": 4500,
  "focus_label": "1時間15分"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `completed` | `integer` | 本日完了した作業セッション数（`mode == "work"` のレコードのみカウント） |
| `focus_seconds` | `integer` | 本日の合計集中時間（秒）（作業セッションのみ集計） |
| `focus_label` | `string` | 集中時間の表示用ラベル |

`focus_label` の計算規則:

- `focus_minutes < 60` の場合: `"XX分"`（例: `"25分"`）
- `focus_minutes >= 60` の場合: `"X時間XX分"`（例: `"1時間15分"`）
- ちょうど1時間の場合: `"1時間0分"`

---

## タイマー定数

| 定数名 | 値 | 説明 |
|---|---|---|
| `WORK_DURATION` | `1500`（25分） | 作業セッションの合計時間（秒） |
| `BREAK_DURATION` | `300`（5分） | 休憩セッションの合計時間（秒） |
