# Page Specification: AI Smart Notes Search & RAG Interface

> **Inheritance:** Extends `../MASTER.md`. Governs semantic query inputs, pgvector retrieval feedback, and grounded citation displays.

---

## 1. Query Input Area

- Full-width prominent search container:
  - Input: Accessible text field with prominent search icon, placeholder with example technical query (e.g., *"How does PostgreSQL implement MVCC under high concurrency?"*).
  - Course Scope Dropdown: Clear selector to search across "All Enrolled Courses" or scope to a specific course (e.g. `CS501`).
  - Search Button: Primary button with loading spinner during vector retrieval and model inference.
- Suggested / Sample Questions:
  - Clean pills or buttons showing real questions based on indexed materials (B-Trees, Raft Consensus, HNSW Vector Graphs, Two-Phase Commit).
  - Clicking a suggested question instantly populates the query and runs the search.

---

## 2. Results & Grounded Synthesis Card

- **Status Banner:**
  - `GROUNDED`: Soft green alert (`#f0fdf4`) with check icon: *"Answer synthesized strictly from retrieved course notes."*
  - `GUARDRAIL_REFUSAL`: Soft amber alert (`#fefce8`): *"The answer is not available in the uploaded course content."*
  - `AI_FALLBACK`: Soft blue alert (`#f0f9ff`): *"Deterministic semantic synthesis active."*
- **Synthesis Body:**
  - Well-formatted markdown with clear paragraph breaks, bold technical terminology, and clean code blocks.
  - Model and latency badge in bottom bar (e.g., `Gemini 2.5 Flash • 28ms latency` or `Deterministic-Semantic-RAG • 5.9ms`).

---

## 3. Source Citation Cards (Grounded References)

- Rendered directly below the synthesized answer in a structured grid or list.
- Each Citation Tile:
  - Note Title & Course Code badge (e.g. `[CS501] Module 3: PostgreSQL MVCC`).
  - Cosine Similarity Badge (e.g. `Similarity: 0.88` or `Cosine Distance: 0.12`).
  - Chunk preview with expandable full passage text.
  - Direct link to open the full study material in the course tab.
