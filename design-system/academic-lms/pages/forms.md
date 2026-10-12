# Page Specification: Accessible Complex Forms & Builders

> **Inheritance:** Extends `../MASTER.md`. Governs Course Creator, Assessment Builder, MCQ Editor, and Upload Zones.

---

## 1. Multi-Section Form Architecture

- Tabbed or stepped sections:
  - Section 1: Basic Information (Code, Title, Descriptions, Department, Level)
  - Section 2: Academic & Instructors (Credits, Term, Prerequisites, Faculty)
  - Section 3: Structure & Modules (Learning outcomes, syllabus outline)
  - Section 4: Schedule & Capacity (Start date, end date, max enrollment)
  - Section 5: Publishing Status (Draft, Published, Archived)
- Accessible form validation:
  - Error summary placed at the top of the form with `role="alert"` and focus management.
  - Inline error text directly below invalid inputs with `aria-describedby`.
  - Required fields marked with clean `*` indicator and visible labels.

---

## 2. Assessment & Assignment Builder

- **Assessment Type Selector:**
  - Distinct radio cards: Descriptive / Essay, Multiple Choice Quiz (MCQ), Document File Submission, Audio Listening.
- **Rubric Builder (for Descriptive & File submissions):**
  - Dynamic rows: Criterion Title, Description, Maximum Points, Weighting.
  - Live total points calculation that synchronizes with assignment max score.
- **MCQ Quiz Builder:**
  - Question prompt textarea.
  - 4 option input fields (A, B, C, D) with radio selector for correct answer key.
  - Explanation textarea for post-attempt student review.
  - Per-question point value.

---

## 3. Study Material Upload Dropzone

- Drag-and-drop zone with clear file type badges (PDF, DOCX, PPTX, TXT, MD).
- File list preview before upload with filename, size, and remove button.
- Progress bar and live indexing status indicators (`PROCESSING` -> `INDEXED` / `FAILED`).
- Re-index action button on existing study material rows.
