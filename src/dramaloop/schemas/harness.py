from typing import Literal


HarnessMode = Literal[
    "baseline",
    "contract_enabled",
    "memory_skill_enabled",
    "memory_context_budgeted",
    "realization_enabled",
    "trajectory_regulation_enabled",
    "full_harness",
]

HARNESS_MODES: tuple[HarnessMode, ...] = (
    "baseline",
    "contract_enabled",
    "memory_skill_enabled",
    "memory_context_budgeted",
    "realization_enabled",
    "trajectory_regulation_enabled",
    "full_harness",
)

HARNESS_MODE_LEVEL = {mode: level for level, mode in enumerate(HARNESS_MODES)}
