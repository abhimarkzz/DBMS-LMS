# Page Specification: Results & Teacher Gradebook

> **Inheritance:** Extends `../MASTER.md`. Governs grading, evaluation matrices, and student performance views.

---

## 1. Gradebook Grid Table (Matrix View)

- **Structure:**
  - Rows: Students enrolled in the course (sorted by Name or Student ID).
  - Columns: Specific Assessments (MCQs, Descriptive, Files, Audio) + Course Total Points + Percentage + Letter Grade.
- **Header:** Sticky top header with subtle gray background (`#f8fafc`), bottom border `2px solid #cbd5e1`.
- **First Column (Student Name & ID):** Sticky left column when scrolling horizontally across many assessments.
- **Cell Content:**
  - Graded: Point score displayed cleanly (e.g. `85 / 100`) with letter grade badge (`A`, `B+`, etc.).
  - Submitted / Needs Grading: Amber highlight with click-to-evaluate action button.
  - Not Submitted / Missing: Subtle muted dash (`—`) or overdue badge.

---

## 2. Evaluation / Grading Drawer & Modal

- Split-pane review:
  - Left pane: Student submission content, uploaded document preview, or inline audio player.
  - Right pane: Rubric criteria breakdown, per-criterion score inputs, feedback textarea.
- Dual Action Buttons:
  - "Save Grade Draft" (Secondary button, stores provisional marks without publishing).
  - "Publish Result" (Primary Oxford Blue button, executes PostgreSQL stored procedure, recalculates course standings, updates leaderboard, and sends MongoDB notification).
- Input Validation:
  - Strict client and server guards: reject negative marks or scores exceeding maximum points.

---

## 3. Class Analytics & Window Functions

- Metric cards above table:
  - Class Average Score (computed via relational aggregate).
  - Highest / Lowest Score in Cohort.
  - Graded vs Pending Submissions count.
- Leaderboard view:
  - Utilizes PostgreSQL `RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)` window function.
  - Shows rank badge (Rank 1, 2, 3) and above-average indicators.
