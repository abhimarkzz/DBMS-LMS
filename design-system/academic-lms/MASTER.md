# Academic LMS Design System Master Specification

> **LOGIC:** This is the project's permanent design system generated and verified with UI/UX Pro Max.
> Follow these strict rules across all current and future screens.

---

**Project:** AI-Powered Distributed Learning Management System  
**Aesthetic Profile:** Dignified University Academic (Ivy League / Oxford Blue + Crisp Slate)  
**Tone:** Calm, Credible, Rigorous, Practical, Human-Designed, Information-Dense  
**Dial Settings:** Visual Density: 8/10 (Dense Academic UI) | Variance: 2/10 (Structured & Orderly) | Motion: 1/10 (Subtle & Functional)

---

## 1. Global Color Tokens

| Role | Hex | CSS Variable | Semantic Usage |
|:---|:---|:---|:---|
| **Primary** | `#1e3a8a` | `--color-primary` | Main academic branding, active tabs, primary actions |
| **Primary Hover** | `#172554` | `--color-primary-hover` | Button hover, focused interactive elements |
| **Primary Subtle** | `#eff6ff` | `--color-primary-light` | Active nav items, selected table rows, info banners |
| **Academic Accent** | `#0f172a` | `--color-accent` | Heavy headings, modal titles, crest background |
| **Canvas Background** | `#f8fafc` | `--color-bg-app` | App background, contrast with white cards |
| **Surface / Card** | `#ffffff` | `--color-bg-surface` | Data cards, tables, modal containers, dropdowns |
| **Subtle Neutral** | `#f1f5f9` | `--color-bg-subtle` | Table headers, code blocks, read notifications |
| **Border Default** | `#e2e8f0` | `--color-border` | Standard 1px dividers, card outlines, table borders |
| **Border Emphasized** | `#cbd5e1` | `--color-border-dark` | Input borders, active focus outlines, tab underlines |
| **Text Primary** | `#0f172a` | `--color-text-main` | High-contrast body, table cell text, user names |
| **Text Secondary** | `#334155` | `--color-text-muted` | Descriptions, labels, table subtitles |
| **Text Muted** | `#64748b` | `--color-text-light` | Timestamps, metadata, footnotes, breadcrumbs |
| **Academic Success** | `#15803d` | `--color-success` | Passing grades (A/B), indexed notes, completed status |
| **Success Subtle** | `#f0fdf4` | `--color-success-bg` | Success badges, verified citation cards |
| **Academic Warning** | `#b45309` | `--color-warning` | Pending reviews, upcoming deadlines, draft courses |
| **Warning Subtle** | `#fefce8` | `--color-warning-bg` | Warning badges, pending status rows |
| **Academic Danger** | `#b91c1c` | `--color-danger` | System errors, failing grades (F), delete actions |
| **Danger Subtle** | `#fef2f2` | `--color-danger-bg` | Error summary callouts, overdue badges |

---

## 2. Typography Rules

- **Sans Font:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Monospace Font:** `'JetBrains Mono', 'Fira Code', Menlo, monospace` (used for course codes `CS501`, grades, points, JSON metadata, latencies)
- **Hierarchy Scale:**
  - Page Titles: `20px` (Weight 600, letter-spacing: `-0.02em`)
  - Section Headings: `16px` – `17px` (Weight 600, letter-spacing: `-0.015em`)
  - Component Titles / Card Headers: `14px` (Weight 600)
  - Body Text / Table Content: `13px` – `13.5px` (Weight 400–500, line-height `1.5`)
  - Metadata / Captions / Badges: `11px` – `12px` (Weight 500)
  - Numeric Counters & KPIs: `22px` – `26px` (Weight 700, font-variant-numeric: `tabular-nums`)

---

## 3. Density & Spacing System (Density 8/10)

- Tight and space-efficient for desktop browser usage:
  - `--space-xs`: `4px`
  - `--space-sm`: `8px`
  - `--space-md`: `12px`
  - `--space-lg`: `16px`
  - `--space-xl`: `20px`
  - `--space-2xl`: `28px`
- **Corner Radii:** Restrained and academic (NO giant bubbles or pill cards):
  - `--radius-sm`: `4px` (buttons, badges, inputs)
  - `--radius-md`: `6px` (cards, dropdown menus, alert banners)
  - `--radius-lg`: `8px` (modals, major section wrappers)
- **Shadows:** Minimal, crisp, non-blurry:
  - `--shadow-sm`: `0 1px 2px 0 rgba(0, 0, 0, 0.04)`
  - `--shadow-md`: `0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04)`
  - `--shadow-modal`: `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)`

---

## 4. Academic UI Component Standards

### A. Tables (Gradebooks, Submissions, User Directory)
- Dense row height (`36px`–`42px`).
- Header: `#f8fafc`, uppercase or title case, font-size `11.5px`, bold `600`, letter-spacing `0.04em`, bottom border `1px solid var(--color-border)`.
- Alternate / Hover rows: Hover background `#f8fafc`, smooth transition `100ms`.
- Numeric columns: Right-aligned with tabular numerals.
- Horizontal scroll container with sticky headers and left column pinning when scrolling wide matrices.

### B. Cards & Metric Tiles
- Background `#ffffff`, border `1px solid var(--color-border)`.
- Left accent indicator (e.g. `3px solid var(--color-primary)`).
- Metric titles: uppercase `11.5px` with muted color `#64748b`.
- Numbers: bold `22px`–`24px` with clear label underneath.

### C. Forms & Complex Builders
- Clear field labels above inputs (`12.5px`, bold `500`).
- Helper text / instructions placed directly below label (`11.5px`, color `#64748b`).
- Explicit focus outline: `2px solid var(--color-primary)`.
- Action bar: Bottom-aligned or floating bar with distinct secondary ("Save Draft") and primary ("Publish Assessment") actions.

### D. Badges & Status Indicators
- Rectangular with slight rounding (`radius 4px`), NOT circular pills.
- Font-size `11px`, padding `2px 8px`, weight `500`.
- Colors:
  - `PUBLISHED` / `GRADED` / `INDEXED`: green text on `#f0fdf4`
  - `DRAFT` / `PENDING` / `SUBMITTED`: amber/blue on subtle background
  - `ARCHIVED` / `INACTIVE`: slate on `#f1f5f9`

---

## 5. Strict Anti-Patterns (Violations to Reject)

1. ❌ **No Floating Blobs or Blurs**: Reject background gradient spheres.
2. ❌ **No Neon or Cyberpunk Colors**: Pure Oxford blues, slates, deep greens, and warm ambers only.
3. ❌ **No Glassmorphism on Reading Surfaces**: No translucent backgrounds with blur on course text or tables.
4. ❌ **No Placeholder Data**: Every number, date, badge, and table cell must represent live database queries.
5. ❌ **No AI Sparkle Animations**: AI tools must look like institutional research indexing systems, not toy assistants.
6. ❌ **No Dead Buttons**: Every action must have working handlers, loading states, and success toasts.
