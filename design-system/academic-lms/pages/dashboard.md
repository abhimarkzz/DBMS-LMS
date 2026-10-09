# Page Specification: Academic Dashboards (Student, Teacher, Admin)

> **Inheritance:** Extends `../MASTER.md`. Governs role-specific dashboard overviews.

---

## 1. Information Density & Layout Architecture

- **Layout Grid:** 12-column responsive CSS grid with `--space-lg` (`16px`) gutters.
- **Top Metrics Row:** 4 KPI metric cards displaying live database counts:
  - *Student:* Enrolled Courses, Pending Submissions, Completed Assignments, Overall Academic Average.
  - *Teacher:* Courses Taught, Total Enrolled Students, Pending Submissions to Grade, Indexed Notes.
  - *Admin:* Active System Users, Courses in Catalog, Submissions Recorded, Polyglot Health Status.
- **Visual Style:**
  - White background (`#ffffff`), 1px solid border (`#e2e8f0`).
  - Left vertical accent bar (`3px solid var(--color-primary)` or role-specific indicator).
  - Stat label: `11.5px` uppercase bold, color `#64748b`.
  - Stat value: `24px` bold `700`, tabular numerals.
  - Supporting subtext: `11px`, color `#94a3b8`.

---

## 2. Main Work Area Split (70/30 or 60/40)

- **Primary Column (Left, 8 cols):**
  - Enrolled / Taught Courses overview with progress bars, course codes, and direct syllabus links.
  - Active submission queues or upcoming assessment deadlines.
- **Secondary Column (Right, 4 cols):**
  - Real-time MongoDB notifications and announcements stream.
  - Academic calendar / schedule milestones.
  - Quick actions panel (Submit Assignment, Upload Notes, Open AI Search).

---

## 3. Empty & Loading States

- Skeleton loaders matching card aspect ratios during initial fetch.
- Empty states must provide actionable guidance:
  - Example: "No assignments pending. You are caught up across all 4 enrolled courses."
  - Includes a direct button to browse courses or explore course materials.
