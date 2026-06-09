"""
StatsService のユニットテスト

InMemoryStatsRepository を注入することで、ファイルI/O 不要でテストする。
"""

import pytest
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
        from datetime import date
        repo = InMemoryStatsRepository()
        repo.record_session(date(2026, 1, 1), 1500, "work")
        stats = repo.get_stats(date(2026, 1, 2))
        assert stats["completed"] == 0
        assert stats["focus_seconds"] == 0
