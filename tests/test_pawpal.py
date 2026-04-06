"""
PawPal+ tests — core behaviors and edge cases.
Run: python -m pytest -v
"""

from datetime import date, datetime, time, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TODAY = date(2026, 4, 6)
NOW   = datetime.combine(TODAY, time(8, 0))


def make_task(
    title="Morning walk",
    duration_min=20,
    priority=3,
    frequency="daily",
    due_at=None,
    is_medication=False,
    pet_id="test-pet",
) -> Task:
    return Task(
        pet_id=pet_id,
        title=title,
        category="walk",
        duration_min=duration_min,
        priority=priority,
        frequency=frequency,
        due_at=due_at,
        is_medication=is_medication,
    )


def make_owner_with_pet(budget_min=120) -> tuple[Owner, Pet, Scheduler]:
    owner = Owner(name="Jordan", daily_time_budget_min=budget_min)
    pet   = Pet(name="Mochi", species="dog")
    owner.add_pet(pet)
    return owner, pet, Scheduler()


# ===========================================================================
# 1. Task completion
# ===========================================================================

def test_mark_completed_sets_completed_at():
    """mark_completed() should record a non-None completed_at timestamp."""
    task = make_task()
    assert task.completed_at is None

    task.mark_completed()

    assert task.completed_at is not None
    assert isinstance(task.completed_at, datetime)


def test_mark_completed_with_explicit_timestamp():
    """mark_completed(ts) should store exactly the provided timestamp."""
    task = make_task()
    ts = datetime(2026, 4, 6, 9, 30)
    task.mark_completed(ts)
    assert task.completed_at == ts


def test_completed_task_is_not_due_today():
    """A task completed today should not appear as due later the same day."""
    task = make_task()
    task.mark_completed(NOW)
    assert task.is_due(NOW + timedelta(hours=2)) is False


# ===========================================================================
# 2. Pet task management
# ===========================================================================

def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Walk"))
    assert len(pet.tasks) == 1


def test_add_multiple_tasks_tracks_all():
    pet = Pet(name="Luna", species="cat")
    for title in ("Feeding", "Playtime", "Grooming"):
        pet.add_task(make_task(title))
    assert len(pet.tasks) == 3


def test_add_task_sets_pet_id():
    """add_task() must update task.pet_id to match the pet's ID."""
    pet  = Pet(name="Buddy", species="dog")
    task = make_task()
    pet.add_task(task)
    assert task.pet_id == pet.pet_id


def test_remove_task_by_id():
    pet  = Pet(name="Mochi", species="dog")
    task = make_task("Evening walk")
    pet.add_task(task)
    pet.remove_task(task.task_id)
    assert len(pet.tasks) == 0


def test_remove_task_nonexistent_id_is_noop():
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(make_task())
    pet.remove_task("does-not-exist")   # should not raise
    assert len(pet.tasks) == 1


# ===========================================================================
# 3. sort_by_time
# ===========================================================================

def test_sort_by_time_orders_earliest_first():
    """Tasks with earlier due_at should appear before later ones."""
    scheduler = Scheduler()
    t_late  = make_task("Evening walk", due_at=datetime.combine(TODAY, time(18, 0)))
    t_early = make_task("Morning meds", due_at=datetime.combine(TODAY, time(7, 0)))
    t_mid   = make_task("Lunch walk",   due_at=datetime.combine(TODAY, time(12, 0)))

    result = scheduler.sort_by_time([t_late, t_early, t_mid])

    assert [t.title for t in result] == ["Morning meds", "Lunch walk", "Evening walk"]


def test_sort_by_time_tasks_without_due_at_go_last():
    """Tasks missing due_at should always sort after timed tasks."""
    scheduler = Scheduler()
    t_timed    = make_task("Morning walk", due_at=datetime.combine(TODAY, time(8, 0)))
    t_untimed  = make_task("Grooming")    # no due_at

    result = scheduler.sort_by_time([t_untimed, t_timed])

    assert result[0].title == "Morning walk"
    assert result[1].title == "Grooming"


def test_sort_by_time_does_not_mutate_input():
    """sort_by_time() must leave the original list in its original order."""
    scheduler = Scheduler()
    t1 = make_task("B task", due_at=datetime.combine(TODAY, time(10, 0)))
    t2 = make_task("A task", due_at=datetime.combine(TODAY, time(8, 0)))
    original = [t1, t2]

    scheduler.sort_by_time(original)

    assert original[0].title == "B task"   # unchanged


def test_sort_by_time_all_untimed_returns_same_count():
    """An all-untimed list should come back with the same number of items."""
    scheduler = Scheduler()
    tasks = [make_task(f"Task {i}") for i in range(4)]
    result = scheduler.sort_by_time(tasks)
    assert len(result) == 4


# ===========================================================================
# 4. filter_tasks (Scheduler)
# ===========================================================================

def test_filter_tasks_pending_only():
    """completed=False should exclude tasks that have completed_at set."""
    scheduler = Scheduler()
    done    = make_task("Done task")
    pending = make_task("Pending task")
    done.mark_completed()

    result = scheduler.filter_tasks([done, pending], completed=False)

    assert result == [pending]


def test_filter_tasks_completed_only():
    """completed=True should include only tasks with completed_at set."""
    scheduler = Scheduler()
    done    = make_task("Done task")
    pending = make_task("Pending task")
    done.mark_completed()

    result = scheduler.filter_tasks([done, pending], completed=True)

    assert result == [done]


def test_filter_tasks_by_pet_name():
    """pet_name filter should return only tasks belonging to that pet."""
    owner, pet, scheduler = make_owner_with_pet()
    luna = Pet(name="Luna", species="cat")
    owner.add_pet(luna)

    mochi_task = make_task("Mochi walk")
    luna_task  = make_task("Luna play")
    pet.add_task(mochi_task)
    luna.add_task(luna_task)

    result = scheduler.filter_tasks(
        owner.get_all_tasks(), pet_name="Mochi", pets=owner.pets
    )
    assert len(result) == 1
    assert result[0].title == "Mochi walk"


def test_filter_tasks_no_filters_returns_all():
    """Calling filter_tasks with no criteria should return every task unchanged."""
    scheduler = Scheduler()
    tasks = [make_task(f"Task {i}") for i in range(5)]
    result = scheduler.filter_tasks(tasks)
    assert len(result) == 5


def test_filter_tasks_unknown_pet_name_returns_empty():
    """A pet_name that matches no pet should return an empty list."""
    owner, pet, scheduler = make_owner_with_pet()
    pet.add_task(make_task("Walk"))

    result = scheduler.filter_tasks(
        owner.get_all_tasks(), pet_name="Ghost", pets=owner.pets
    )
    assert result == []


# ===========================================================================
# 5. mark_task_complete — auto-recurrence
# ===========================================================================

def test_mark_task_complete_daily_adds_next_day():
    """Completing a daily task should add a new task due tomorrow."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task("Morning walk", frequency="daily",
                     due_at=datetime.combine(TODAY, time(8, 0)))
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert next_task is not None
    assert next_task.due_at.date() == TODAY + timedelta(days=1)


def test_mark_task_complete_weekly_adds_next_week():
    """Completing a weekly task should add a new task due 7 days later."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task("Bath & brush", frequency="weekly",
                     due_at=datetime.combine(TODAY, time(10, 0)))
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert next_task is not None
    assert next_task.due_at.date() == TODAY + timedelta(days=7)


def test_mark_task_complete_as_needed_returns_none():
    """Completing an as_needed task should NOT create a new task."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task("Vet checkup", frequency="as_needed",
                     due_at=datetime.combine(TODAY, time(10, 0)))
    pet.add_task(task)
    count_before = len(pet.tasks)

    result = scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert result is None
    assert len(pet.tasks) == count_before   # no new task added


def test_mark_task_complete_preserves_time_of_day():
    """The next occurrence should keep the same HH:MM as the original."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task("Evening walk", frequency="daily",
                     due_at=datetime.combine(TODAY, time(18, 30)))
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert next_task.due_at.time() == time(18, 30)


def test_mark_task_complete_stamps_original_as_done():
    """The original task must have completed_at set after the call."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task(frequency="daily")
    pet.add_task(task)

    scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert task.completed_at == NOW


def test_mark_task_complete_new_task_has_fresh_id():
    """The auto-created next task must have a different task_id."""
    _, pet, scheduler = make_owner_with_pet()
    task = make_task(frequency="daily")
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task, pet, timestamp=NOW)

    assert next_task.task_id != task.task_id


# ===========================================================================
# 6. warn_task_conflicts
# ===========================================================================

def _timed(title, start_time: time, duration_min: int, pet_id="p1") -> Task:
    return Task(
        pet_id=pet_id,
        title=title,
        category="test",
        duration_min=duration_min,
        priority=3,
        due_at=datetime.combine(TODAY, start_time),
    )


def test_warn_task_conflicts_detects_overlap():
    """Two tasks whose windows overlap should produce exactly one warning."""
    scheduler = Scheduler()
    a = _timed("Task A", time(10, 0), 30)   # 10:00–10:30
    b = _timed("Task B", time(10, 15), 20)  # 10:15–10:35

    warnings = scheduler.warn_task_conflicts([a, b])

    assert len(warnings) == 1
    assert "Task A" in warnings[0]
    assert "Task B" in warnings[0]


def test_warn_task_conflicts_no_overlap_is_empty():
    """Non-overlapping tasks should produce no warnings."""
    scheduler = Scheduler()
    a = _timed("Task A", time(9, 0),  30)   # 09:00–09:30
    b = _timed("Task B", time(10, 0), 20)   # 10:00–10:20

    warnings = scheduler.warn_task_conflicts([a, b])

    assert warnings == []


def test_warn_task_conflicts_adjacent_tasks_are_safe():
    """Tasks that touch (end of A == start of B) must NOT be flagged."""
    scheduler = Scheduler()
    a = _timed("Task A", time(9, 0),  30)   # 09:00–09:30
    b = _timed("Task B", time(9, 30), 20)   # 09:30–09:50  ← exactly adjacent

    warnings = scheduler.warn_task_conflicts([a, b])

    assert warnings == []


def test_warn_task_conflicts_untimed_tasks_ignored():
    """Tasks without due_at should never trigger a conflict warning."""
    scheduler = Scheduler()
    a = make_task("Task A")   # no due_at
    b = make_task("Task B")   # no due_at

    warnings = scheduler.warn_task_conflicts([a, b])

    assert warnings == []


def test_warn_task_conflicts_same_start_time():
    """Two tasks starting at the exact same time must be flagged as a conflict."""
    scheduler = Scheduler()
    a = _timed("Task A", time(9, 0), 30)   # 09:00–09:30
    b = _timed("Task B", time(9, 0), 20)   # 09:00–09:20  ← identical start

    warnings = scheduler.warn_task_conflicts([a, b])

    assert len(warnings) >= 1
    assert "Task A" in warnings[0]
    assert "Task B" in warnings[0]


def test_warn_task_conflicts_cross_pet_detected():
    """Conflicts between tasks from different pets should still be caught."""
    scheduler = Scheduler()
    a = _timed("Mochi walk", time(10, 0), 30, pet_id="pet-mochi")   # 10:00–10:30
    b = _timed("Luna trim",  time(10, 15), 10, pet_id="pet-luna")   # 10:15–10:25

    warnings = scheduler.warn_task_conflicts([a, b])

    assert len(warnings) == 1


# ===========================================================================
# 7. build_daily_plan — budget and scheduling
# ===========================================================================

def test_build_daily_plan_respects_budget():
    """Tasks exceeding the budget should appear in skipped_tasks, not scheduled."""
    owner, pet, scheduler = make_owner_with_pet(budget_min=30)
    pet.add_task(make_task("Short task",  duration_min=20, priority=3))
    pet.add_task(make_task("Long task",   duration_min=25, priority=2))

    plan = scheduler.build_daily_plan(owner, TODAY)

    scheduled_titles = [item.task.title for item in plan.scheduled_items]
    skipped_titles   = [t.title for t in plan.skipped_tasks]
    assert "Short task" in scheduled_titles
    assert "Long task"  in skipped_titles


def test_build_daily_plan_medications_scheduled_first():
    """A medication task should be scheduled before a lower-priority walk."""
    owner, pet, scheduler = make_owner_with_pet(budget_min=120)
    pet.add_task(make_task("Morning walk",  priority=3, duration_min=25))
    pet.add_task(Task(
        pet_id=pet.pet_id, title="Heartworm pill", category="medication",
        duration_min=5, priority=5, is_medication=True,
    ))

    plan = scheduler.build_daily_plan(owner, TODAY)

    titles = [item.task.title for item in plan.scheduled_items]
    assert titles.index("Heartworm pill") < titles.index("Morning walk")


def test_build_daily_plan_empty_pet_returns_empty_plan():
    """An owner whose pet has no tasks should get a plan with nothing scheduled."""
    owner, _, scheduler = make_owner_with_pet()
    # pet has no tasks

    plan = scheduler.build_daily_plan(owner, TODAY)

    assert plan.scheduled_items == []
    assert plan.skipped_tasks   == []
    assert plan.total_minutes   == 0


def test_build_daily_plan_no_pets_returns_empty_plan():
    """An owner with no pets at all should get a valid but empty plan."""
    owner     = Owner(name="Jordan", daily_time_budget_min=120)
    scheduler = Scheduler()

    plan = scheduler.build_daily_plan(owner, TODAY)

    assert plan.scheduled_items == []


def test_build_daily_plan_total_minutes_matches_scheduled():
    """plan.total_minutes should equal the sum of scheduled task durations."""
    owner, pet, scheduler = make_owner_with_pet(budget_min=120)
    pet.add_task(make_task("Task A", duration_min=20))
    pet.add_task(make_task("Task B", duration_min=15))

    plan = scheduler.build_daily_plan(owner, TODAY)

    expected = sum(item.task.duration_min for item in plan.scheduled_items)
    assert plan.total_minutes == expected
