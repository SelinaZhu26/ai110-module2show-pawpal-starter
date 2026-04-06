"""
PawPal+ core system — full implementation.
Six classes: Owner, Pet, Task, ScheduledItem, PlanResult, Scheduler.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional


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
        """Record the task as completed at the given timestamp (defaults to now)."""
        self.completed_at = timestamp or datetime.now()

    def is_due(self, now: datetime) -> bool:
        """Return True if the task should appear in today's plan."""
        if self.completed_at is not None:
            return False
        if self.due_at is None:
            return self.frequency == "daily"
        return self.due_at.date() <= now.date()

    def urgency_score(self, now: datetime) -> float:
        """Compute a numeric urgency score used by the Scheduler."""
        score = self.priority * 10.0
        if self.is_medication:
            score += 30.0
        if self.due_at is not None and self.due_at < now:
            hours_overdue = (now - self.due_at).total_seconds() / 3600
            score += min(hours_overdue * 2.0, 20.0)
        return score

    def __repr__(self) -> str:
        return f"Task(title={self.title!r}, priority={self.priority}, duration={self.duration_min}min)"


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
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet, updating pet_id to stay consistent."""
        task.pet_id = self.pet_id
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its ID (no-op if not found)."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def get_tasks_for_date(self, target_date: date) -> list[Task]:
        """Return every task that is due on target_date (daily or exact match)."""
        anchor = datetime.combine(target_date, time(8, 0))
        return [t for t in self.tasks if t.is_due(anchor)]

    def __repr__(self) -> str:
        return f"Pet(name={self.name!r}, species={self.species!r}, tasks={len(self.tasks)})"


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

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def set_preference(self, key: str, value) -> None:
        """Store an owner preference by key."""
        self.preferences[key] = value

    def get_available_minutes(self) -> int:
        """Return the owner's total daily time budget in minutes."""
        return self.daily_time_budget_min

    def get_all_tasks(self) -> list[Task]:
        """Return a flat list of every task across all owned pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def __repr__(self) -> str:
        return f"Owner(name={self.name!r}, pets={len(self.pets)})"


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

    def overlaps_with(self, other: ScheduledItem) -> bool:
        """Return True if this slot overlaps with another ScheduledItem."""
        return self.start_time < other.end_time and self.end_time > other.start_time

    def to_dict(self) -> dict:
        """Serialise to a plain dict for Streamlit table display."""
        return {
            "title": self.task.title,
            "category": self.task.category,
            "start": self.start_time.strftime("%H:%M"),
            "end": self.end_time.strftime("%H:%M"),
            "duration_min": self.task.duration_min,
            "priority": self.task.priority,
            "reason": self.reason,
        }


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
        n = len(self.scheduled_items)
        skipped = len(self.skipped_tasks)
        lines = [
            f"Plan for {self.plan_date}",
            f"  Scheduled: {n} task(s), {self.total_minutes} minutes",
            f"  Skipped:   {skipped} task(s) (over time budget)",
        ]
        for item in self.scheduled_items:
            lines.append(f"  {item.start_time.strftime('%H:%M')} – {item.end_time.strftime('%H:%M')}  {item.task.title}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "plan_date": str(self.plan_date),
            "total_minutes": self.total_minutes,
            "scheduled": [item.to_dict() for item in self.scheduled_items],
            "skipped": [t.title for t in self.skipped_tasks],
        }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Algorithmic engine: scores tasks and builds a daily plan for an owner."""

    def __init__(self):
        self.rules: list = []   # extensible rule objects (reserved for future use)

    def score_task(self, task: Task, owner: Owner, now: datetime) -> float:
        """Return a numeric score for a single task given the owner context."""
        score = task.urgency_score(now)
        if owner.preferences.get("prioritize_medications") and task.is_medication:
            score *= 2.0
        return score

    def prioritize(self, tasks: list[Task], owner: Owner, now: datetime) -> list[Task]:
        """Return tasks sorted by descending score (highest urgency first)."""
        return sorted(tasks, key=lambda t: self.score_task(t, owner, now), reverse=True)

    def build_daily_plan(self, owner: Owner, target_date: date) -> PlanResult:
        """Select and order tasks that fit within the owner's time budget."""
        now = datetime.combine(target_date, time(8, 0))

        eligible = [t for t in owner.get_all_tasks() if t.is_due(now)]
        ordered = self.prioritize(eligible, owner, now)

        budget = owner.get_available_minutes()
        current_time = now
        scheduled: list[ScheduledItem] = []
        skipped: list[Task] = []

        for task in ordered:
            if task.duration_min <= budget:
                end_time = current_time + timedelta(minutes=task.duration_min)
                reason = self._reason_for(task, now)
                scheduled.append(ScheduledItem(
                    task=task,
                    start_time=current_time,
                    end_time=end_time,
                    reason=reason,
                ))
                current_time = end_time
                budget -= task.duration_min
            else:
                skipped.append(task)

        total = sum(item.task.duration_min for item in scheduled)
        return PlanResult(
            plan_date=target_date,
            scheduled_items=scheduled,
            skipped_tasks=skipped,
            total_minutes=total,
        )

    def explain_plan(self, plan: PlanResult) -> list[str]:
        """Return a list of explanation strings, one per scheduled item."""
        lines = []
        for item in plan.scheduled_items:
            lines.append(
                f"{item.start_time.strftime('%H:%M')} — {item.task.title}: {item.reason}"
            )
        if plan.skipped_tasks:
            skipped_titles = ", ".join(t.title for t in plan.skipped_tasks)
            lines.append(f"Skipped (over budget): {skipped_titles}")
        return lines

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reason_for(self, task: Task, now: datetime) -> str:
        """Generate a plain-English reason string for why a task was scheduled."""
        parts = []
        if task.is_medication:
            parts.append("medication (safety-critical)")
        elif task.priority >= 4:
            parts.append(f"high priority ({task.priority}/5)")
        else:
            parts.append(f"priority {task.priority}/5")

        if task.due_at is not None and task.due_at < now:
            hours = int((now - task.due_at).total_seconds() / 3600)
            parts.append(f"overdue by {hours}h")

        return ", ".join(parts)
