package com.lms.result.service;

import com.lms.result.dto.ResultComponentRequest;
import com.lms.result.dto.ResultResponse;
import com.lms.result.entity.CourseResult;
import com.lms.result.entity.ResultComponent;
import com.lms.result.entity.ResultComponentType;
import com.lms.result.entity.ResultStatus;
import com.lms.result.repository.CourseResultRepository;
import com.lms.result.repository.ResultComponentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ResultServiceTest {

    @Mock
    private CourseResultRepository courseResultRepository;

    @Mock
    private ResultComponentRepository resultComponentRepository;

    @InjectMocks
    private ResultService resultService;

    private CourseResult mockResult;
    private UUID resultId;

    @BeforeEach
    void setUp() {
        resultId = UUID.randomUUID();
        mockResult = CourseResult.builder()
                .resultId(resultId)
                .courseId(UUID.randomUUID())
                .studentId(UUID.randomUUID())
                .status(ResultStatus.PENDING)
                .components(new ArrayList<>())
                .build();
    }

    @Test
    void testCalculateResult_A_Plus() {
        when(courseResultRepository.findById(resultId)).thenReturn(Optional.of(mockResult));
        when(courseResultRepository.save(any(CourseResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResultComponent comp1 = ResultComponent.builder()
                .marksObtained(new BigDecimal("45.00"))
                .maxMarks(new BigDecimal("50.00"))
                .weightPercentage(new BigDecimal("50.00"))
                .build();
        ResultComponent comp2 = ResultComponent.builder()
                .marksObtained(new BigDecimal("95.00"))
                .maxMarks(new BigDecimal("100.00"))
                .weightPercentage(new BigDecimal("50.00"))
                .build();
        mockResult.getComponents().add(comp1);
        mockResult.getComponents().add(comp2);

        ResultResponse response = resultService.calculateResult(resultId);

        assertEquals(new BigDecimal("92.5000"), response.getPercentage());
        assertEquals("A+", response.getGrade());
        assertEquals(new BigDecimal("10.0"), response.getGradePoints());
    }

    @Test
    void testCalculateResult_F() {
        when(courseResultRepository.findById(resultId)).thenReturn(Optional.of(mockResult));
        when(courseResultRepository.save(any(CourseResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResultComponent comp1 = ResultComponent.builder()
                .marksObtained(new BigDecimal("15.00"))
                .maxMarks(new BigDecimal("50.00"))
                .weightPercentage(new BigDecimal("100.00"))
                .build();
        mockResult.getComponents().add(comp1);

        ResultResponse response = resultService.calculateResult(resultId);

        assertEquals(new BigDecimal("30.0000"), response.getPercentage());
        assertEquals("F", response.getGrade());
        assertEquals(new BigDecimal("0.0"), response.getGradePoints());
    }
}
