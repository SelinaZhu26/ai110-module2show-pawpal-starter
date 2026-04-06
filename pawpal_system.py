"""
PawPal+ core system — class stubs.
Attributes and method signatures match the UML in README.md.
No scheduling logic is implemented yet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """Represents a pet owner with a daily time budget and preferences."""

    def __init__(self, name: str, daily_time_budget_min: int = 120):
        self.owner_id: str = str(uuid.uuid4())
        self.name: str = name
        self.daily_time_budget_min: int = daily_time_budget_min
        self.preferences: dict = {}   # e.g. {"prefer_morning": True}
        self.pets: list[Pet] = []

    def add_pet(self, pet: "Pet") -> None:
        """Add a pet to this owner's pet list."""
        pass

    def set_preference(self, key: str, value) -> None:
        """Store an owner preference by key."""
        pass

    def get_available_minutes(self) -> int:
        """Return daily_time_budget_min (hook for future overrides)."""
        pass

    def __repr__(self) -> str:
        return f"Owner(name={self.name!r}, pets={len(self.pets)})"


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents a pet with its own task list."""

    name: str
    species: str
    age_years: int = 0
    weight_kg: float = 0.0
    pet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    medications: list[str] = field(default_factory=list)
    tasks: list["Task"] = field(default_factory=list)

    def add_task(self, task: "Task") -> None:
        """Attach a task to this pet."""
        pass

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its ID."""
        pass

    def get_tasks_for_date(self, target_date: date) -> list["Task"]:
        """Return tasks whose due_at falls on target_date."""
        pass


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single care task (walk, feeding, medication, etc.)."""

    pet_id: str
    title: str
    category: str                          # e.g. "walk", "feeding", "medication"
    duration_min: int
    priority: int                          # 1 (low) – 5 (critical)
    frequency: str = "daily"              # "daily", "weekly", "as_needed"
    due_at: Optional[datetime] = None
    is_medication: bool = False
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed_at: Optional[datetime] = None

    def mark_completed(self, timestamp: Optional[datetime] = None) -> None:
        """Record the task as completed at the given timestamp."""
        pass

    def is_due(self, now: datetime) -> bool:
        """Return True if the task is due at or before now."""
        pass

    def urgency_score(self, now: datetime) -> float:
        """Compute a numeric urgency score used by the Scheduler."""
        pass


# ---------------------------------------------------------------------------
# ScheduledItem
# ---------------------------------------------------------------------------

@dataclass
class ScheduledItem:
    """One task placed at a specific time slot in the daily plan."""

    task: Task
    start_time: datetime
    end_time: datetime
    reason: str = ""

    def overlaps_with(self, other: "ScheduledItem") -> bool:
        """Return True if this slot overlaps with another ScheduledItem."""
        pass

    def to_dict(self) -> dict:
        """Serialise to a plain dict (used by Streamlit table display)."""
        pass


# ---------------------------------------------------------------------------
# PlanResult
# ---------------------------------------------------------------------------

@dataclass
class PlanResult:
    """The output produced by Scheduler.build_daily_plan()."""

    plan_date: date
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        pass

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Algorithmic engine: scores tasks and builds a daily plan for an owner."""

    def __init__(self):
        self.rules: list = []   # extensible rule objects (not used yet)

    def score_task(self, task: Task, owner: Owner, now: datetime) -> float:
        """Return a numeric score for a single task given the owner context."""
        pass

    def prioritize(self, tasks: list[Task], owner: Owner, now: datetime) -> list[Task]:
        """Return tasks sorted by descending score."""
        pass

    def build_daily_plan(self, owner: Owner, target_date: date) -> PlanResult:
        """Select and order tasks that fit within the owner's time budget."""
        pass

    def explain_plan(self, plan: PlanResult) -> list[str]:
        """Return a list of explanation strings, one per scheduled item."""
        pass
