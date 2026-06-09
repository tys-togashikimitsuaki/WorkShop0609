# API リファレンス

ポモドーロタイマーの REST API エンドポイント一覧です。

---

## 共通仕様

- ベース URL: `http://<host>/`
- リクエスト / レスポンスのボディ形式: `application/json`
- すべてのタイマー系エンドポイントはタイマーの現在状態を返す

---

## ページ

### `GET /`

メインページ（`index.html`）を返す。

**レスポンス**: HTML（200 OK）

---

## タイマー API

### タイマー状態オブジェクト

タイマー系エンドポイントはすべて以下の JSON オブジェクトを返す。

| フィールド | 型 | 説明 |
|---|---|---|
| `mode` | `"work"` \| `"break"` | 現在のモード（作業 / 休憩） |
| `state` | `"idle"` \| `"running"` \| `"paused"` | タイマーの状態 |
| `remaining_seconds` | `integer` | 残り時間（秒） |
| `total_duration` | `integer` | 現在モードの合計時間（秒） |

---

### `GET /api/state`

タイマーの現在状態を取得する。

**レスポンス例（200 OK）:**

````json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
````

---

### `POST /api/start`

タイマーを開始または再開する。すでに `running` の場合は何もしない（冪等）。

**レスポンス例（200 OK）:**

````json
{
  "mode": "work",
  "state": "running",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
````

---

### `POST /api/pause`

実行中のタイマーを一時停止する。`running` 以外の状態では何もしない。

**レスポンス例（200 OK）:**

````json
{
  "mode": "work",
  "state": "paused",
  "remaining_seconds": 1440,
  "total_duration": 1500
}
````

---

### `POST /api/reset`

タイマーを初期状態にリセットする。モードを `work`、状態を `idle` に戻し、残り時間を作業時間の全長に戻す。

**レスポンス例（200 OK）:**

````json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
````

---

### `POST /api/complete`

クライアントがセッション完了を通知する。  
`mode` が `work` かつ `duration_seconds > 0` の場合、統計に作業セッションを記録する。  
完了後は次のモード（work → break、break → work）に切り替わり、状態は `idle` になる。

**リクエストボディ（省略可）:**

| フィールド | 型 | 説明 |
|---|---|---|
| `duration_seconds` | `integer` | 実際に経過した秒数（0 または省略時は統計に記録しない） |

**リクエスト例:**

````json
{ "duration_seconds": 1500 }
````

**レスポンス例（200 OK）— 作業完了後:**

````json
{
  "mode": "break",
  "state": "idle",
  "remaining_seconds": 300,
  "total_duration": 300
}
````

---

## 設定 API

### `GET /api/settings`

現在の設定と選択可能な値の一覧を返す。

**レスポンス例（200 OK）:**

````json
{
  "settings": {
    "work_duration_minutes": 25,
    "break_duration_minutes": 5
  },
  "options": {
    "work_duration_minutes": [15, 25, 35, 45],
    "break_duration_minutes": [5, 10, 15]
  }
}
````

---

### `POST /api/settings`

作業時間・休憩時間を更新し、タイマーをリセットする。  
`work_duration_minutes` が `[15, 25, 35, 45]` 以外、または `break_duration_minutes` が `[5, 10, 15]` 以外の場合は `400` を返す。

**リクエストボディ:**

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `work_duration_minutes` | `integer` | ✓ | 作業時間（分）: 15 / 25 / 35 / 45 |
| `break_duration_minutes` | `integer` | ✓ | 休憩時間（分）: 5 / 10 / 15 |

**リクエスト例:**

````json
{
  "work_duration_minutes": 35,
  "break_duration_minutes": 10
}
````

**レスポンス例（200 OK）:**

````json
{
  "timer": {
    "mode": "work",
    "state": "idle",
    "remaining_seconds": 2100,
    "total_duration": 2100
  },
  "settings": {
    "work_duration_minutes": 35,
    "break_duration_minutes": 10
  }
}
````

**エラーレスポンス例（400 Bad Request）:**

````json
{ "error": "invalid settings" }
````

---

## 統計 API

### `GET /api/stats`

今日の作業統計とゲーミフィケーション情報を返す。

**レスポンスフィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `completed` | `integer` | 今日完了した作業セッション数 |
| `focus_seconds` | `integer` | 今日の合計集中時間（秒） |
| `focus_label` | `string` | 集中時間の表示文字列（例: `"25分"`, `"1時間40分"`） |
| `gamification` | `object` | ゲーミフィケーション情報（下表参照） |

**`gamification` フィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `xp` | `integer` | 累計 XP（作業セッション 1 回 = 100 XP） |
| `level` | `integer` | 現在のレベル（500 XP ごとにレベルアップ） |
| `xp_in_level` | `integer` | 現レベル内の XP |
| `xp_to_next_level` | `integer` | 次レベルまでの残り XP |
| `streak_days` | `integer` | 連続作業日数 |
| `badges` | `array` | バッジ一覧（下表参照） |
| `earned_badges` | `integer` | 獲得済みバッジ数 |
| `weekly` | `object` | 週間統計 |
| `monthly` | `object` | 月間統計 |

**`badges` 配列の各要素:**

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | `string` | バッジ ID (`"streak_3"`, `"weekly_10"`) |
| `name` | `string` | バッジ名 |
| `description` | `string` | バッジ説明 |
| `earned` | `boolean` | 獲得済みかどうか |
| `progress` | `integer` | 現在の進捗 |
| `target` | `integer` | 達成目標値 |

**`weekly` / `monthly` フィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `sessions_completed` | `integer` | 期間内の完了セッション数 |
| `focus_seconds` | `integer` | 期間内の合計集中時間（秒） |
| `completion_rate` | `float` | 目標達成率（%）、最大 100.0 |
| `average_focus_seconds` | `integer` | 1 セッションあたりの平均集中時間（秒） |

> 週間目標: 10 セッション / 月間目標: 40 セッション

**レスポンス例（200 OK）:**

````json
{
  "completed": 2,
  "focus_seconds": 3000,
  "focus_label": "50分",
  "gamification": {
    "xp": 200,
    "level": 1,
    "xp_in_level": 200,
    "xp_to_next_level": 300,
    "streak_days": 1,
    "badges": [
      {
        "id": "streak_3",
        "name": "3日連続",
        "description": "3日連続で作業セッションを完了",
        "earned": false,
        "progress": 1,
        "target": 3
      },
      {
        "id": "weekly_10",
        "name": "週10回",
        "description": "1週間で10回の作業セッションを完了",
        "earned": false,
        "progress": 2,
        "target": 10
      }
    ],
    "earned_badges": 0,
    "weekly": {
      "sessions_completed": 2,
      "focus_seconds": 3000,
      "completion_rate": 20.0,
      "average_focus_seconds": 1500
    },
    "monthly": {
      "sessions_completed": 2,
      "focus_seconds": 3000,
      "completion_rate": 5.0,
      "average_focus_seconds": 1500
    }
  }
}
````
