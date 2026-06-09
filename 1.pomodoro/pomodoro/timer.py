"""
PomodoroTimer ドメインモデル

テスタビリティのため clock_fn を DI で受け取る設計にしている。
テスト時は clock_fn に固定値を返すラムダを渡すことで、
時刻依存のロジックを確定的にテストできる。
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable


class TimerMode(str, Enum):
    WORK = "work"
    BREAK = "break"


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


WORK_DURATION = 25 * 60   # 1500 秒
BREAK_DURATION = 5 * 60   # 300 秒
ALLOWED_WORK_DURATIONS_MINUTES = (15, 25, 35, 45)
ALLOWED_BREAK_DURATIONS_MINUTES = (5, 10, 15)


class PomodoroTimer:
    """ポモドーロタイマーのドメインモデル。

    Args:
        clock_fn: 現在時刻を秒で返す callable（デフォルト: time.time）。
                  テスト時には固定値やモックを渡すことで時刻制御が可能。
    """

    def __init__(self, clock_fn: Callable[[], float] = time.time) -> None:
        self._clock_fn = clock_fn
        self._work_duration = WORK_DURATION
        self._break_duration = BREAK_DURATION
        self._mode = TimerMode.WORK
        self._state = TimerState.IDLE
        self._start_time: float | None = None
        self._paused_remaining: int = self._work_duration

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mode(self) -> TimerMode:
        return self._mode

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def remaining_seconds(self) -> int:
        if self._state == TimerState.RUNNING and self._start_time is not None:
            elapsed = self._clock_fn() - self._start_time
            remaining = self._paused_remaining - int(elapsed)
            return max(0, remaining)
        return self._paused_remaining

    @property
    def total_duration(self) -> int:
        return self._work_duration if self._mode == TimerMode.WORK else self._break_duration

    @property
    def settings(self) -> dict[str, int]:
        return {
            "work_duration_minutes": self._work_duration // 60,
            "break_duration_minutes": self._break_duration // 60,
        }

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def start(self) -> None:
        """タイマーを開始または再開する。"""
        if self._state == TimerState.RUNNING:
            return
        self._start_time = self._clock_fn()
        self._state = TimerState.RUNNING

    def pause(self) -> None:
        """タイマーを一時停止する。"""
        if self._state != TimerState.RUNNING:
            return
        self._paused_remaining = self.remaining_seconds
        self._start_time = None
        self._state = TimerState.PAUSED

    def reset(self) -> None:
        """タイマーを初期状態（WORK モード）にリセットする。"""
        self._mode = TimerMode.WORK
        self._state = TimerState.IDLE
        self._start_time = None
        self._paused_remaining = self._work_duration

    def complete_session(self) -> TimerMode:
        """現在のセッションを完了し、次のモードに切り替える。

        Returns:
            切り替え後の TimerMode
        """
        if self._mode == TimerMode.WORK:
            self._mode = TimerMode.BREAK
            self._paused_remaining = self._break_duration
        else:
            self._mode = TimerMode.WORK
            self._paused_remaining = self._work_duration
        self._state = TimerState.IDLE
        self._start_time = None
        return self._mode

    def set_durations(self, work_duration_minutes: int, break_duration_minutes: int) -> None:
        """作業/休憩時間を更新する。"""
        if work_duration_minutes not in ALLOWED_WORK_DURATIONS_MINUTES:
            raise ValueError("invalid work duration")
        if break_duration_minutes not in ALLOWED_BREAK_DURATIONS_MINUTES:
            raise ValueError("invalid break duration")

        self._work_duration = work_duration_minutes * 60
        self._break_duration = break_duration_minutes * 60

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "mode": self._mode.value,
            "state": self._state.value,
            "remaining_seconds": self.remaining_seconds,
            "total_duration": self.total_duration,
        }

    @classmethod
    def from_dict(cls, data: dict, clock_fn: Callable[[], float] = time.time) -> "PomodoroTimer":
        timer = cls(clock_fn=clock_fn)
        timer._mode = TimerMode(data["mode"])
        timer._state = TimerState(data.get("state", TimerState.IDLE.value))
        timer._paused_remaining = data.get("remaining_seconds", WORK_DURATION)
        return timer
