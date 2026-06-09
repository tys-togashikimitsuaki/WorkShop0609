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
from typing import Callable, Protocol


# ---------------------------------------------------------------------------
# Repository Protocol（抽象インターフェース）
# ---------------------------------------------------------------------------

class StatsRepository(Protocol):
    def record_session(self, session_date: date, duration_seconds: int, mode: str) -> None:
        ...

    def get_stats(self, session_date: date) -> dict:
        ...

    def get_all_records(self) -> list[dict]:
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

    def get_all_records(self) -> list[dict]:
        return list(self._records)


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

    def get_all_records(self) -> list[dict]:
        return self._load()


# ---------------------------------------------------------------------------
# StatsService
# ---------------------------------------------------------------------------

class StatsService:
    """統計サービス。リポジトリを注入して利用する。"""

    XP_PER_WORK_SESSION = 100
    LEVEL_STEP_XP = 500
    WEEKLY_TARGET_SESSIONS = 10
    MONTHLY_TARGET_SESSIONS = 40

    def __init__(self, repository: StatsRepository, today_fn: Callable[[], date] = date.today) -> None:
        self._repo = repository
        self._today_fn = today_fn

    def record_work_session(self, duration_seconds: int) -> None:
        self._repo.record_session(self._today_fn(), duration_seconds, "work")

    def record_break_session(self, duration_seconds: int) -> None:
        self._repo.record_session(self._today_fn(), duration_seconds, "break")

    def get_today_stats(self) -> dict:
        today = self._today_fn()
        stats = self._repo.get_stats(today)
        focus_minutes = stats["focus_seconds"] // 60
        focus_hours = focus_minutes // 60
        remaining_minutes = focus_minutes % 60
        records = self._repo.get_all_records()
        work_records = [r for r in records if r["mode"] == "work"]
        work_dates = sorted(date.fromisoformat(r["date"]) for r in work_records)
        total_completed = len(work_records)
        total_focus_seconds = sum(r["duration_seconds"] for r in work_records)
        xp = total_completed * self.XP_PER_WORK_SESSION
        level = (xp // self.LEVEL_STEP_XP) + 1
        xp_in_level = xp % self.LEVEL_STEP_XP

        streak_days = 0
        if today in set(work_dates):
            check_day = today
            work_date_set = set(work_dates)
            while check_day in work_date_set:
                streak_days += 1
                check_day = date.fromordinal(check_day.toordinal() - 1)

        def _range_work_stats(days: int) -> tuple[int, int]:
            start_ordinal = today.toordinal() - days + 1
            range_records = [
                r for r in work_records
                if date.fromisoformat(r["date"]).toordinal() >= start_ordinal
            ]
            sessions = len(range_records)
            focus_sum = sum(r["duration_seconds"] for r in range_records)
            return sessions, focus_sum

        weekly_completed, weekly_focus_seconds = _range_work_stats(7)
        monthly_completed, monthly_focus_seconds = _range_work_stats(30)

        badges = [
            {
                "id": "streak_3",
                "name": "3日連続",
                "description": "3日連続で作業セッションを完了",
                "earned": streak_days >= 3,
                "progress": min(streak_days, 3),
                "target": 3,
            },
            {
                "id": "weekly_10",
                "name": "週10回",
                "description": "1週間で10回の作業セッションを完了",
                "earned": weekly_completed >= self.WEEKLY_TARGET_SESSIONS,
                "progress": min(weekly_completed, self.WEEKLY_TARGET_SESSIONS),
                "target": self.WEEKLY_TARGET_SESSIONS,
            },
        ]

        return {
            "completed": stats["completed"],
            "focus_seconds": stats["focus_seconds"],
            "focus_label": f"{focus_hours}時間{remaining_minutes}分" if focus_hours > 0 else f"{focus_minutes}分",
            "gamification": {
                "xp": xp,
                "level": level,
                "xp_in_level": xp_in_level,
                "xp_to_next_level": self.LEVEL_STEP_XP - xp_in_level,
                "streak_days": streak_days,
                "badges": badges,
                "earned_badges": len([b for b in badges if b["earned"]]),
                "weekly": {
                    "sessions_completed": weekly_completed,
                    "focus_seconds": weekly_focus_seconds,
                    "completion_rate": min(100.0, round((weekly_completed / self.WEEKLY_TARGET_SESSIONS) * 100, 1)),
                    "average_focus_seconds": weekly_focus_seconds // weekly_completed if weekly_completed > 0 else 0,
                },
                "monthly": {
                    "sessions_completed": monthly_completed,
                    "focus_seconds": monthly_focus_seconds,
                    "completion_rate": min(100.0, round((monthly_completed / self.MONTHLY_TARGET_SESSIONS) * 100, 1)),
                    "average_focus_seconds": monthly_focus_seconds // monthly_completed if monthly_completed > 0 else 0,
                },
            },
        }
