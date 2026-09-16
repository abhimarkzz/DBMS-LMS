# LMS SQL Examples

As requested by the Master Prompt, here are real-world SQL examples demonstrating complex querying capabilities using the actual schema.

## 1. Window Functions: Rank Students by Course Performance

```sql
SELECT 
    e.course_id,
    e.student_id,
    c.course_name,
    u.first_name || ' ' || u.last_name AS student_name,
    e.completion_percentage,
    RANK() OVER(PARTITION BY e.course_id ORDER BY e.completion_percentage DESC) as rank
FROM enrollments e
JOIN student_profiles sp ON e.student_id = sp.student_id
JOIN users u ON sp.user_id = u.user_id
JOIN courses c ON e.course_id = c.course_id;
```

## 2. CTEs: Find Students Scoring Above Average in an Assignment

```sql
WITH AssignmentAverages AS (
    SELECT 
        assignment_id, 
        AVG(marks_obtained) as avg_marks
    FROM submission_grades
    GROUP BY assignment_id
)
SELECT 
    sg.submission_id,
    sg.marks_obtained,
    aa.avg_marks,
    u.first_name,
    a.title as assignment_title
FROM submission_grades sg
JOIN AssignmentAverages aa ON sg.assignment_id = aa.assignment_id
JOIN submissions s ON sg.submission_id = s.submission_id
JOIN student_profiles sp ON s.student_id = sp.student_id
JOIN users u ON sp.user_id = u.user_id
JOIN assignments a ON sg.assignment_id = a.assignment_id
WHERE sg.marks_obtained > aa.avg_marks;
```

## 3. Subqueries & Aggregates: Find Courses with Most Enrollments

```sql
SELECT 
    c.course_name, 
    c.course_code,
    (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.course_id) as total_enrollments
FROM courses c
ORDER BY total_enrollments DESC
LIMIT 5;
```

## 4. pgvector Semantic Search (Cosine Similarity)

```sql
-- Finds the 5 most semantically similar chunks of text to a given embedding,
-- restricting the search to courses the student is allowed to see.
SELECT 
    mc.chunk_id,
    mc.content,
    cm.title,
    1 - (mc.embedding <=> '[0.1, 0.2, ...]') AS similarity_score
FROM material_chunks mc
JOIN course_materials cm ON mc.material_id = cm.material_id
WHERE cm.course_id IN ('UUID-1', 'UUID-2')
ORDER BY mc.embedding <=> '[0.1, 0.2, ...]'
LIMIT 5;
```
