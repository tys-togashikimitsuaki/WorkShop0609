"""
StatsService のユニットテスト

InMemoryStatsRepository を注入することで、ファイルI/O 不要でテストする。
"""

import pytest
from datetime import date
from pomodoro.stats import InMemoryStatsRepository, StatsService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    repo = InMemoryStatsRepository()
    return StatsService(repo)


# ---------------------------------------------------------------------------
# record_work_session
# ---------------------------------------------------------------------------

class TestRecordWorkSession:
    def test_completed_count_increments(self, service):
        service.record_work_session(1500)
        stats = service.get_today_stats()
        assert stats["completed"] == 1

    def test_multiple_sessions_accumulate(self, service):
        service.record_work_session(1500)
        service.record_work_session(1500)
        stats = service.get_today_stats()
        assert stats["completed"] == 2

    def test_focus_seconds_accumulates(self, service):
        service.record_work_session(1500)
        service.record_work_session(900)
        stats = service.get_today_stats()
        assert stats["focus_seconds"] == 2400


# ---------------------------------------------------------------------------
# record_break_session
# ---------------------------------------------------------------------------

class TestRecordBreakSession:
    def test_break_does_not_count_as_completed(self, service):
        service.record_break_session(300)
        stats = service.get_today_stats()
        assert stats["completed"] == 0

    def test_break_does_not_add_to_focus_seconds(self, service):
        service.record_break_session(300)
        stats = service.get_today_stats()
        assert stats["focus_seconds"] == 0


# ---------------------------------------------------------------------------
# focus_label
# ---------------------------------------------------------------------------

class TestFocusLabel:
    def test_label_minutes_only(self, service):
        service.record_work_session(25 * 60)  # 25分
        stats = service.get_today_stats()
        assert stats["focus_label"] == "25分"

    def test_label_hours_and_minutes(self, service):
        # 1時間40分 = 100分 = 6000秒
        service.record_work_session(6000)
        stats = service.get_today_stats()
        assert stats["focus_label"] == "1時間40分"

    def test_label_exact_one_hour(self, service):
        service.record_work_session(3600)
        stats = service.get_today_stats()
        assert stats["focus_label"] == "1時間0分"

    def test_label_zero_minutes(self, service):
        stats = service.get_today_stats()
        assert stats["focus_label"] == "0分"


# ---------------------------------------------------------------------------
# InMemoryStatsRepository の日付分離
# ---------------------------------------------------------------------------

class TestDateIsolation:
    def test_different_dates_are_isolated(self):
        from datetime import date
        repo = InMemoryStatsRepository()
        repo.record_session(date(2026, 1, 1), 1500, "work")
        repo.record_session(date(2026, 1, 2), 1500, "work")
        stats_day1 = repo.get_stats(date(2026, 1, 1))
        stats_day2 = repo.get_stats(date(2026, 1, 2))
        assert stats_day1["completed"] == 1
        assert stats_day2["completed"] == 1

    def test_no_cross_date_contamination(self):
        repo = InMemoryStatsRepository()
        repo.record_session(date(2026, 1, 1), 1500, "work")
        stats = repo.get_stats(date(2026, 1, 2))
        assert stats["completed"] == 0
        assert stats["focus_seconds"] == 0


class TestGamification:
    def test_xp_and_level(self):
        repo = InMemoryStatsRepository()
        for _ in range(6):
            repo.record_session(date(2026, 1, 3), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 3))
        stats = service.get_today_stats()
        assert stats["gamification"]["xp"] == 600
        assert stats["gamification"]["level"] == 2

    def test_xp_to_next_level_is_zero_on_exact_level_up(self):
        repo = InMemoryStatsRepository()
        for _ in range(5):
            repo.record_session(date(2026, 1, 3), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 3))
        stats = service.get_today_stats()
        assert stats["gamification"]["xp"] == 500
        assert stats["gamification"]["xp_to_next_level"] == 0

    def test_streak_counts_consecutive_days(self):
        repo = InMemoryStatsRepository()
        repo.record_session(date(2026, 1, 1), 1500, "work")
        repo.record_session(date(2026, 1, 2), 1500, "work")
        repo.record_session(date(2026, 1, 3), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 3))
        stats = service.get_today_stats()
        assert stats["gamification"]["streak_days"] == 3

    def test_weekly_and_monthly_aggregates(self):
        repo = InMemoryStatsRepository()
        for day in range(1, 8):
            repo.record_session(date(2026, 1, day), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 7))
        stats = service.get_today_stats()
        assert stats["gamification"]["weekly"]["sessions_completed"] == 7
        assert stats["gamification"]["monthly"]["sessions_completed"] == 7

    def test_completion_rate_is_capped_at_100_percent(self):
        repo = InMemoryStatsRepository()
        for _ in range(15):
            repo.record_session(date(2026, 1, 7), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 7))
        stats = service.get_today_stats()
        assert stats["gamification"]["weekly"]["completion_rate"] == 100.0

    def test_badge_progress_reflects_streak_and_weekly_sessions(self):
        repo = InMemoryStatsRepository()
        for day in range(1, 4):
            repo.record_session(date(2026, 1, day), 1500, "work")
        for _ in range(7):
            repo.record_session(date(2026, 1, 3), 1500, "work")
        service = StatsService(repo, today_fn=lambda: date(2026, 1, 3))
        stats = service.get_today_stats()
        badges = {b["id"]: b for b in stats["gamification"]["badges"]}
        assert badges["streak_3"]["earned"] is True
        assert badges["weekly_10"]["earned"] is True
