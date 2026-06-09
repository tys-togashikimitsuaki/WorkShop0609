"""
PomodoroTimer のユニットテスト

clock_fn に固定値/インクリメント関数を渡すことで、
実際の時間待機なしに時刻依存ロジックを検証する。
"""

import pytest
from pomodoro.timer import (
    ALLOWED_BREAK_DURATIONS_MINUTES,
    ALLOWED_WORK_DURATIONS_MINUTES,
    PomodoroTimer,
    TimerMode,
    TimerState,
    WORK_DURATION,
    BREAK_DURATION,
)


# ---------------------------------------------------------------------------
# 初期状態
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_mode_is_work(self):
        t = PomodoroTimer()
        assert t.mode == TimerMode.WORK

    def test_state_is_idle(self):
        t = PomodoroTimer()
        assert t.state == TimerState.IDLE

    def test_remaining_equals_work_duration(self):
        t = PomodoroTimer()
        assert t.remaining_seconds == WORK_DURATION

    def test_total_duration_is_work_duration(self):
        t = PomodoroTimer()
        assert t.total_duration == WORK_DURATION


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestStart:
    def test_start_changes_state_to_running(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.start()
        assert t.state == TimerState.RUNNING

    def test_start_twice_is_idempotent(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.start()
        t.start()
        assert t.state == TimerState.RUNNING

    def test_remaining_decreases_after_start(self):
        now = [0.0]
        t = PomodoroTimer(clock_fn=lambda: now[0])
        t.start()
        now[0] = 10.0
        assert t.remaining_seconds == WORK_DURATION - 10

    def test_remaining_does_not_go_below_zero(self):
        now = [0.0]
        t = PomodoroTimer(clock_fn=lambda: now[0])
        t.start()
        now[0] = WORK_DURATION + 100
        assert t.remaining_seconds == 0


# ---------------------------------------------------------------------------
# pause()
# ---------------------------------------------------------------------------

class TestPause:
    def test_pause_changes_state_to_paused(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.start()
        t.pause()
        assert t.state == TimerState.PAUSED

    def test_pause_preserves_remaining_seconds(self):
        now = [0.0]
        t = PomodoroTimer(clock_fn=lambda: now[0])
        t.start()
        now[0] = 60.0
        t.pause()
        assert t.remaining_seconds == WORK_DURATION - 60

    def test_pause_without_start_has_no_effect(self):
        t = PomodoroTimer()
        t.pause()
        assert t.state == TimerState.IDLE

    def test_resume_after_pause_continues_countdown(self):
        now = [0.0]
        t = PomodoroTimer(clock_fn=lambda: now[0])
        t.start()
        now[0] = 60.0
        t.pause()
        # 再開後さらに30秒経過
        now[0] = 90.0
        t.start()
        now[0] = 120.0
        assert t.remaining_seconds == WORK_DURATION - 60 - 30


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_returns_to_idle(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.start()
        t.reset()
        assert t.state == TimerState.IDLE

    def test_reset_restores_work_mode(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.complete_session()  # BREAK モードへ
        t.reset()
        assert t.mode == TimerMode.WORK

    def test_reset_restores_full_duration(self):
        now = [0.0]
        t = PomodoroTimer(clock_fn=lambda: now[0])
        t.start()
        now[0] = 300.0
        t.reset()
        assert t.remaining_seconds == WORK_DURATION


# ---------------------------------------------------------------------------
# complete_session()
# ---------------------------------------------------------------------------

class TestCompleteSession:
    def test_work_to_break(self):
        t = PomodoroTimer()
        next_mode = t.complete_session()
        assert next_mode == TimerMode.BREAK
        assert t.mode == TimerMode.BREAK

    def test_break_to_work(self):
        t = PomodoroTimer()
        t.complete_session()  # WORK → BREAK
        next_mode = t.complete_session()  # BREAK → WORK
        assert next_mode == TimerMode.WORK
        assert t.mode == TimerMode.WORK

    def test_state_becomes_idle_after_complete(self):
        t = PomodoroTimer(clock_fn=lambda: 0.0)
        t.start()
        t.complete_session()
        assert t.state == TimerState.IDLE

    def test_remaining_set_to_break_duration_after_work_complete(self):
        t = PomodoroTimer()
        t.complete_session()
        assert t.remaining_seconds == BREAK_DURATION

    def test_remaining_set_to_work_duration_after_break_complete(self):
        t = PomodoroTimer()
        t.complete_session()  # → BREAK
        t.complete_session()  # → WORK
        assert t.remaining_seconds == WORK_DURATION


# ---------------------------------------------------------------------------
# to_dict() / from_dict()
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_to_dict_contains_expected_keys(self):
        t = PomodoroTimer()
        d = t.to_dict()
        assert set(d.keys()) == {"mode", "state", "remaining_seconds", "total_duration"}

    def test_from_dict_restores_mode_and_remaining(self):
        data = {
            "mode": "break",
            "state": "idle",
            "remaining_seconds": 200,
        }
        t = PomodoroTimer.from_dict(data)
        assert t.mode == TimerMode.BREAK
        assert t.remaining_seconds == 200


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_set_durations_changes_work_and_break_lengths(self):
        t = PomodoroTimer()
        t.set_durations(work_duration_minutes=45, break_duration_minutes=15)
        assert t.settings == {
            "work_duration_minutes": 45,
            "break_duration_minutes": 15,
        }
        t.reset()
        assert t.remaining_seconds == 45 * 60
        t.complete_session()
        assert t.remaining_seconds == 15 * 60

    def test_set_durations_rejects_invalid_work_duration(self):
        t = PomodoroTimer()
        invalid = max(ALLOWED_WORK_DURATIONS_MINUTES) + 1
        with pytest.raises(ValueError):
            t.set_durations(work_duration_minutes=invalid, break_duration_minutes=5)

    def test_set_durations_rejects_invalid_break_duration(self):
        t = PomodoroTimer()
        invalid = max(ALLOWED_BREAK_DURATIONS_MINUTES) + 1
        with pytest.raises(ValueError):
            t.set_durations(work_duration_minutes=25, break_duration_minutes=invalid)
