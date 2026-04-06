import streamlit as st
from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()

if "plan" not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — backed by real Python objects.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.subheader("1. Owner")

col_a, col_b = st.columns(2)
with col_a:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_b:
    budget = st.number_input("Daily time budget (minutes)", min_value=10, max_value=480, value=90)

if st.button("Save owner"):
    st.session_state.owner = Owner(name=owner_name, daily_time_budget_min=int(budget))
    st.session_state.plan = None
    st.success(f"Owner saved: {owner_name} ({budget} min/day)")

if st.session_state.owner:
    st.caption(
        f"Current owner: **{st.session_state.owner.name}** — "
        f"{st.session_state.owner.get_available_minutes()} min budget — "
        f"{len(st.session_state.owner.pets)} pet(s)"
    )

# ---------------------------------------------------------------------------
# Section 2 — Add pets
# ---------------------------------------------------------------------------

st.divider()
st.subheader("2. Pets")

if st.session_state.owner is None:
    st.info("Save an owner first.")
else:
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])

    if st.button("Add pet"):
        new_pet = Pet(name=pet_name, species=species)
        st.session_state.owner.add_pet(new_pet)
        st.session_state.plan = None
        st.success(f"Added {pet_name} the {species} to {st.session_state.owner.name}'s household.")

    pets = st.session_state.owner.pets
    if pets:
        st.write("**Registered pets:**")
        st.table([
            {"Name": p.name, "Species": p.species, "Tasks": len(p.tasks)}
            for p in pets
        ])
    else:
        st.info("No pets yet — add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Add tasks
# ---------------------------------------------------------------------------

st.divider()
st.subheader("3. Tasks")

owner = st.session_state.owner
if owner is None or not owner.pets:
    st.info("Add at least one pet before creating tasks.")
else:
    PRIORITY_MAP = {"low (1)": 1, "medium (3)": 3, "high (5)": 5}

    pet_options = {p.name: p for p in owner.pets}
    selected_pet_name = st.selectbox("Assign task to", list(pet_options.keys()))
    selected_pet = pet_options[selected_pet_name]

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Minutes", min_value=1, max_value=240, value=20)
    with col3:
        category = st.selectbox(
            "Category", ["walk", "feeding", "medication", "enrichment", "grooming", "other"]
        )

    col4, col5 = st.columns(2)
    with col4:
        priority_label = st.selectbox("Priority", list(PRIORITY_MAP.keys()), index=2)
    with col5:
        is_med = st.checkbox("Medication task")

    if st.button("Add task"):
        new_task = Task(
            pet_id=selected_pet.pet_id,
            title=task_title,
            category=category,
            duration_min=int(duration),
            priority=PRIORITY_MAP[priority_label],
            frequency="daily",
            is_medication=is_med,
        )
        selected_pet.add_task(new_task)
        st.session_state.plan = None
        st.success(f"Added '{task_title}' to {selected_pet_name}'s task list.")

    # ── Smart task display: sorted by time, filterable by status ────────────
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        scheduler = st.session_state.scheduler

        st.write(f"**All tasks ({len(all_tasks)} total):**")

        col_filter, col_sort_label = st.columns([2, 3])
        with col_filter:
            show_pending_only = st.checkbox("Show pending only", value=False)

        # Apply filter then sort
        display_tasks = scheduler.filter_tasks(
            all_tasks, completed=False if show_pending_only else None
        )
        display_tasks = scheduler.sort_by_time(display_tasks)

        # ── Conflict warnings ────────────────────────────────────────────────
        conflicts = scheduler.warn_task_conflicts(display_tasks)
        if conflicts:
            st.warning(
                f"⚠️ **{len(conflicts)} scheduling conflict(s) detected** — "
                "resolve these before generating your plan:"
            )
            for msg in conflicts:
                st.warning(f"• {msg}")

        pet_name_map = {p.pet_id: p.name for p in owner.pets}
        st.table([
            {
                "Pet":       pet_name_map.get(t.pet_id, "?"),
                "Title":     t.title,
                "Category":  t.category,
                "Due at":    t.due_at.strftime("%H:%M") if t.due_at else "—",
                "Minutes":   t.duration_min,
                "Priority":  t.priority,
                "Medication": "yes" if t.is_medication else "no",
                "Done":      "✓" if t.completed_at else "",
            }
            for t in display_tasks
        ])
    else:
        st.info("No tasks yet — add one above.")

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("4. Generate Schedule")

if owner is None or not owner.pets:
    st.info("Complete sections 1–3 first.")
elif not owner.get_all_tasks():
    st.info("Add at least one task before generating a schedule.")
else:
    # ── Pre-flight conflict check ────────────────────────────────────────────
    scheduler = st.session_state.scheduler
    pending   = scheduler.filter_tasks(owner.get_all_tasks(), completed=False)
    conflicts = scheduler.warn_task_conflicts(pending)

    if conflicts:
        st.warning(
            f"⚠️ **{len(conflicts)} conflict(s) in your pending tasks** — "
            "your plan may be unreliable until these are resolved."
        )
        for msg in conflicts:
            st.warning(f"• {msg}")

    if st.button("Generate schedule"):
        plan = scheduler.build_daily_plan(owner, date.today())
        st.session_state.plan = plan

    if st.session_state.plan is not None:
        plan = st.session_state.plan

        st.success(
            f"Plan for **{plan.plan_date}** — "
            f"{len(plan.scheduled_items)} task(s) scheduled, "
            f"{plan.total_minutes} / {owner.get_available_minutes()} min used"
        )

        if plan.scheduled_items:
            st.table([item.to_dict() for item in plan.scheduled_items])

        if plan.skipped_tasks:
            skipped = ", ".join(t.title for t in plan.skipped_tasks)
            st.warning(f"Skipped (over time budget): {skipped}")

        with st.expander("Why this order?"):
            for line in scheduler.explain_plan(plan):
                st.write(f"• {line}")
