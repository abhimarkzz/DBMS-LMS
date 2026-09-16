package com.lms.courseservice.controller;

import com.lms.courseservice.dto.request.CreateAnnouncementRequest;
import com.lms.courseservice.dto.request.CreateCourseRequest;
import com.lms.courseservice.dto.request.UpdateCourseRequest;
import com.lms.courseservice.dto.response.AnnouncementResponse;
import com.lms.courseservice.dto.response.CourseResponse;
import com.lms.courseservice.dto.response.PageResponse;
import com.lms.courseservice.security.AuthenticatedUser;
import com.lms.courseservice.service.AnnouncementService;
import com.lms.courseservice.service.CourseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

/**
 * Course Controller
 *
 * Endpoints:
 *   GET    /api/v1/courses                           — Public course catalog
 *   POST   /api/v1/courses                           — Create course (TEACHER/ADMIN)
 *   GET    /api/v1/courses/{courseId}                — Get course detail
 *   PATCH  /api/v1/courses/{courseId}                — Update course (teacher/admin)
 *   DELETE /api/v1/courses/{courseId}                — Archive course (ADMIN)
 *   GET    /api/v1/courses/my                        — Teacher's own courses
 *   GET    /api/v1/courses/{courseId}/announcements  — Course announcements
 *   POST   /api/v1/courses/{courseId}/announcements  — Create announcement
 *   DELETE /api/v1/courses/announcements/{id}        — Delete announcement
 *
 * The controller is thin — it extracts data from the request, delegates to
 * the service, and returns the response. No business logic here.
 */
@RestController
@RequestMapping("/api/v1/courses")
@RequiredArgsConstructor
@Tag(name = "Courses", description = "Course management endpoints")
public class CourseController {

    private final CourseService courseService;
    private final AnnouncementService announcementService;

    @GetMapping
    @Operation(summary = "List active courses", description = "Public endpoint. Supports optional department and semester filters.")
    public ResponseEntity<PageResponse<CourseResponse>> listCourses(
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "20") int pageSize,
        @RequestParam(required = false) String department,
        @RequestParam(required = false) Short semester
    ) {
        return ResponseEntity.ok(
            courseService.listCourses(page, pageSize, department, semester)
        );
    }

    @PostMapping
    @Operation(summary = "Create a new course", description = "Teacher or Admin only.")
    public ResponseEntity<CourseResponse> createCourse(
        @Valid @RequestBody CreateCourseRequest request,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(courseService.createCourse(request, currentUser));
    }

    @GetMapping("/{courseId}")
    @Operation(summary = "Get course details by ID")
    public ResponseEntity<CourseResponse> getCourse(@PathVariable UUID courseId) {
        return ResponseEntity.ok(courseService.getCourseById(courseId));
    }

    @PatchMapping("/{courseId}")
    @Operation(summary = "Update a course", description = "Teacher can update their own course. Admin can update any.")
    public ResponseEntity<CourseResponse> updateCourse(
        @PathVariable UUID courseId,
        @Valid @RequestBody UpdateCourseRequest request,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return ResponseEntity.ok(courseService.updateCourse(courseId, request, currentUser));
    }

    @DeleteMapping("/{courseId}")
    @Operation(summary = "Archive a course (Admin only)")
    public ResponseEntity<CourseResponse> archiveCourse(
        @PathVariable UUID courseId,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return ResponseEntity.ok(courseService.archiveCourse(courseId));
    }

    @GetMapping("/my")
    @Operation(summary = "Get courses taught by the authenticated teacher")
    public ResponseEntity<List<CourseResponse>> getMyCourses(
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return ResponseEntity.ok(
            courseService.getTeacherCourses(UUID.fromString(currentUser.getUserId()))
        );
    }

    // ---- Announcements ----

    @GetMapping("/{courseId}/announcements")
    @Operation(summary = "Get all announcements for a course")
    public ResponseEntity<List<AnnouncementResponse>> getCourseAnnouncements(
        @PathVariable UUID courseId
    ) {
        return ResponseEntity.ok(announcementService.getCourseAnnouncements(courseId));
    }

    @PostMapping("/{courseId}/announcements")
    @Operation(summary = "Post an announcement in a course", description = "Teacher or Admin only.")
    public ResponseEntity<AnnouncementResponse> createAnnouncement(
        @PathVariable UUID courseId,
        @Valid @RequestBody CreateAnnouncementRequest request,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(announcementService.createAnnouncement(courseId, request, currentUser));
    }

    @DeleteMapping("/announcements/{announcementId}")
    @Operation(summary = "Delete an announcement")
    public ResponseEntity<Void> deleteAnnouncement(
        @PathVariable UUID announcementId,
        @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        announcementService.deleteAnnouncement(announcementId, currentUser);
        return ResponseEntity.noContent().build();
    }
}
