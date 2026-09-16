package com.lms.courseservice.dto.request;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * PATCH request for updating a course.
 * All fields are optional — only non-null values are applied.
 * Teachers can update description and name; status changes are admin-only
 * (enforced in the service layer).
 */
@Data
public class UpdateCourseRequest {

    @Size(min = 3, max = 200)
    private String courseName;

    @Size(max = 5000)
    private String description;

    @Min(1) @Max(10)
    private Short credits;

    // Status changes allowed values: ACTIVE, INACTIVE, ARCHIVED
    // Validated in service — not using enum here so the API accepts string input
    private String status;
}
