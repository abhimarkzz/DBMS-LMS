package com.lms.courseservice.service;

import com.lms.courseservice.dto.response.EnrollmentResponse;
import com.lms.courseservice.entity.Course;
import com.lms.courseservice.entity.Enrollment;
import com.lms.courseservice.exception.AppException;
import com.lms.courseservice.repository.CourseRepository;
import com.lms.courseservice.repository.EnrollmentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Enrollment Service — Business Logic
 *
 * Rules:
 *   - A student can only enroll in ACTIVE courses
 *   - A student cannot enroll twice in the same course
 *   - Only the enrolled student or an admin can drop an enrollment
 *   - Teachers can view all students in their courses
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class EnrollmentService {

    private final CourseRepository courseRepository;
    private final EnrollmentRepository enrollmentRepository;

    /**
     * Enroll a student in a course.
     *
     * The studentId comes from the JWT (requestorId), not the request body.
     * This prevents a student from enrolling on behalf of another student.
     */
    @Transactional
    @PreAuthorize("hasRole('STUDENT') or hasRole('ADMIN')")
    public EnrollmentResponse enroll(UUID courseId, UUID studentId) {
        Course course = courseRepository.findById(courseId)
            .orElseThrow(() -> AppException.notFound("Course not found: " + courseId));

        if (course.getStatus() != Course.CourseStatus.ACTIVE) {
            throw AppException.badRequest("Cannot enroll in an inactive or archived course");
        }

        // Check for existing enrollment (any status — prevents re-enrollment after dropping)
        enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId)
            .ifPresent(existing -> {
                if (existing.getStatus() == Enrollment.EnrollmentStatus.ENROLLED) {
                    throw AppException.alreadyEnrolled();
                }
                if (existing.getStatus() == Enrollment.EnrollmentStatus.SUSPENDED) {
                    throw new AppException(
                        HttpStatus.FORBIDDEN,
                        "ENROLLMENT_SUSPENDED",
                        "Your enrollment in this course is suspended. Contact an admin."
                    );
                }
                // If DROPPED or COMPLETED, we allow re-enrollment by creating a new record
            });

        Enrollment enrollment = Enrollment.builder()
            .studentId(studentId)
            .course(course)
            .status(Enrollment.EnrollmentStatus.ENROLLED)
            .build();

        enrollment = enrollmentRepository.save(enrollment);
        log.info("Student {} enrolled in course {}", studentId, courseId);

        return EnrollmentResponse.from(enrollment);
    }

    /**
     * Drop (unenroll) a student from a course.
     *
     * Authorization:
     *   - A student can drop themselves
     *   - An admin can drop any student
     *   - A teacher cannot drop a student (use admin for that)
     */
    @Transactional
    public EnrollmentResponse dropEnrollment(UUID courseId, UUID studentId, UUID requestorId, boolean isAdmin) {
        // Non-admin students can only drop themselves
        if (!isAdmin && !studentId.equals(requestorId)) {
            throw AppException.forbidden("You can only drop your own enrollment");
        }

        int updated = enrollmentRepository.dropEnrollment(studentId, courseId);

        if (updated == 0) {
            throw AppException.notEnrolled();
        }

        log.info("Student {} dropped from course {}", studentId, courseId);

        // Reload to return the updated enrollment
        return enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId)
            .map(EnrollmentResponse::from)
            .orElseThrow(() -> AppException.notFound("Enrollment not found after drop"));
    }

    /**
     * Get all active enrollments for a course.
     * Used by teachers to see their student list.
     */
    @Transactional(readOnly = true)
    @PreAuthorize("hasRole('TEACHER') or hasRole('ADMIN')")
    public List<EnrollmentResponse> getCourseEnrollments(UUID courseId) {
        return enrollmentRepository
            .findByCourse_CourseIdAndStatus(courseId, Enrollment.EnrollmentStatus.ENROLLED)
            .stream()
            .map(EnrollmentResponse::from)
            .collect(Collectors.toList());
    }

    /**
     * Get all courses a student is enrolled in.
     */
    @Transactional(readOnly = true)
    public List<EnrollmentResponse> getStudentEnrollments(UUID studentId) {
        return courseRepository
            .findEnrolledCoursesForStudent(studentId)
            .stream()
            .map(course -> {
                Enrollment e = enrollmentRepository
                    .findByStudentIdAndCourse_CourseIdAndStatus(
                        studentId,
                        course.getCourseId(),
                        Enrollment.EnrollmentStatus.ENROLLED
                    )
                    .orElse(null);
                return e != null ? EnrollmentResponse.from(e) : null;
            })
            .filter(e -> e != null)
            .collect(Collectors.toList());
    }

    /**
     * Verify a student is enrolled in a course.
     * Used by other services as an authorization check.
     */
    @Transactional(readOnly = true)
    public boolean isStudentEnrolled(UUID studentId, UUID courseId) {
        return enrollmentRepository.existsByStudentIdAndCourse_CourseIdAndStatus(
            studentId,
            courseId,
            Enrollment.EnrollmentStatus.ENROLLED
        );
    }
}
