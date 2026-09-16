package com.lms.courseservice.service;

import com.lms.courseservice.dto.request.CreateCourseRequest;
import com.lms.courseservice.dto.request.UpdateCourseRequest;
import com.lms.courseservice.dto.response.CourseResponse;
import com.lms.courseservice.dto.response.PageResponse;
import com.lms.courseservice.entity.Course;
import com.lms.courseservice.exception.AppException;
import com.lms.courseservice.repository.CourseRepository;
import com.lms.courseservice.repository.EnrollmentRepository;
import com.lms.courseservice.security.AuthenticatedUser;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Course Service — Business Logic
 *
 * Rules enforced here:
 *   - Only TEACHER and ADMIN can create courses
 *   - Only the course's own teacher or an ADMIN can update it
 *   - Course code must be globally unique
 *   - Status transitions are validated (cannot un-archive a course)
 *
 * Caching:
 *   - Course details cached in Redis with key "course:{courseId}"
 *   - Cache is evicted on any write operation
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CourseService {

    private final CourseRepository courseRepository;
    private final EnrollmentRepository enrollmentRepository;

    /**
     * Create a new course.
     *
     * The teacher_id comes from the authenticated user's JWT, not the request body.
     * This prevents a teacher from creating a course attributed to another teacher.
     * Admins can create courses on behalf of any teacher via a separate admin endpoint.
     */
    @Transactional
    @PreAuthorize("hasRole('TEACHER') or hasRole('ADMIN')")
    public CourseResponse createCourse(CreateCourseRequest request, AuthenticatedUser creator) {
        if (courseRepository.existsByCourseCode(request.getCourseCode())) {
            throw AppException.courseCodeTaken(request.getCourseCode());
        }

        Course course = Course.builder()
            .courseCode(request.getCourseCode().toUpperCase())
            .courseName(request.getCourseName())
            .description(request.getDescription())
            .credits(request.getCredits())
            .department(request.getDepartment())
            .semester(request.getSemester())
            .teacherId(UUID.fromString(creator.getUserId()))
            .status(Course.CourseStatus.ACTIVE)
            .build();

        course = courseRepository.save(course);
        log.info("Course created: {} (id={})", course.getCourseCode(), course.getCourseId());

        return CourseResponse.from(course, 0L);
    }

    /**
     * Get a single course by ID.
     * Result is cached for 10 minutes (configured in application.yml).
     */
    @Cacheable(value = "courses", key = "#courseId.toString()")
    @Transactional(readOnly = true)
    public CourseResponse getCourseById(UUID courseId) {
        Course course = courseRepository.findById(courseId)
            .orElseThrow(() -> AppException.notFound("Course not found: " + courseId));

        long enrollmentCount = enrollmentRepository.countActiveByCourseId(courseId);
        return CourseResponse.from(course, enrollmentCount);
    }

    /**
     * List active courses with optional filters.
     * Supports pagination and filtering by department and semester.
     */
    @Transactional(readOnly = true)
    public PageResponse<CourseResponse> listCourses(
        int page,
        int pageSize,
        String department,
        Short semester
    ) {
        PageRequest pageable = PageRequest.of(
            page - 1,   // Spring's Page is 0-indexed, our API is 1-indexed
            pageSize,
            Sort.by("department", "courseCode")
        );

        Page<Course> coursePage = courseRepository.findActiveCourses(
            department,
            semester,
            pageable
        );

        List<CourseResponse> content = coursePage.getContent().stream()
            .map(c -> CourseResponse.from(c, enrollmentRepository.countActiveByCourseId(c.getCourseId())))
            .collect(Collectors.toList());

        return PageResponse.<CourseResponse>builder()
            .content(content)
            .page(page)
            .pageSize(pageSize)
            .totalElements(coursePage.getTotalElements())
            .totalPages(coursePage.getTotalPages())
            .last(coursePage.isLast())
            .build();
    }

    /**
     * Get all courses taught by a teacher.
     * Used for the teacher's "My Courses" dashboard view.
     */
    @Transactional(readOnly = true)
    public List<CourseResponse> getTeacherCourses(UUID teacherId) {
        return courseRepository
            .findByTeacherIdAndStatus(teacherId, Course.CourseStatus.ACTIVE)
            .stream()
            .map(c -> CourseResponse.from(c, enrollmentRepository.countActiveByCourseId(c.getCourseId())))
            .collect(Collectors.toList());
    }

    /**
     * Update course details.
     *
     * Authorization:
     *   - A teacher can only update their own course
     *   - An admin can update any course
     */
    @Transactional
    @CacheEvict(value = "courses", key = "#courseId.toString()")
    public CourseResponse updateCourse(
        UUID courseId,
        UpdateCourseRequest request,
        AuthenticatedUser requestor
    ) {
        Course course = courseRepository.findById(courseId)
            .orElseThrow(() -> AppException.notFound("Course not found: " + courseId));

        // Ownership check: teacher can only update their own course
        if (requestor.isTeacher()
                && !course.getTeacherId().toString().equals(requestor.getUserId())) {
            throw AppException.forbidden("You can only update your own courses");
        }

        if (request.getCourseName() != null) {
            course.setCourseName(request.getCourseName());
        }
        if (request.getDescription() != null) {
            course.setDescription(request.getDescription());
        }
        if (request.getCredits() != null) {
            course.setCredits(request.getCredits());
        }
        if (request.getStatus() != null) {
            course.setStatus(parseAndValidateStatus(request.getStatus()));
        }

        course = courseRepository.save(course);
        long enrollmentCount = enrollmentRepository.countActiveByCourseId(courseId);
        return CourseResponse.from(course, enrollmentCount);
    }

    /**
     * Archive a course (soft delete — data is preserved).
     * Only admins can archive courses.
     */
    @Transactional
    @CacheEvict(value = "courses", key = "#courseId.toString()")
    @PreAuthorize("hasRole('ADMIN')")
    public CourseResponse archiveCourse(UUID courseId) {
        Course course = courseRepository.findById(courseId)
            .orElseThrow(() -> AppException.notFound("Course not found: " + courseId));

        course.setStatus(Course.CourseStatus.ARCHIVED);
        course = courseRepository.save(course);
        log.info("Course archived: {}", course.getCourseCode());

        return CourseResponse.from(course, 0L);
    }

    private Course.CourseStatus parseAndValidateStatus(String statusString) {
        try {
            return Course.CourseStatus.valueOf(statusString.toUpperCase());
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest(
                "Invalid status: " + statusString + ". Must be ACTIVE, INACTIVE, or ARCHIVED"
            );
        }
    }
}
