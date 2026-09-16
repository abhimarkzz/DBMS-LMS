package com.lms.courseservice.dto.response;

import com.lms.courseservice.entity.Enrollment;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@Builder
public class EnrollmentResponse {

    private UUID enrollmentId;
    private UUID studentId;
    private UUID courseId;
    private String courseCode;
    private String courseName;
    private OffsetDateTime enrolledAt;
    private String status;
    private BigDecimal completionPercentage;

    public static EnrollmentResponse from(Enrollment enrollment) {
        return EnrollmentResponse.builder()
            .enrollmentId(enrollment.getEnrollmentId())
            .studentId(enrollment.getStudentId())
            .courseId(enrollment.getCourse().getCourseId())
            .courseCode(enrollment.getCourse().getCourseCode())
            .courseName(enrollment.getCourse().getCourseName())
            .enrolledAt(enrollment.getEnrolledAt())
            .status(enrollment.getStatus().name())
            .completionPercentage(enrollment.getCompletionPercentage())
            .build();
    }
}
