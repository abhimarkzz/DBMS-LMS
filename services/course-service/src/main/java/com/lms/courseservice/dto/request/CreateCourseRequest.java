package com.lms.courseservice.dto.request;

import com.lms.courseservice.entity.Course;
import jakarta.validation.constraints.*;
import lombok.Data;

/**
 * Request payload for creating a new course.
 * The teacher_id is taken from the JWT — teachers don't pass it explicitly.
 * Admins can pass teacher_id to create a course on behalf of a teacher.
 */
@Data
public class CreateCourseRequest {

    @NotBlank(message = "Course code is required")
    @Size(min = 2, max = 20, message = "Course code must be 2-20 characters")
    @Pattern(regexp = "^[A-Z]{2,4}[0-9]{2,4}$", message = "Course code must be like CS501 or ECE401")
    private String courseCode;

    @NotBlank(message = "Course name is required")
    @Size(min = 3, max = 200, message = "Course name must be 3-200 characters")
    private String courseName;

    @Size(max = 5000, message = "Description cannot exceed 5000 characters")
    private String description;

    @NotNull(message = "Credits are required")
    @Min(value = 1, message = "Credits must be at least 1")
    @Max(value = 10, message = "Credits cannot exceed 10")
    private Short credits;

    @NotBlank(message = "Department is required")
    @Size(min = 2, max = 100)
    private String department;

    @NotNull(message = "Semester is required")
    @Min(value = 1, message = "Semester must be between 1 and 12")
    @Max(value = 12, message = "Semester must be between 1 and 12")
    private Short semester;
}
