# API リファレンス

ポモドーロタイマーアプリのREST APIリファレンスです。

---

## 共通仕様

- ベースURL: `http://localhost:5000`
- リクエスト/レスポンス形式: `application/json`
- すべてのAPIエンドポイントは成功時に HTTP `200` を返す

---

## ページ

### `GET /`

HTMLページを返す。

**レスポンス**: `text/html` — `templates/index.html` のレンダリング結果

---

## タイマー API

### `GET /api/state`

現在のタイマー状態を取得する。

**レスポンス例:**

```json
{
  "mode": "work",
  "state": "idle",
  "remaining_seconds": 1500,
  "total_duration": 1500
}
```

**フィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `mode` | `"work"` \| `"break"` | 現在のモード（作業/休憩） |
| `state` | `"idle"` \| `"running"` \| `"paused"` | タイマーの状態 |
| `remaining_seconds` | `integer` | 残り時間（秒） |
| `total_duration` | `integer` | 現在モードの合計時間（秒）。`work` = 1500、`break` = 300 |

---

### `POST /api/start`

タイマーを開始または一時停止から再開する。既に `running` の場合は何もしない（冪等）。

**リクエストボディ:** 不要

**レスポンス:** タイマー状態オブジェクト（`GET /api/state` と同形式）

**レスポンス例:**

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

実行中のタイマーを一時停止する。`running` 以外の状態では何もしない。

**リクエストボディ:** 不要

**レスポンス:** タイマー状態オブジェクト

**レスポンス例:**

```json
{
  "mode": "work",
  "state": "paused",
  "remaining_seconds": 1440,
  "total_duration": 1500
}
```

---

### `POST /api/reset`

タイマーを初期状態（`work` モード、`idle` 状態、残り1500秒）にリセットする。

**リクエストボディ:** 不要

**レスポンス:** タイマー状態オブジェクト

**レスポンス例:**

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

クライアントからセッション完了を通知する。`work` モードかつ `duration_seconds > 0` の場合のみ統計を記録する。セッション完了後は次のモード（`work` → `break`、`break` → `work`）に切り替える。

**リクエストボディ（省略可）:**

```json
{
  "duration_seconds": 1500
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `duration_seconds` | `integer` | 実際に経過したセッション時間（秒）。省略または `0` の場合は統計を記録しない |

**レスポンス:** 次のモードに切り替わったタイマー状態オブジェクト

**レスポンス例（`work` セッション完了後）:**

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

本日の作業統計を取得する。

**レスポンス例:**

```json
{
  "completed": 3,
  "focus_seconds": 4500,
  "focus_label": "1時間15分"
}
```

**フィールド:**

| フィールド | 型 | 説明 |
|---|---|---|
| `completed` | `integer` | 本日完了した作業セッション数 |
| `focus_seconds` | `integer` | 本日の合計集中時間（秒） |
| `focus_label` | `string` | 集中時間の表示用ラベル。60分未満は `"XX分"`、60分以上は `"X時間XX分"` |
