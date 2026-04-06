"""
PawPal+ demo script.
Run: python main.py
"""

from datetime import date, datetime, time

from pawpal_system import Owner, Pet, Scheduler, Task


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


# ---------------------------------------------------------------------------
# Build the schedule
# ---------------------------------------------------------------------------

scheduler = Scheduler()
plan = scheduler.build_daily_plan(owner, today)
explanations = scheduler.explain_plan(plan)


# ---------------------------------------------------------------------------
# Print "Today's Schedule"
# ---------------------------------------------------------------------------

WIDTH = 60

def rule(char="─"):
    return char * WIDTH

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
    for item in plan.scheduled_items:
        pet_name = next(
            (p.name for p in owner.pets if p.pet_id == item.task.pet_id),
            "?"
        )
        time_range = f"{item.start_time.strftime('%H:%M')}–{item.end_time.strftime('%H:%M')}"
        print(f"  {time_range:>10}   {item.task.title:<25}  {pet_name:<8}  {item.task.duration_min:>4}")
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
for line in explanations:
    print(f"    {line}")

print()
print(rule("═"))
print()
