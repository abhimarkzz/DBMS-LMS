package com.lms.courseservice.controller;

import com.lms.courseservice.dto.response.EnrollmentResponse;
import com.lms.courseservice.security.AuthenticatedUser;
import com.lms.courseservice.service.EnrollmentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

/**
 * Enrollment Controller
 *
 * Endpoints:
 *   POST   /api/v1/enrollments/{courseId}              — Enroll self (STUDENT)
 *   DELETE /api/v1/enrollments/{courseId}              — Drop self (STUDENT/ADMIN)
 *   GET    /api/v1/enrollments/my                      — Get my enrolled courses
 *   GET    /api/v1/enrollments/courses/{courseId}      — Get all students in course (TEACHER/ADMIN)
 *   GET    /api/v1/enrollments/check/{courseId}        — Check if enrolled
 */
@RestController
@RequestMapping("/api/v1/enrollments")
@RequiredArgsConstructor
@Tag(name = "Enrollments", description = "Course enrollment management")
public class EnrollmentController {

    private final EnrollmentService enrollmentService;

    @PostMapping("/{courseId}")
    @Operation(summary = "Enroll the authenticated student in a course")
    public ResponseEntity<EnrollmentResponse> enroll(
        @PathVariable UUID courseId,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        UUID studentId = UUID.fromString(currentUser.getUserId());
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(enrollmentService.enroll(courseId, studentId));
    }

    @DeleteMapping("/{courseId}")
    @Operation(summary = "Drop enrollment in a course")
    public ResponseEntity<EnrollmentResponse> drop(
        @PathVariable UUID courseId,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        UUID requestorId = UUID.fromString(currentUser.getUserId());
        return ResponseEntity.ok(
            enrollmentService.dropEnrollment(courseId, requestorId, requestorId, currentUser.isAdmin())
        );
    }

    @GetMapping("/my")
    @Operation(summary = "Get all courses the authenticated student is enrolled in")
    public ResponseEntity<List<EnrollmentResponse>> getMyEnrollments(
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        UUID studentId = UUID.fromString(currentUser.getUserId());
        return ResponseEntity.ok(enrollmentService.getStudentEnrollments(studentId));
    }

    @GetMapping("/courses/{courseId}")
    @Operation(
        summary = "Get all enrolled students in a course",
        description = "Teacher or Admin only."
    )
    public ResponseEntity<List<EnrollmentResponse>> getCourseStudents(
        @PathVariable UUID courseId
    ) {
        return ResponseEntity.ok(enrollmentService.getCourseEnrollments(courseId));
    }

    @GetMapping("/check/{courseId}")
    @Operation(summary = "Check if the authenticated student is enrolled in a course")
    public ResponseEntity<Boolean> checkEnrollment(
        @PathVariable UUID courseId,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        UUID studentId = UUID.fromString(currentUser.getUserId());
        return ResponseEntity.ok(enrollmentService.isStudentEnrolled(studentId, courseId));
    }
}
