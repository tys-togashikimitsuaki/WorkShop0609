"""
統計サービスとリポジトリ

Repository パターンにより、ストレージ実装をドメインロジックから分離している。
テスト時は InMemoryStatsRepository を注入することで、
ファイルI/O に依存せず StatsService をテストできる。
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Protocol


# ---------------------------------------------------------------------------
# Repository Protocol（抽象インターフェース）
# ---------------------------------------------------------------------------

class StatsRepository(Protocol):
    def record_session(self, session_date: date, duration_seconds: int, mode: str) -> None:
        ...

    def get_stats(self, session_date: date) -> dict:
        ...


# ---------------------------------------------------------------------------
# InMemoryStatsRepository — テスト用
# ---------------------------------------------------------------------------

class InMemoryStatsRepository:
    def __init__(self) -> None:
        self._records: list[dict] = []

    def record_session(self, session_date: date, duration_seconds: int, mode: str) -> None:
        self._records.append({
            "date": session_date.isoformat(),
            "duration_seconds": duration_seconds,
            "mode": mode,
        })

    def get_stats(self, session_date: date) -> dict:
        day_str = session_date.isoformat()
        work_sessions = [
            r for r in self._records
            if r["date"] == day_str and r["mode"] == "work"
        ]
        total_focus = sum(r["duration_seconds"] for r in work_sessions)
        return {
            "completed": len(work_sessions),
            "focus_seconds": total_focus,
        }


# ---------------------------------------------------------------------------
# JsonStatsRepository — ファイル永続化
# ---------------------------------------------------------------------------

class JsonStatsRepository:
    def __init__(self, filepath: str = "stats.json") -> None:
        self._filepath = filepath

    def _load(self) -> list[dict]:
        if not os.path.exists(self._filepath):
            return []
        with open(self._filepath, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, records: list[dict]) -> None:
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def record_session(self, session_date: date, duration_seconds: int, mode: str) -> None:
        records = self._load()
        records.append({
            "date": session_date.isoformat(),
            "duration_seconds": duration_seconds,
            "mode": mode,
        })
        self._save(records)

    def get_stats(self, session_date: date) -> dict:
        records = self._load()
        day_str = session_date.isoformat()
        work_sessions = [
            r for r in records
            if r["date"] == day_str and r["mode"] == "work"
        ]
        total_focus = sum(r["duration_seconds"] for r in work_sessions)
        return {
            "completed": len(work_sessions),
            "focus_seconds": total_focus,
        }


# ---------------------------------------------------------------------------
# StatsService
# ---------------------------------------------------------------------------

class StatsService:
    """統計サービス。リポジトリを注入して利用する。"""

    def __init__(self, repository: StatsRepository) -> None:
        self._repo = repository

    def record_work_session(self, duration_seconds: int) -> None:
        self._repo.record_session(date.today(), duration_seconds, "work")

    def record_break_session(self, duration_seconds: int) -> None:
        self._repo.record_session(date.today(), duration_seconds, "break")

    def get_today_stats(self) -> dict:
        stats = self._repo.get_stats(date.today())
        focus_minutes = stats["focus_seconds"] // 60
        focus_hours = focus_minutes // 60
        remaining_minutes = focus_minutes % 60
        return {
            "completed": stats["completed"],
            "focus_seconds": stats["focus_seconds"],
            "focus_label": f"{focus_hours}時間{remaining_minutes}分" if focus_hours > 0 else f"{focus_minutes}分",
        }
