"""
PawPal+ tests — two core behaviors.
Run: python -m pytest
"""

from datetime import datetime

from pawpal_system import Pet, Task


def make_task(title="Morning walk", duration_min=20, priority=3) -> Task:
    """Helper: return a simple daily walk task."""
    return Task(
        pet_id="test-pet",
        title=title,
        category="walk",
        duration_min=duration_min,
        priority=priority,
        frequency="daily",
    )


# ---------------------------------------------------------------------------
# Test 1: Task completion
# ---------------------------------------------------------------------------

def test_mark_completed_sets_completed_at():
    """Calling mark_completed() should record a non-None completed_at timestamp."""
    task = make_task()
    assert task.completed_at is None, "Task should start as incomplete"

    task.mark_completed()

    assert task.completed_at is not None, "completed_at should be set after mark_completed()"
    assert isinstance(task.completed_at, datetime)


def test_mark_completed_with_explicit_timestamp():
    """mark_completed(timestamp) should store the exact timestamp provided."""
    task = make_task()
    ts = datetime(2026, 4, 6, 9, 30)

    task.mark_completed(ts)

    assert task.completed_at == ts


def test_completed_task_is_not_due():
    """A completed task should not appear as due, even if its due date matches."""
    task = make_task()
    task.mark_completed()

    assert task.is_due(datetime.now()) is False


# ---------------------------------------------------------------------------
# Test 2: Adding a task to a Pet
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by exactly one."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0, "Pet should start with no tasks"

    pet.add_task(make_task("Walk"))

    assert len(pet.tasks) == 1


def test_add_multiple_tasks_tracks_all():
    """Adding three tasks should result in a task list of length three."""
    pet = Pet(name="Luna", species="cat")

    pet.add_task(make_task("Feeding", duration_min=10, priority=4))
    pet.add_task(make_task("Playtime", duration_min=15, priority=3))
    pet.add_task(make_task("Grooming", duration_min=20, priority=2))

    assert len(pet.tasks) == 3


def test_add_task_sets_pet_id():
    """add_task() should update task.pet_id to match the pet's own ID."""
    pet = Pet(name="Buddy", species="dog")
    task = make_task()

    pet.add_task(task)

    assert task.pet_id == pet.pet_id
