"""
PawPal+ core system — full implementation.
Six classes: Owner, Pet, Task, ScheduledItem, PlanResult, Scheduler.
"""

from __future__ import annotations

import dataclasses
import itertools
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
        """Return True if the task should appear in today's plan.

        Handles three frequency modes:
        - "daily"    : always due (unless completed today).
        - "weekly"   : due if due_at falls within the same ISO week as now,
                       or if due_at has passed and the task is still pending.
        - "as_needed": only due when due_at is set and on/before today.
        """
        if self.completed_at is not None:
            # Already done today — suppress.
            if self.completed_at.date() == now.date():
                return False

        if self.frequency == "daily":
            return True

        if self.frequency == "weekly":
            if self.due_at is None:
                return False
            # Due if the scheduled date is this week or already overdue.
            return self.due_at.date() <= now.date() or (
                self.due_at.isocalendar()[:2] == now.isocalendar()[:2]
            )

        # "as_needed" — only due when explicitly given a due_at date
        if self.due_at is None:
            return False
        return self.due_at.date() <= now.date()

    def next_due_after(self, after: date) -> Optional[date]:
        """Return the next date this task is due after a given date.

        Algorithm 3 — recurring task support:
        - daily    → tomorrow
        - weekly   → same weekday next week
        - as_needed → None (no automatic recurrence)
        """
        if self.frequency == "daily":
            return after + timedelta(days=1)
        if self.frequency == "weekly":
            anchor = self.due_at.date() if self.due_at else after
            days_ahead = (anchor.weekday() - after.weekday()) % 7 or 7
            return after + timedelta(days=days_ahead)
        return None

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
        """Return every task that is due on target_date."""
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
        self.preferences: dict = {}
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

    def filter_tasks(
        self,
        *,
        pet_name: Optional[str] = None,
        category: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """Return tasks filtered by any combination of pet, category, and status.

        Algorithm 2 — filter by pet / status / category:
        Each keyword argument is optional; pass only the dimensions you need.

        Examples:
            owner.filter_tasks(pet_name="Mochi")
            owner.filter_tasks(category="medication", completed=False)
            owner.filter_tasks(pet_name="Luna", completed=True)
        """
        results: list[Task] = []
        pet_lookup = {p.name: p for p in self.pets}

        target_pets = (
            [pet_lookup[pet_name]] if pet_name and pet_name in pet_lookup
            else self.pets
        )

        for pet in target_pets:
            for task in pet.tasks:
                if category is not None and task.category != category:
                    continue
                if completed is True and task.completed_at is None:
                    continue
                if completed is False and task.completed_at is not None:
                    continue
                results.append(task)

        return results

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

    def sorted_by_time(self) -> list[ScheduledItem]:
        """Return scheduled items ordered by start_time (earliest first).

        Algorithm 1 — sort by clock time:
        build_daily_plan() orders by urgency score, but for display the
        user needs chronological order. This view leaves the original list
        intact and returns a new sorted copy.
        """
        return sorted(self.scheduled_items, key=lambda item: item.start_time)

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        n = len(self.scheduled_items)
        skipped = len(self.skipped_tasks)
        lines = [
            f"Plan for {self.plan_date}",
            f"  Scheduled: {n} task(s), {self.total_minutes} minutes",
            f"  Skipped:   {skipped} task(s) (over time budget)",
        ]
        for item in self.sorted_by_time():
            lines.append(
                f"  {item.start_time.strftime('%H:%M')} – "
                f"{item.end_time.strftime('%H:%M')}  {item.task.title}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise to a plain dict, items in chronological order."""
        return {
            "plan_date": str(self.plan_date),
            "total_minutes": self.total_minutes,
            "scheduled": [item.to_dict() for item in self.sorted_by_time()],
            "skipped": [t.title for t in self.skipped_tasks],
        }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Algorithmic engine: scores tasks and builds a daily plan for an owner."""

    def __init__(self):
        self.rules: list = []

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

    def detect_conflicts(
        self, items: list[ScheduledItem]
    ) -> list[tuple[ScheduledItem, ScheduledItem]]:
        """Return all pairs of ScheduledItems whose time slots overlap.

        Algorithm 4 — conflict detection:
        Compares every unique pair using ScheduledItem.overlaps_with().
        The current greedy planner places tasks back-to-back so conflicts
        cannot occur in a normal plan, but this method makes hidden bugs
        visible and supports future features like pinned start times.

        Returns an empty list when there are no conflicts.

        Simplified from nested index loops to itertools.combinations —
        same O(n²) complexity, but the intent ("every unique pair") is
        expressed directly rather than through manual index arithmetic.
        """
        return [
            (a, b)
            for a, b in itertools.combinations(items, 2)
            if a.overlaps_with(b)
        ]

    def warn_task_conflicts(
        self,
        tasks: list[Task],
        pets: Optional[list] = None,
    ) -> list[str]:
        """Return warning strings for any tasks whose time windows overlap.

        Lightweight conflict detection strategy:
        - Only considers tasks that have a due_at set (tasks without a
          pinned time cannot conflict on the clock).
        - For every unique pair (A, B), checks whether the half-open
          intervals [A.due_at, A.due_at + duration] and
          [B.due_at, B.due_at + duration] intersect using the standard
          overlap condition: A.start < B.end and B.start < A.end.
        - Returns a plain warning string per conflict instead of raising,
          so the caller can print, log, or surface it in the UI gracefully.

        Parameters
        ----------
        tasks : flat list of Task objects to check (usually owner.get_all_tasks())
        pets  : optional Pet list used to resolve pet_id → name in messages
        """
        pet_name_map: dict[str, str] = {}
        if pets:
            pet_name_map = {p.pet_id: p.name for p in pets}

        # Only tasks with a pinned due_at can conflict on the clock.
        timed = [t for t in tasks if t.due_at is not None]

        warnings: list[str] = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a, b = timed[i], timed[j]
                a_start = a.due_at
                a_end   = a.due_at + timedelta(minutes=a.duration_min)
                b_start = b.due_at
                b_end   = b.due_at + timedelta(minutes=b.duration_min)

                if a_start < b_end and b_start < a_end:
                    a_pet = pet_name_map.get(a.pet_id, a.pet_id[:8])
                    b_pet = pet_name_map.get(b.pet_id, b.pet_id[:8])
                    warnings.append(
                        f"WARNING: '{a.title}' [{a_pet}] "
                        f"{a_start.strftime('%H:%M')}–{a_end.strftime('%H:%M')}"
                        f"  overlaps  "
                        f"'{b.title}' [{b_pet}] "
                        f"{b_start.strftime('%H:%M')}–{b_end.strftime('%H:%M')}"
                    )
        return warnings

    def explain_plan(self, plan: PlanResult) -> list[str]:
        """Return a list of explanation strings, one per scheduled item."""
        lines = []
        for item in plan.sorted_by_time():
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

    def mark_task_complete(
        self,
        task: Task,
        pet: Pet,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Task]:
        """Mark a task complete and automatically enqueue the next occurrence.

        For "daily" tasks  → next due_at = completion date + timedelta(days=1).
        For "weekly" tasks → next due_at = same weekday next week via timedelta(days=7).
        For "as_needed"    → no new task is created; returns None.

        The next task is a copy of the original with a fresh task_id, the
        updated due_at, and completed_at reset to None.  It is appended to
        pet.tasks so it will appear automatically in future daily plans.

        Returns the newly created Task, or None when no recurrence applies.
        """
        task.mark_completed(timestamp)

        today = (timestamp or datetime.now()).date()
        next_date = task.next_due_after(today)
        if next_date is None:
            return None  # "as_needed" — no automatic recurrence

        # Preserve the original time-of-day if due_at was set; otherwise 08:00.
        if task.due_at is not None:
            next_due_at = datetime.combine(next_date, task.due_at.time())
        else:
            next_due_at = datetime.combine(next_date, time(8, 0))

        next_task = dataclasses.replace(
            task,
            task_id=str(uuid.uuid4()),
            due_at=next_due_at,
            completed_at=None,
        )
        pet.add_task(next_task)
        return next_task

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by their due_at time in ascending HH:MM order.

        Uses a lambda key that extracts the "HH:MM" string from each task's
        due_at datetime. Tasks without a due_at are placed at the end by
        falling back to the sentinel string "99:99".

        Parameters
        ----------
        tasks : list[Task]
            The flat list of Task objects to sort. The original list is not
            modified; a new sorted list is returned.

        Returns
        -------
        list[Task]
            A new list of Task objects ordered earliest due_at first.
            Tasks with no due_at appear at the end, preserving their
            relative order among each other.
        """
        return sorted(
            tasks,
            key=lambda t: t.due_at.strftime("%H:%M") if t.due_at is not None else "99:99",
        )

    def filter_tasks(
        self,
        tasks: list[Task],
        *,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
        pets: Optional[list] = None,
    ) -> list[Task]:
        """Return tasks filtered by completion status and/or pet name.

        Parameters
        ----------
        tasks:     The flat list of Task objects to filter.
        completed: True → keep only completed tasks; False → keep only pending.
        pet_name:  If given, keep only tasks belonging to a pet with this name.
        pets:      Full list of Pet objects used to resolve pet_name → pet_id.
                   Required when pet_name is provided.

        Returns
        -------
        list[Task]
            A new list containing only the Task objects that pass every
            supplied filter. Returns all tasks when no filters are given.
        """
        pet_ids: Optional[set] = None
        if pet_name is not None and pets is not None:
            pet_ids = {p.pet_id for p in pets if p.name == pet_name}

        result: list[Task] = []
        for task in tasks:
            if completed is True and task.completed_at is None:
                continue
            if completed is False and task.completed_at is not None:
                continue
            if pet_ids is not None and task.pet_id not in pet_ids:
                continue
            result.append(task)
        return result

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
