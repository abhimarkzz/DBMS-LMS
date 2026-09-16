package com.lms.courseservice.dto.response;

import com.lms.courseservice.entity.Course;
import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Response DTO for a course.
 *
 * Using a DTO (not the entity directly) keeps the API contract independent
 * of the database schema. We can add computed fields (enrollmentCount)
 * without changing the entity.
 *
 * Note: We deliberately don't nest enrollments here to avoid N+1 queries.
 *       The enrollment list is a separate endpoint.
 */
@Data
@Builder
public class CourseResponse {

    private UUID courseId;
    private String courseCode;
    private String courseName;
    private String description;
    private Short credits;
    private String department;
    private Short semester;
    private UUID teacherId;
    private String status;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    // Computed stat (populated by service layer, not from entity directly)
    private Long enrollmentCount;

    /**
     * Convert a Course entity to this DTO.
     * The enrollmentCount must be passed separately since it requires a DB query.
     */
    public static CourseResponse from(Course course, Long enrollmentCount) {
        return CourseResponse.builder()
            .courseId(course.getCourseId())
            .courseCode(course.getCourseCode())
            .courseName(course.getCourseName())
            .description(course.getDescription())
            .credits(course.getCredits())
            .department(course.getDepartment())
            .semester(course.getSemester())
            .teacherId(course.getTeacherId())
            .status(course.getStatus().name())
            .createdAt(course.getCreatedAt())
            .updatedAt(course.getUpdatedAt())
            .enrollmentCount(enrollmentCount)
            .build();
    }

    public static CourseResponse from(Course course) {
        return from(course, null);
    }
}
