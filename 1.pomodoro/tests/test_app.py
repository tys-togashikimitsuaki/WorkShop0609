"""
Flask ルート（app.py）のユニットテスト

create_app() ファクトリに PomodoroTimer / StatsService のテスト用インスタンスを
注入することで、HTTP レイヤーをドメインモデルと独立してテストする。
"""

import json
import pytest

from app import create_app
from pomodoro.timer import PomodoroTimer, TimerMode, TimerState, WORK_DURATION, BREAK_DURATION
from pomodoro.stats import InMemoryStatsRepository, StatsService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def timer():
    """各テストに新鮮な PomodoroTimer を提供する（clock_fn 固定）。"""
    return PomodoroTimer(clock_fn=lambda: 0.0)


@pytest.fixture
def stats_service():
    """各テストに InMemoryStatsRepository ベースの StatsService を提供する。"""
    return StatsService(InMemoryStatsRepository())


@pytest.fixture
def client(timer, stats_service):
    """テスト用 Flask クライアント。timer と stats_service は注入済み。"""
    app = create_app(timer=timer, stats_service=stats_service)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestIndexPage:
    def test_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_returns_html(self, client):
        res = client.get("/")
        assert "\u30dd\u30e2\u30c9\u30fc\u30ed\u30bf\u30a4\u30de\u30fc" in res.data.decode("utf-8")


# ---------------------------------------------------------------------------
# GET /api/state
# ---------------------------------------------------------------------------

class TestApiState:
    def test_returns_200(self, client):
        res = client.get("/api/state")
        assert res.status_code == 200

    def test_initial_state_is_idle_work(self, client):
        data = client.get("/api/state").get_json()
        assert data["state"] == "idle"
        assert data["mode"] == "work"
        assert data["remaining_seconds"] == WORK_DURATION
        assert data["total_duration"] == WORK_DURATION

    def test_response_contains_required_keys(self, client):
        data = client.get("/api/state").get_json()
        assert set(data.keys()) == {"state", "mode", "remaining_seconds", "total_duration"}


# ---------------------------------------------------------------------------
# POST /api/start
# ---------------------------------------------------------------------------

class TestApiStart:
    def test_returns_200(self, client):
        res = client.post("/api/start")
        assert res.status_code == 200

    def test_state_becomes_running(self, client):
        data = client.post("/api/start").get_json()
        assert data["state"] == "running"

    def test_mode_unchanged_after_start(self, client):
        data = client.post("/api/start").get_json()
        assert data["mode"] == "work"

    def test_start_twice_is_idempotent(self, client):
        client.post("/api/start")
        data = client.post("/api/start").get_json()
        assert data["state"] == "running"


# ---------------------------------------------------------------------------
# POST /api/pause
# ---------------------------------------------------------------------------

class TestApiPause:
    def test_returns_200(self, client):
        client.post("/api/start")
        res = client.post("/api/pause")
        assert res.status_code == 200

    def test_state_becomes_paused_after_start_then_pause(self, client):
        client.post("/api/start")
        data = client.post("/api/pause").get_json()
        assert data["state"] == "paused"

    def test_pause_without_start_remains_idle(self, client):
        data = client.post("/api/pause").get_json()
        assert data["state"] == "idle"


# ---------------------------------------------------------------------------
# POST /api/reset
# ---------------------------------------------------------------------------

class TestApiReset:
    def test_returns_200(self, client):
        res = client.post("/api/reset")
        assert res.status_code == 200

    def test_reset_from_running_returns_to_idle(self, client):
        client.post("/api/start")
        data = client.post("/api/reset").get_json()
        assert data["state"] == "idle"

    def test_reset_restores_work_mode(self, client):
        # BREAK モードに進めてからリセット
        client.post("/api/complete", json={"duration_seconds": 1500})
        data = client.post("/api/reset").get_json()
        assert data["mode"] == "work"

    def test_reset_restores_full_duration(self, client):
        client.post("/api/start")
        data = client.post("/api/reset").get_json()
        assert data["remaining_seconds"] == WORK_DURATION


# ---------------------------------------------------------------------------
# POST /api/complete
# ---------------------------------------------------------------------------

class TestApiComplete:
    def test_returns_200(self, client):
        res = client.post("/api/complete", json={"duration_seconds": 1500})
        assert res.status_code == 200

    def test_work_session_switches_to_break(self, client):
        data = client.post("/api/complete", json={"duration_seconds": 1500}).get_json()
        assert data["mode"] == "break"
        assert data["remaining_seconds"] == BREAK_DURATION

    def test_break_session_switches_to_work(self, client):
        client.post("/api/complete", json={"duration_seconds": 1500})  # → BREAK
        data = client.post("/api/complete", json={"duration_seconds": 0}).get_json()
        assert data["mode"] == "work"
        assert data["remaining_seconds"] == WORK_DURATION

    def test_complete_sets_state_to_idle(self, client):
        client.post("/api/start")
        data = client.post("/api/complete", json={"duration_seconds": 1500}).get_json()
        assert data["state"] == "idle"

    def test_work_session_records_stats(self, client, stats_service):
        client.post("/api/complete", json={"duration_seconds": 1500})
        stats = stats_service.get_today_stats()
        assert stats["completed"] == 1
        assert stats["focus_seconds"] == 1500

    def test_break_session_does_not_record_stats(self, client, stats_service):
        # BREAK モードへ切り替え
        client.post("/api/complete", json={"duration_seconds": 1500})
        # BREAK セッション完了
        client.post("/api/complete", json={"duration_seconds": 300})
        stats = stats_service.get_today_stats()
        assert stats["completed"] == 1  # WORK 分のみカウント

    def test_complete_without_body_does_not_error(self, client):
        res = client.post("/api/complete")
        assert res.status_code == 200

    def test_complete_with_zero_duration_does_not_record(self, client, stats_service):
        client.post("/api/complete", json={"duration_seconds": 0})
        stats = stats_service.get_today_stats()
        assert stats["completed"] == 0


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------

class TestApiStats:
    def test_returns_200(self, client):
        res = client.get("/api/stats")
        assert res.status_code == 200

    def test_initial_stats_are_zero(self, client):
        data = client.get("/api/stats").get_json()
        assert data["completed"] == 0
        assert data["focus_seconds"] == 0

    def test_stats_response_contains_required_keys(self, client):
        data = client.get("/api/stats").get_json()
        assert set(data.keys()) == {"completed", "focus_seconds", "focus_label", "gamification"}

    def test_stats_update_after_complete(self, client):
        client.post("/api/complete", json={"duration_seconds": 1500})
        data = client.get("/api/stats").get_json()
        assert data["completed"] == 1
        assert data["focus_seconds"] == 1500
        assert data["focus_label"] == "25分"

    def test_stats_include_gamification_fields(self, client):
        data = client.get("/api/stats").get_json()
        gamification = data["gamification"]
        assert set(gamification.keys()) == {
            "xp",
            "level",
            "xp_in_level",
            "xp_to_next_level",
            "streak_days",
            "badges",
            "earned_badges",
            "weekly",
            "monthly",
        }

    def test_stats_accumulate_across_multiple_sessions(self, client):
        client.post("/api/complete", json={"duration_seconds": 1500})  # WORK → BREAK
        client.post("/api/complete", json={"duration_seconds": 0})     # BREAK → WORK
        client.post("/api/complete", json={"duration_seconds": 1500})  # WORK → BREAK
        data = client.get("/api/stats").get_json()
        assert data["completed"] == 2
        assert data["focus_seconds"] == 3000

    def test_after_work_complete_break_duration_is_300(self, client):
        """作業完了後に休憩タイマー(5分=300秒)へ切り替わること。"""
        data = client.post("/api/complete", json={"duration_seconds": 1500}).get_json()
        assert data["mode"] == "break"
        assert data["remaining_seconds"] == 300
        assert data["total_duration"] == 300
