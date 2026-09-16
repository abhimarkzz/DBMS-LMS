package com.lms.courseservice.repository;

import com.lms.courseservice.entity.Course;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for courses.
 *
 * Spring generates the SQL for standard methods at startup.
 * Complex queries (with JOINs or multiple filters) use @Query with JPQL.
 *
 * JPQL operates on entity names and field names, not table/column names.
 * This means Hibernate handles dialect differences transparently.
 */
@Repository
public interface CourseRepository extends JpaRepository<Course, UUID> {

    /**
     * Find a course by its course code (e.g., "CS501").
     * Used for uniqueness checks during creation.
     */
    Optional<Course> findByCourseCode(String courseCode);

    boolean existsByCourseCode(String courseCode);

    /**
     * List all active courses with optional department filter.
     * Used for the public course catalog.
     *
     * JPQL note: (:department IS NULL OR c.department = :department)
     *   allows the same query to work with or without a department filter.
     */
    @Query("""
        SELECT c FROM Course c
        WHERE c.status = 'ACTIVE'
          AND (:department IS NULL OR c.department = :department)
          AND (:semester IS NULL OR c.semester = :semester)
        ORDER BY c.department, c.courseCode
        """)
    Page<Course> findActiveCourses(
        @Param("department") String department,
        @Param("semester") Short semester,
        Pageable pageable
    );

    /**
     * Find all courses taught by a specific teacher.
     * Used for the teacher's dashboard ("My Courses").
     */
    List<Course> findByTeacherIdAndStatus(UUID teacherId, Course.CourseStatus status);

    /**
     * Find courses a student is enrolled in.
     * Joins through the enrollments table to find the student's active courses.
     */
    @Query("""
        SELECT c FROM Course c
        JOIN c.enrollments e
        WHERE e.studentId = :studentId
          AND e.status = 'ENROLLED'
          AND c.status = 'ACTIVE'
        ORDER BY c.semester DESC, c.courseCode
        """)
    List<Course> findEnrolledCoursesForStudent(@Param("studentId") UUID studentId);

    /**
     * Check if a course code is already taken (excluding the current course for updates).
     */
    @Query("""
        SELECT COUNT(c) > 0 FROM Course c
        WHERE c.courseCode = :courseCode AND c.courseId != :excludeCourseId
        """)
    boolean existsByCourseCodeAndCourseIdNot(
        @Param("courseCode") String courseCode,
        @Param("excludeCourseId") UUID excludeCourseId
    );
}
