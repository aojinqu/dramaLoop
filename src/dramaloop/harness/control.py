"""Thread-safe run control for pause / resume / cancel checkpoints."""

from __future__ import annotations

import threading
from typing import Literal


class RunCancelled(Exception):
    """Raised when a run is cancelled at a checkpoint."""


ControlPhase = Literal["awaiting_plan_review", "between_episodes", "idle"]


class RunController:
    def __init__(self, *, pause_after_plan: bool = True) -> None:
        self.pause_after_plan = pause_after_plan
        self._lock = threading.Lock()
        self._cancelled = False
        self._paused = False
        self._gate = threading.Event()
        self._gate.set()
        self.phase: ControlPhase = "idle"

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            self._paused = False
            self.phase = "idle"
            self._gate.set()

    def pause(self, phase: ControlPhase = "between_episodes") -> None:
        with self._lock:
            if self._cancelled:
                return
            self._paused = True
            self.phase = phase
            self._gate.clear()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self.phase = "idle"
            self._gate.set()

    def checkpoint(self, *, label: str = "") -> None:
        """Block while paused; raise RunCancelled if cancelled."""
        with self._lock:
            if self._cancelled:
                raise RunCancelled(label or "cancelled")
        while True:
            self._gate.wait(timeout=0.25)
            with self._lock:
                if self._cancelled:
                    raise RunCancelled(label or "cancelled")
                if not self._paused:
                    return

    def enter_plan_review(self) -> None:
        if not self.pause_after_plan:
            return
        self.pause(phase="awaiting_plan_review")
        self.checkpoint(label="plan_review")


class RunControllerRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._controllers: dict[str, RunController] = {}

    def create(self, run_id: str, *, pause_after_plan: bool = True) -> RunController:
        controller = RunController(pause_after_plan=pause_after_plan)
        with self._lock:
            self._controllers[run_id] = controller
        return controller

    def get(self, run_id: str) -> RunController | None:
        with self._lock:
            return self._controllers.get(run_id)

    def discard(self, run_id: str) -> None:
        with self._lock:
            self._controllers.pop(run_id, None)

    def clear(self) -> None:
        with self._lock:
            self._controllers.clear()


CONTROLLERS = RunControllerRegistry()
