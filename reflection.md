# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial design has six classes, each with a single clear responsibility:

- **Owner** — holds identity info, a daily time budget (minutes), and a list of owned pets. It is the entry point the Scheduler queries for constraints.
- **Pet** — holds a pet's profile (species, age, weight, medications) and owns the task list for that pet. Tasks are scoped to a pet, not to the owner directly.
- **Task** — represents one care item (walk, feeding, medication, etc.) with a priority integer (1–5), duration in minutes, optional due time, and a medication flag. It computes its own urgency score so the Scheduler stays decoupled from that detail.
- **ScheduledItem** — a thin wrapper that pairs a Task with a concrete start/end time and a plain-English reason string. It is produced by the Scheduler, not stored on Pet or Task.
- **PlanResult** — collects all ScheduledItems for one day alongside tasks that were skipped (didn't fit the budget). Separates planning output from raw input data.
- **Scheduler** — the algorithmic engine. It scores tasks, sorts them, and greedily fills the owner's time budget. It depends on Owner and Task but does not own either, keeping the data model and logic layer separate.

**b. Design changes**

One gap was found during AI review of the skeleton: `Scheduler.build_daily_plan(owner, date)` needs to collect tasks from every pet the owner has, but `Owner` had no method for that. The Scheduler would have had to know to loop `owner.pets` and flatten each pet's `.tasks` — coupling the scheduling algorithm to the internal structure of both `Owner` and `Pet`.

**Change made:** Added `Owner.get_all_tasks() -> list[Task]` as a single aggregation point. The Scheduler now calls one method instead of navigating two levels of the object graph. This means changes to how pets store tasks only require updating `Pet` and `Owner.get_all_tasks`, not the Scheduler itself.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints:

- **Time budget** — the owner sets a `daily_time_budget_min` (e.g., 90 minutes). Tasks are added greedily until the budget is exhausted; any remaining tasks go to `skipped_tasks`.
- **Priority** — each task has a 1–5 integer priority that seeds the urgency score. Higher-priority tasks are placed earlier in the day.
- **Medication flag** — any task with `is_medication=True` receives a +30 urgency bonus, pushing it ahead of all non-medication tasks regardless of their numeric priority.

The medication constraint was treated as the highest-importance rule because missing a dose has real health consequences — unlike a missed walk, which is inconvenient but not dangerous. That asymmetry justified a hard bonus rather than relying on users to always assign priority 5 to medications manually.

**b. Tradeoffs**

**Tradeoff: greedy urgency-first scheduling vs. optimal packing**

The scheduler sorts all tasks by urgency score (priority × 10 + medication bonus + overdue
penalty) and then fills the owner's time budget greedily — highest score first, no
backtracking. This means it can miss a better combination. For example, if the budget is
90 minutes and the top-scored task takes 85 minutes, only 5 minutes remain and several
smaller tasks get skipped, even though swapping in two 40-minute tasks would use the same
budget and serve more needs.

A true optimal solution would require evaluating all subsets (knapsack problem), which
is NP-hard and overkill for a daily pet-care app where the task count is small and the
owner's priorities are already encoded in the scores.

This tradeoff is reasonable because:
- Pet-care priorities (medications, overdue tasks) are well-captured by the urgency score,
  so the greedy order is usually the right order anyway.
- The app targets non-technical users who need a fast, deterministic result, not a
  provably optimal one.
- Skipped tasks are surfaced explicitly in `PlanResult.skipped_tasks`, so the owner can
  always reschedule them manually.

**AI simplification reviewed: `detect_conflicts`**

The original method used manual nested index loops (`for i … for j in range(i+1, …)`) to
generate every unique pair of `ScheduledItem` objects. When asked for a more Pythonic
approach, the AI suggested replacing the loops with `itertools.combinations(items, 2)` and
a list comprehension. The performance is identical (O(n²) pairs either way), but the
intent — "check every unique pair" — is stated directly rather than implied by the index
arithmetic. This suggestion was accepted and applied.

The same pattern was *considered* but *not applied* to `warn_task_conflicts`, because that
method's loop body builds multi-line warning strings with several intermediate variables.
Collapsing it into a single comprehension would make each "line" of logic harder to read,
which outweighs the brevity gain for a teaching codebase.

---

## 3. AI Collaboration

**a. How you used AI**

AI tools were used across every phase, but in different roles at each stage:

- **Phase 1 (design)** — used Copilot Chat to pressure-test the UML. Prompts like *"What methods are missing from this class diagram if I want the Scheduler to avoid knowing about Pet internals?"* surfaced the need for `Owner.get_all_tasks()` before any code was written. This was the highest-leverage use of AI in the project — fixing a design flaw costs nothing at the diagram stage and is expensive after the code is written.
- **Phase 2 (implementation)** — used inline Copilot completions for boilerplate (`@dataclass` field declarations, `uuid.uuid4()` defaults) and asked Chat to explain the `isocalendar()` API when implementing weekly recurrence. The AI wrote first drafts of `urgency_score` and `_reason_for`; both were reviewed and adjusted.
- **Phase 3 (algorithms)** — used Chat to review the `sort_by_time` sentinel approach and to suggest `itertools.combinations` for `detect_conflicts`. In both cases the AI's suggestion was evaluated before being accepted.
- **Phase 4 (testing + UI)** — used Chat with `#file:pawpal_system.py` to generate test scaffolding. The AI produced correct test structures but sometimes wrote tests that only checked the happy path; edge cases (adjacent tasks, untimed tasks, `as_needed` recurrence) were added manually.

Most effective prompt style: *"Given this method signature and docstring, what edge cases should a test cover?"* — asking for gaps rather than asking the AI to write everything.

**b. Judgment and verification**

During Phase 3, Copilot suggested rewriting `warn_task_conflicts` to use `itertools.combinations` and a nested list comprehension, producing the entire warning string inside a single expression. The suggestion was syntactically correct but compressed six lines of readable variable assignments (`a_start`, `a_end`, `a_pet`, etc.) into one dense expression. A future reader — or the developer returning to debug a conflict-detection bug — would have to mentally unpack the whole expression to understand what each component meant.

The suggestion was rejected for `warn_task_conflicts` specifically. The reasoning: readability is a design value, not a style preference. The method is already well-tested and the O(n²) loop is not a performance bottleneck for typical task counts (< 20). Making it harder to read in exchange for fewer lines is a bad trade. The `itertools.combinations` refactor *was* accepted in `detect_conflicts` because that method's body is a single boolean expression with no intermediate names to lose.

This illustrates the evaluation process used throughout: AI suggestions were accepted when they expressed the same intent more clearly, and rejected when they optimised for brevity at the cost of comprehension.

---

## 4. Testing and Verification

**a. What you tested**

The 34-test suite covers seven behavioral areas:

1. **Task completion** — `mark_completed()` stamps a timestamp; a completed task suppresses itself from future `is_due()` checks the same day.
2. **Pet task management** — `add_task()` stamps `pet_id`; `remove_task()` is a safe no-op for unknown IDs.
3. **Sorting correctness** — `sort_by_time()` returns chronological order; untimed tasks go last; the original list is not mutated.
4. **Filtering** — completion status and pet-name filters work independently and in combination; an unknown pet name returns an empty list rather than an error.
5. **Auto-recurrence** — daily tasks produce a next-day task; weekly tasks produce a next-week task; `as_needed` returns `None`; the new task has a fresh ID and the same time of day.
6. **Conflict detection** — overlapping windows produce exactly one warning; adjacent tasks do not; identical start times are flagged; untimed tasks are ignored; cross-pet conflicts are caught.
7. **Daily plan builder** — tasks exceeding the budget are skipped; medications appear first; empty inputs return a valid empty plan; `total_minutes` equals the sum of scheduled durations.

These behaviors were prioritised because they are the load-bearing logic: if sorting, recurrence, or conflict detection breaks, the entire app becomes unreliable. Simpler operations (string formatting, UUID generation) were not tested because they delegate to the standard library, which has its own test coverage.

**b. Confidence**

Confidence: **5/5** for the behaviors actually tested. The suite runs in under 0.1 s with 34/34 passing and covers normal cases, edge cases, and boundary conditions for every algorithm.

Edge cases to test next with more time:
- Tasks that span midnight (e.g., `due_at` at 23:45 with a 30-minute duration)
- An owner with 10+ pets and 50+ tasks — verifying that `sort_by_time` and `warn_task_conflicts` remain correct at scale
- `mark_task_complete` called twice on the same task (should the second call be a no-op or create a second recurrence?)
- `build_daily_plan` when two tasks have identical urgency scores — the order is currently undefined (Python's sort is stable, so it follows insertion order, but that is an implicit guarantee, not an explicit one)

---

## 5. Reflection

**a. What went well**

The cleanest part of the project was the separation between the data layer (`Owner`, `Pet`, `Task`) and the algorithm layer (`Scheduler`). Because the Scheduler accesses owner data through `Owner.get_all_tasks()` and `owner.get_available_minutes()` rather than navigating `owner.pets[i].tasks[j]` directly, every algorithm method could be tested in isolation by passing a minimal fake owner object. That made writing the 34-test suite straightforward — there was no need to construct deep, realistic object graphs for most tests.

**b. What you would improve**

The biggest limitation is that tasks have no pinned start time the user can set in the UI. The conflict detection logic is already built (`warn_task_conflicts` operates on `due_at`), but the Streamlit form has no time input field. A user who wants "walk at 7am, feeding at 8am" has to accept whatever start time the greedy planner assigns. Adding a `due_at` time picker to the task form would make conflict detection genuinely useful for day-to-day planning rather than a demonstration feature.

A secondary improvement would be to replace the greedy budget-filling algorithm with a simple priority-queue approach that backtracks when a large task would strand several smaller high-priority tasks. The current algorithm occasionally skips important tasks because the budget was consumed by one long low-urgency task that scored slightly higher.

**c. Key takeaway**

The most important thing learned about collaborating with AI on a system design project: **the AI is a fast and fluent implementer, but it does not remember your design decisions from one prompt to the next.** It will suggest technically correct code that violates a constraint you established two phases ago — for example, putting filtering logic inside `Task` instead of `Scheduler`, or suggesting a global state variable that bypasses the `Owner`-as-entry-point design. Staying effective meant keeping a written design record (the UML diagram and the reflection notes) and reading every suggestion against that record before accepting it. The AI accelerated every phase of the project; the developer's job was to ensure that acceleration stayed pointed in the right direction.

---

## 6. AI Strategy — VS Code Copilot

**Which Copilot features were most effective for building the scheduler?**

Three features stood out:

- **Inline completions for boilerplate** — `@dataclass` field declarations with `default_factory=lambda: str(uuid.uuid4())`, `Optional[datetime] = None` type annotations, and `__repr__` methods were completed accurately on the first suggestion in most cases. This saved time without introducing design risk because the generated code was easy to read and verify at a glance.
- **Chat with `#file:` context** — attaching `#file:pawpal_system.py` to Chat prompts let the AI give advice that was grounded in the actual implementation rather than generic Python patterns. Asking *"Based on my final implementation, what updates should I make to my initial UML diagram?"* produced a specific, accurate gap analysis that would have taken significant manual cross-referencing to produce unaided.
- **Test scaffolding via Chat** — prompting *"What edge cases should `warn_task_conflicts` test?"* with the method signature in context produced a useful list of cases (adjacent tasks, untimed tasks, cross-pet conflicts) that were then written as concrete `pytest` functions. The AI generated the structure; human judgment filled in the assertions.

**One AI suggestion rejected to keep the design clean**

Copilot Chat suggested adding a `conflicts: list[str]` field directly to `PlanResult` so that conflict warnings would be embedded in the plan output. The suggestion was well-intentioned — it would make conflict information easy to retrieve from the plan object — but it would couple conflict detection to plan generation. The current design keeps them separate: `warn_task_conflicts` runs on raw `Task` objects *before* a plan is generated, and the UI calls it independently. Embedding conflicts in `PlanResult` would mean the scheduler has to perform conflict detection as a side effect of building a plan, making both behaviors harder to test and reuse independently. The suggestion was rejected; `warn_task_conflicts` remained a standalone method on `Scheduler`.

**How did using separate chat sessions for different phases help?**

Each phase had a different goal and a different failure mode. Phase 1 (design) needed broad, critical feedback — questions like "what's missing?" and "what could go wrong?". A session carrying implementation context from Phase 2 would have biased those answers toward what was already built rather than what should be built. Phase 3 (algorithms) needed a session that knew the full class structure but had no attachment to any particular implementation detail, so suggestions were easier to evaluate objectively. Keeping sessions separate meant each conversation had a clean, well-scoped context, which produced more focused and reliable suggestions than a single long session where the AI's attention is divided across weeks of accumulated context.

**What it means to be the "lead architect" when working with powerful AI tools**

Being the lead architect means owning the constraints the AI cannot see: the design principles agreed on at the start, the tradeoffs already made, the reasons a previous suggestion was rejected. The AI is fast, knowledgeable, and confident — it will produce a plausible answer to almost any prompt. The architect's job is not to generate ideas but to evaluate them: Does this suggestion fit the design? Does it respect the boundaries between classes? Does it make the code easier or harder for the next person to understand?

In practice, this meant treating every AI suggestion as a pull request from a capable but context-free collaborator. Accepting it required the same review as any other PR: read it, understand it, check it against the design, run the tests, and only then merge. The AI made the project faster. The design decisions — and the responsibility for them — remained with the developer.
