package com.lms.result.dto;

import com.lms.result.entity.ResultComponentType;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@Builder
public class ComponentResponse {
    private UUID componentId;
    private ResultComponentType componentType;
    private String componentName;
    private BigDecimal marksObtained;
    private BigDecimal maxMarks;
    private BigDecimal weightPercentage;
    private OffsetDateTime createdAt;
}
