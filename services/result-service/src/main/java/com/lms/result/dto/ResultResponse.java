package com.lms.result.dto;

import com.lms.result.entity.ResultStatus;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Data
@Builder
public class ResultResponse {
    private UUID resultId;
    private UUID studentId;
    private UUID courseId;
    private BigDecimal totalMarks;
    private BigDecimal maxMarks;
    private BigDecimal percentage;
    private String grade;
    private BigDecimal gradePoints;
    private ResultStatus status;
    private OffsetDateTime publishedAt;
    private OffsetDateTime calculatedAt;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private List<ComponentResponse> components;
}
