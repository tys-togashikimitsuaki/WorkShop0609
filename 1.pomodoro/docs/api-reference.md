# REST API リファレンス

ポモドーロタイマーが提供する REST API エンドポイントの仕様です。

---

## ページ

### `GET /`

タイマーの UI ページを返します。

**レスポンス:** `200 OK` — `text/html`（`templates/index.html` をレンダリング）

---

## タイマー API

タイマーの状態オブジェクト（以下「タイマーレスポンス」）はすべてのタイマー API で共通して返されます。

**タイマーレスポンス形式:**

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
| `mode` | `"work"` \| `"break"` | 現在のモード |
| `state` | `"idle"` \| `"running"` \| `"paused"` | 現在の状態 |
| `remaining_seconds` | `integer` | 残り時間（秒） |
| `total_duration` | `integer` | 現在モードの全体時間（秒）。作業: 1500、休憩: 300 |

---

### `GET /api/state`

現在のタイマー状態を取得します。

**レスポンス:** `200 OK` — タイマーレスポンス

**例:**

```bash
curl http://localhost:5000/api/state
```

```json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

---

### `POST /api/start`

タイマーを開始または再開します。すでに実行中の場合は何もせず現在の状態を返します。

**リクエストボディ:** なし

**レスポンス:** `200 OK` — タイマーレスポンス（`state: "running"`）

**例:**

```bash
curl -X POST http://localhost:5000/api/start
```

```json
{
  "mode": "work",
  "state": "running",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

---

### `POST /api/pause`

実行中のタイマーを一時停止します。実行中でない場合は何もしません。

**リクエストボディ:** なし

**レスポンス:** `200 OK` — タイマーレスポンス（`state: "paused"` または変化なし）

**例:**

```bash
curl -X POST http://localhost:5000/api/pause
```

```json
{
  "mode": "work",
  "state": "paused",
  "remaining_seconds": 1490,
  "total_duration": 1500
}
```

---

### `POST /api/reset`

タイマーを初期状態にリセットします。モードが `work` に戻り、残り時間が 1500 秒に戻ります。

**リクエストボディ:** なし

**レスポンス:** `200 OK` — タイマーレスポンス（`state: "idle"`, `mode: "work"`, `remaining_seconds: 1500`）

**例:**

```bash
curl -X POST http://localhost:5000/api/reset
```

```json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

---

### `POST /api/complete`

現在のセッションを完了し、次のモードへ切り替えます。作業セッション完了時のみ統計を記録します。

**リクエストボディ:** `application/json`（省略可）

```json
{
  "duration_seconds": 1500
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `duration_seconds` | `integer` | 実際の作業時間（秒）。0 または省略時は統計を記録しません。 |

**挙動:**
- 現在のモードが `work` かつ `duration_seconds > 0` の場合、統計にワークセッションを記録します。
- モードを `work → break` または `break → work` に切り替えます。
- 状態を `idle` に設定します。

**レスポンス:** `200 OK` — タイマーレスポンス（切り替え後のモード）

**例（作業完了）:**

```bash
curl -X POST http://localhost:5000/api/complete \
  -H "Content-Type: application/json" \
  -d '{"duration_seconds": 1500}'
```

```json
{
  "mode": "break",
  "state": "idle",
  "remaining_seconds": 300,
  "total_duration": 300
}
```

---

## 統計 API

### `GET /api/stats`

今日のワークセッション統計を取得します。

**レスポンス:** `200 OK`

```json
{
  "completed": 3,
  "focus_seconds": 4500,
  "focus_label": "1時間15分"
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `completed` | `integer` | 今日完了した作業セッション数 |
| `focus_seconds` | `integer` | 今日の累計作業時間（秒） |
| `focus_label` | `string` | 集中時間の表示文字列。60分未満は「N分」、60分以上は「N時間M分」 |

**例:**

```bash
curl http://localhost:5000/api/stats
```

```json
{
  "completed": 2,
  "focus_seconds": 3000,
  "focus_label": "50分"
}
```
