from enum import Enum


class StopReason(str, Enum):
    TASK_COMPLETED = "task_completed"
    MAX_TURNS_REACHED = "max_turns_reached"
    MAX_TOOL_CALLS_REACHED = "max_tool_calls_reached"
    TIMEOUT = "timeout"
    SAFETY_BLOCKED = "safety_blocked"
