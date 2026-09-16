package com.lms.courseservice.repository;

import com.lms.courseservice.entity.Enrollment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface EnrollmentRepository extends JpaRepository<Enrollment, UUID> {

    /**
     * Find active enrollment for a student in a specific course.
     * Used to verify enrollment before submission, search authorization, etc.
     */
    Optional<Enrollment> findByStudentIdAndCourse_CourseIdAndStatus(
        UUID studentId,
        UUID courseId,
        Enrollment.EnrollmentStatus status
    );

    /**
     * Find any enrollment (regardless of status) for duplicate check.
     */
    Optional<Enrollment> findByStudentIdAndCourse_CourseId(UUID studentId, UUID courseId);

    /**
     * Count active students in a course. Used for course overview stats.
     */
    @Query("""
        SELECT COUNT(e) FROM Enrollment e
        WHERE e.course.courseId = :courseId AND e.status = 'ENROLLED'
        """)
    long countActiveByCourseId(@Param("courseId") UUID courseId);

    /**
     * Get all enrollments for a course (for teacher's student list).
     */
    List<Enrollment> findByCourse_CourseIdAndStatus(UUID courseId, Enrollment.EnrollmentStatus status);

    /**
     * Check if a student is actively enrolled in a course.
     * Used as an authorization gate (student can only access their enrolled courses).
     */
    boolean existsByStudentIdAndCourse_CourseIdAndStatus(
        UUID studentId,
        UUID courseId,
        Enrollment.EnrollmentStatus status
    );

    /**
     * Update enrollment status to DROPPED without loading the entity.
     * Using @Modifying + @Query for a direct UPDATE — avoids loading the entity,
     * modifying it, and flushing, which is 3x the work for a simple status change.
     */
    @Modifying
    @Query("""
        UPDATE Enrollment e
        SET e.status = 'DROPPED', e.updatedAt = CURRENT_TIMESTAMP
        WHERE e.studentId = :studentId
          AND e.course.courseId = :courseId
          AND e.status = 'ENROLLED'
        """)
    int dropEnrollment(@Param("studentId") UUID studentId, @Param("courseId") UUID courseId);
}
