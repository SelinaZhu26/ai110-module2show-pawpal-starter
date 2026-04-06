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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
