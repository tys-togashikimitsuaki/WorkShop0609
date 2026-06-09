# API リファレンス

ポモドーロタイマー REST API の仕様書です。

---

## 共通仕様

- **ベース URL**: `/`
- **リクエスト形式**: `application/json`（POSTボディが必要な場合）
- **レスポンス形式**: `application/json`

---

## タイマー API

### GET /api/state

現在のタイマー状態を取得します。

**レスポンス例**

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
| `mode` | `"work"` \| `"break"` | 現在のモード（作業 / 休憩） |
| `state` | `"idle"` \| `"running"` \| `"paused"` | タイマーの状態 |
| `remaining_seconds` | `integer` | 残り秒数 |
| `total_duration` | `integer` | 現在モードの総秒数 |

---

### POST /api/start

タイマーを開始または再開します。

**リクエストボディ**: 不要

**レスポンス**: `GET /api/state` と同じ形式

**動作**
- `state` が `idle` または `paused` の場合、`running` に遷移する
- すでに `running` の場合は変化なし（冪等）

---

### POST /api/pause

タイマーを一時停止します。

**リクエストボディ**: 不要

**レスポンス**: `GET /api/state` と同じ形式

**動作**
- `state` が `running` の場合、残り秒数を保持したまま `paused` に遷移する
- `running` 以外の場合は変化なし

---

### POST /api/reset

タイマーを初期状態にリセットします。

**リクエストボディ**: 不要

**レスポンス**: `GET /api/state` と同じ形式

**動作**
- `mode` を `work` に戻す
- `state` を `idle` に戻す
- `remaining_seconds` を作業時間の秒数に戻す

---

### POST /api/complete

セッション完了を通知し、次のモードへ切り替えます。  
作業セッション（`mode == "work"`）かつ `duration_seconds > 0` の場合のみ統計に記録されます。

**リクエストボディ**

```json
{
  "duration_seconds": 1500
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `duration_seconds` | `integer` | 任意 | 実際に経過した秒数（省略時は 0 として扱われる） |

**レスポンス**: `GET /api/state` と同じ形式（次のモードに切り替わった状態）

**動作**
- `work` → `break` モードに切り替え
- `break` → `work` モードに切り替え
- `state` は `idle` になる
- 統計は `work` モードかつ `duration_seconds > 0` のときのみ記録

---

## 設定 API

### GET /api/settings

現在の設定と選択可能なオプションを取得します。

**レスポンス例**

```json
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
```

---

### POST /api/settings

作業時間・休憩時間を更新し、タイマーをリセットします。

**リクエストボディ**

```json
{
  "work_duration_minutes": 35,
  "break_duration_minutes": 10
}
```

| フィールド | 型 | 必須 | 許可値 |
|---|---|---|---|
| `work_duration_minutes` | `integer` | 必須 | `15`, `25`, `35`, `45` |
| `break_duration_minutes` | `integer` | 必須 | `5`, `10`, `15` |

**レスポンス例（200 OK）**

```json
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
```

**エラーレスポンス（400 Bad Request）**

許可値以外の値を指定した場合:

```json
{
  "error": "invalid settings"
}
```

---

## 統計 API

### GET /api/stats

今日の作業統計を取得します。

**レスポンス例**

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
| `focus_seconds` | `integer` | 今日の合計集中秒数 |
| `focus_label` | `string` | 集中時間の表示文字列（例: `"25分"`, `"1時間40分"`） |

**`focus_label` の形式**
- 60分未満: `"{分数}分"`（例: `"25分"`）
- 60分以上: `"{時間}時間{分}分"`（例: `"1時間40分"`）

---

## ページ

### GET /

ポモドーロタイマーのメインページを返します。  
HTML レスポンス（`text/html`）。
