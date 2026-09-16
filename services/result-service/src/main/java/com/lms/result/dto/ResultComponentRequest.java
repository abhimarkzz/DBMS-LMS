package com.lms.result.dto;

import com.lms.result.entity.ResultComponentType;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class ResultComponentRequest {
    @NotNull
    private ResultComponentType componentType;
    @NotBlank
    private String componentName;
    @NotNull
    @DecimalMin("0.0")
    private BigDecimal marksObtained;
    @NotNull
    @DecimalMin("0.01")
    private BigDecimal maxMarks;
    @NotNull
    @DecimalMin("0.01")
    @DecimalMax("100.0")
    private BigDecimal weightPercentage;
}
