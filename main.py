"""
PawPal+ demo script — Phase 3 (algorithms).
Demonstrates: sorting, filtering, recurring tasks, conflict detection.
Run: python main.py
"""

from datetime import date, datetime, time

from pawpal_system import Owner, Pet, Scheduler, Task

WIDTH = 60

def rule(char="─"):
    return char * WIDTH

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", daily_time_budget_min=90)

mochi = Pet(name="Mochi", species="dog", age_years=3, weight_kg=8.5)
luna  = Pet(name="Luna",  species="cat", age_years=5, weight_kg=4.2)

owner.add_pet(mochi)
owner.add_pet(luna)

today = date.today()

# --- Mochi's tasks ----------------------------------------------------------
mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Morning walk",
    category="walk",
    duration_min=25,
    priority=4,
    frequency="daily",
))

mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Heartworm pill",
    category="medication",
    duration_min=5,
    priority=5,
    frequency="daily",
    is_medication=True,
))

mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Breakfast",
    category="feeding",
    duration_min=10,
    priority=4,
    frequency="daily",
))

# Weekly grooming — due this week (Algorithm 3: recurring tasks)
mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Bath & brush",
    category="grooming",
    duration_min=30,
    priority=3,
    frequency="weekly",
    due_at=datetime.combine(today, time(10, 0)),   # due today
))

# --- Luna's tasks -----------------------------------------------------------
luna.add_task(Task(
    pet_id=luna.pet_id,
    title="Playtime / enrichment",
    category="enrichment",
    duration_min=20,
    priority=3,
    frequency="daily",
))

luna.add_task(Task(
    pet_id=luna.pet_id,
    title="Flea treatment",
    category="medication",
    duration_min=5,
    priority=5,
    frequency="daily",
    is_medication=True,
    due_at=datetime.combine(today, time(9, 0)),
))

luna.add_task(Task(
    pet_id=luna.pet_id,
    title="Grooming brush",
    category="grooming",
    duration_min=15,
    priority=2,
    frequency="daily",
))

# Tasks added OUT OF ORDER (evening task first, then morning) to demo sort_by_time()
mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Evening walk",
    category="walk",
    duration_min=20,
    priority=3,
    frequency="daily",
    due_at=datetime.combine(today, time(18, 30)),   # 18:30 — added first intentionally
))

mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Morning meds",
    category="medication",
    duration_min=5,
    priority=5,
    frequency="daily",
    is_medication=True,
    due_at=datetime.combine(today, time(7, 0)),     # 07:00 — added after the 18:30 task
))

# Deliberately overlapping tasks to demo warn_task_conflicts()
# Mochi: "Vet checkup" starts at 10:00, lasts 45 min → window 10:00–10:45
# Luna:  "Nail trim"   starts at 10:15, lasts 10 min → window 10:15–10:25
# Both windows overlap, so the detector should fire.
mochi.add_task(Task(
    pet_id=mochi.pet_id,
    title="Vet checkup",
    category="vet",
    duration_min=45,
    priority=5,
    frequency="as_needed",
    due_at=datetime.combine(today, time(10, 0)),
))

luna.add_task(Task(
    pet_id=luna.pet_id,
    title="Nail trim",
    category="grooming",
    duration_min=10,
    priority=3,
    frequency="as_needed",
    due_at=datetime.combine(today, time(10, 15)),
))

# Mark one task completed so the filter demo is interesting
luna.tasks[0].mark_completed()   # Playtime is already done

# ---------------------------------------------------------------------------
# Build the schedule
# ---------------------------------------------------------------------------

scheduler = Scheduler()
plan = scheduler.build_daily_plan(owner, today)

# ---------------------------------------------------------------------------
# DISPLAY 1: Today's schedule sorted by clock time (Algorithm 1)
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print(f"  🐾  PawPal+ — Today's Schedule  ({plan.plan_date})")
print(rule("═"))
print(f"  Owner : {owner.name}")
print(f"  Budget: {owner.get_available_minutes()} min available  |  {plan.total_minutes} min scheduled")
print(rule())

if plan.scheduled_items:
    print(f"  {'TIME':>10}   {'TASK':<25}  {'PET':<8}  {'MIN':>4}")
    print(rule())
    for item in plan.sorted_by_time():         # ← Algorithm 1: sorted by start time
        pet_name = next(
            (p.name for p in owner.pets if p.pet_id == item.task.pet_id), "?"
        )
        time_range = f"{item.start_time.strftime('%H:%M')}–{item.end_time.strftime('%H:%M')}"
        freq_tag = f"[{item.task.frequency}]" if item.task.frequency != "daily" else ""
        print(f"  {time_range:>10}   {item.task.title:<22} {freq_tag:<4}  {pet_name:<8}  {item.task.duration_min:>4}")
else:
    print("  No tasks scheduled.")

print(rule())

if plan.skipped_tasks:
    print("  Skipped (over budget):")
    for t in plan.skipped_tasks:
        print(f"    • {t.title} ({t.duration_min} min)")
    print(rule())

print()
print("  Why this order?")
for line in scheduler.explain_plan(plan):
    print(f"    {line}")

# ---------------------------------------------------------------------------
# DISPLAY 2: Filter demos (Algorithm 2)
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  🔍  Filter demos")
print(rule("═"))

meds = owner.filter_tasks(category="medication")
print(f"  All medication tasks ({len(meds)}):")
for t in meds:
    pet_name = next((p.name for p in owner.pets if p.pet_id == t.pet_id), "?")
    print(f"    • [{pet_name}] {t.title}")

print()
pending = owner.filter_tasks(pet_name="Luna", completed=False)
print(f"  Luna's pending tasks ({len(pending)}):")
for t in pending:
    print(f"    • {t.title} (priority {t.priority})")

print()
done = owner.filter_tasks(completed=True)
print(f"  Completed tasks across all pets ({len(done)}):")
for t in done:
    pet_name = next((p.name for p in owner.pets if p.pet_id == t.pet_id), "?")
    print(f"    • [{pet_name}] {t.title}")

# ---------------------------------------------------------------------------
# DISPLAY 3: Recurring task — next due date (Algorithm 3)
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  🔁  Recurring task — next due dates")
print(rule("═"))

for pet in owner.pets:
    for task in pet.tasks:
        next_due = task.next_due_after(today)
        if next_due:
            print(f"  [{pet.name}] {task.title:<25}  next due: {next_due}  (freq: {task.frequency})")

# ---------------------------------------------------------------------------
# DISPLAY 4: Conflict detection (Algorithm 4)
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  ⚠️   Conflict detection")
print(rule("═"))

conflicts = scheduler.detect_conflicts(plan.scheduled_items)
if conflicts:
    print(f"  {len(conflicts)} conflict(s) found:")
    for a, b in conflicts:
        print(f"    ✗ '{a.task.title}' ({a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}) "
              f"overlaps '{b.task.title}' ({b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')})")
else:
    print("  No conflicts — all time slots are clean.")

print()
print(rule("═"))

# ---------------------------------------------------------------------------
# DISPLAY 4b: warn_task_conflicts() — raw-task overlap warnings
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  ⚠️   warn_task_conflicts() — pre-plan overlap detection")
print(rule("═"))
print("  (Vet checkup 10:00–10:45 and Nail trim 10:15–10:25 intentionally overlap)")
print()

conflict_warnings = scheduler.warn_task_conflicts(owner.get_all_tasks(), pets=owner.pets)
if conflict_warnings:
    for msg in conflict_warnings:
        print(f"  {msg}")
else:
    print("  No raw-task conflicts detected.")

print(rule("═"))

# ---------------------------------------------------------------------------
# DISPLAY 5: sort_by_time() — tasks sorted by HH:MM using a lambda
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  🕐  Scheduler.sort_by_time() — chronological order via lambda")
print(rule("═"))
print("  (Tasks were added out of order: Evening walk before Morning meds)")
print()

all_tasks = owner.get_all_tasks()
sorted_tasks = scheduler.sort_by_time(all_tasks)

print(f"  {'TIME':>6}   {'TASK':<28}  {'CAT':<12}")
print(rule())
for t in sorted_tasks:
    time_str = t.due_at.strftime("%H:%M") if t.due_at is not None else "no time"
    pet_name = next((p.name for p in owner.pets if p.pet_id == t.pet_id), "?")
    print(f"  {time_str:>6}   {t.title:<28}  {t.category:<12}  [{pet_name}]")

print(rule())

# ---------------------------------------------------------------------------
# DISPLAY 6: Scheduler.filter_tasks() — by completion status and pet name
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  🔎  Scheduler.filter_tasks() — by status and pet name")
print(rule("═"))

pending_mochi = scheduler.filter_tasks(
    all_tasks, completed=False, pet_name="Mochi", pets=owner.pets
)
print(f"  Mochi's pending tasks ({len(pending_mochi)}):")
for t in pending_mochi:
    time_str = t.due_at.strftime("%H:%M") if t.due_at else "—"
    print(f"    • {t.title:<28}  due: {time_str}")

print()
done_tasks = scheduler.filter_tasks(all_tasks, completed=True)
print(f"  Completed tasks across all pets ({len(done_tasks)}):")
for t in done_tasks:
    pet_name = next((p.name for p in owner.pets if p.pet_id == t.pet_id), "?")
    print(f"    • [{pet_name}] {t.title}")

print()
print(rule("═"))

# ---------------------------------------------------------------------------
# DISPLAY 7: mark_task_complete() — auto-create next occurrence
# ---------------------------------------------------------------------------

print()
print(rule("═"))
print("  🔄  Scheduler.mark_task_complete() — auto-recurrence on completion")
print(rule("═"))

# Pick Mochi's Morning walk (daily) and Bath & brush (weekly) to demo.
walk_task  = next(t for t in mochi.tasks if t.title == "Morning walk")
bath_task  = next(t for t in mochi.tasks if t.title == "Bath & brush")

tasks_before = len(mochi.tasks)
print(f"  Mochi's task count before completion: {tasks_before}")
print()

# Mark the daily task complete → next occurrence is today + 1 day (timedelta(days=1))
next_walk = scheduler.mark_task_complete(walk_task, mochi)
print(f"  Completed : '{walk_task.title}' (daily)")
print(f"    completed_at : {walk_task.completed_at.strftime('%Y-%m-%d %H:%M')}")
print(f"    next due_at  : {next_walk.due_at.strftime('%Y-%m-%d %H:%M')}  (+1 day via timedelta)")
print()

# Mark the weekly task complete → next occurrence is same weekday next week
next_bath = scheduler.mark_task_complete(bath_task, mochi)
print(f"  Completed : '{bath_task.title}' (weekly)")
print(f"    completed_at : {bath_task.completed_at.strftime('%Y-%m-%d %H:%M')}")
print(f"    next due_at  : {next_bath.due_at.strftime('%Y-%m-%d %H:%M')}  (+7 days via timedelta)")
print()

tasks_after = len(mochi.tasks)
print(f"  Mochi's task count after completion: {tasks_after}  (+{tasks_after - tasks_before} auto-created)")

print()
print(rule("═"))
print()
