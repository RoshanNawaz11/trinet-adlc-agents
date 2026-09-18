from __future__ import annotations

# Every run pauses before aggregating, so a human/reviewer step can inspect
# step_results before final_output is produced. In a real system this list
# would likely be conditional (e.g. only when `state["flagged"]` is True) —
# kept unconditional here since the whole point of the scaffold is to show
# the resume mechanics working end-to-end.
INTERRUPT_BEFORE: list[str] = ["aggregate"]