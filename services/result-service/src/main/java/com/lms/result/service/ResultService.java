package com.lms.result.service;

import com.lms.result.dto.ComponentResponse;
import com.lms.result.dto.ResultComponentRequest;
import com.lms.result.dto.ResultResponse;
import com.lms.result.entity.CourseResult;
import com.lms.result.entity.ResultComponent;
import com.lms.result.entity.ResultStatus;
import com.lms.result.repository.CourseResultRepository;
import com.lms.result.repository.ResultComponentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ResultService {

    private final CourseResultRepository courseResultRepository;
    private final ResultComponentRepository resultComponentRepository;

    @Transactional
    public ResultResponse initializeResult(UUID courseId, UUID studentId) {
        if (courseResultRepository.findByStudentIdAndCourseId(studentId, courseId).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Result already initialized for this student and course");
        }
        CourseResult result = CourseResult.builder()
                .courseId(courseId)
                .studentId(studentId)
                .status(ResultStatus.PENDING)
                .build();
        return mapToResponse(courseResultRepository.save(result));
    }

    @Transactional
    public ResultResponse addComponent(UUID resultId, ResultComponentRequest request) {
        CourseResult result = courseResultRepository.findById(resultId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Result not found"));

        if (result.getStatus() == ResultStatus.PUBLISHED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Cannot add components to a published result");
        }

        ResultComponent component = ResultComponent.builder()
                .courseResult(result)
                .componentType(request.getComponentType())
                .componentName(request.getComponentName())
                .marksObtained(request.getMarksObtained())
                .maxMarks(request.getMaxMarks())
                .weightPercentage(request.getWeightPercentage())
                .build();

        resultComponentRepository.save(component);
        return calculateResult(resultId);
    }

    @Transactional
    public ResultResponse calculateResult(UUID resultId) {
        CourseResult result = courseResultRepository.findById(resultId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Result not found"));

        if (result.getStatus() == ResultStatus.PUBLISHED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Cannot recalculate a published result");
        }

        List<ResultComponent> components = result.getComponents();
        if (components == null || components.isEmpty()) {
            return mapToResponse(result);
        }

        BigDecimal totalWeightedScore = BigDecimal.ZERO;
        BigDecimal totalWeight = BigDecimal.ZERO;

        for (ResultComponent comp : components) {
            BigDecimal ratio = comp.getMarksObtained().divide(comp.getMaxMarks(), 4, RoundingMode.HALF_UP);
            BigDecimal weighted = ratio.multiply(comp.getWeightPercentage());
            totalWeightedScore = totalWeightedScore.add(weighted);
            totalWeight = totalWeight.add(comp.getWeightPercentage());
        }

        result.setTotalMarks(totalWeightedScore);
        result.setMaxMarks(totalWeight);

        if (totalWeight.compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal percentage = totalWeightedScore.divide(totalWeight, 4, RoundingMode.HALF_UP).multiply(new BigDecimal("100"));
            result.setPercentage(percentage);
            assignGrade(result, percentage);
        }

        result.setCalculatedAt(OffsetDateTime.now());
        return mapToResponse(courseResultRepository.save(result));
    }

    private void assignGrade(CourseResult result, BigDecimal percentage) {
        if (percentage.compareTo(new BigDecimal("90")) >= 0) {
            result.setGrade("A+");
            result.setGradePoints(new BigDecimal("10.0"));
        } else if (percentage.compareTo(new BigDecimal("80")) >= 0) {
            result.setGrade("A");
            result.setGradePoints(new BigDecimal("9.0"));
        } else if (percentage.compareTo(new BigDecimal("70")) >= 0) {
            result.setGrade("B+");
            result.setGradePoints(new BigDecimal("8.0"));
        } else if (percentage.compareTo(new BigDecimal("60")) >= 0) {
            result.setGrade("B");
            result.setGradePoints(new BigDecimal("7.0"));
        } else if (percentage.compareTo(new BigDecimal("50")) >= 0) {
            result.setGrade("C");
            result.setGradePoints(new BigDecimal("6.0"));
        } else if (percentage.compareTo(new BigDecimal("40")) >= 0) {
            result.setGrade("D");
            result.setGradePoints(new BigDecimal("5.0"));
        } else {
            result.setGrade("F");
            result.setGradePoints(new BigDecimal("0.0"));
        }
    }

    @Transactional
    public ResultResponse publishResult(UUID resultId) {
        CourseResult result = courseResultRepository.findById(resultId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Result not found"));
        
        result.setStatus(ResultStatus.PUBLISHED);
        result.setPublishedAt(OffsetDateTime.now());
        return mapToResponse(courseResultRepository.save(result));
    }

    @Transactional(readOnly = true)
    public ResultResponse getResultForStudent(UUID courseId, UUID studentId) {
        CourseResult result = courseResultRepository.findByStudentIdAndCourseId(studentId, courseId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Result not found"));
        return mapToResponse(result);
    }

    @Transactional(readOnly = true)
    public List<ResultResponse> getResultsForCourse(UUID courseId) {
        return courseResultRepository.findByCourseId(courseId).stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    private ResultResponse mapToResponse(CourseResult result) {
        List<ComponentResponse> compResponses = null;
        if (result.getComponents() != null) {
            compResponses = result.getComponents().stream().map(c -> ComponentResponse.builder()
                    .componentId(c.getComponentId())
                    .componentType(c.getComponentType())
                    .componentName(c.getComponentName())
                    .marksObtained(c.getMarksObtained())
                    .maxMarks(c.getMaxMarks())
                    .weightPercentage(c.getWeightPercentage())
                    .createdAt(c.getCreatedAt())
                    .build()).collect(Collectors.toList());
        }

        return ResultResponse.builder()
                .resultId(result.getResultId())
                .studentId(result.getStudentId())
                .courseId(result.getCourseId())
                .totalMarks(result.getTotalMarks())
                .maxMarks(result.getMaxMarks())
                .percentage(result.getPercentage())
                .grade(result.getGrade())
                .gradePoints(result.getGradePoints())
                .status(result.getStatus())
                .publishedAt(result.getPublishedAt())
                .calculatedAt(result.getCalculatedAt())
                .createdAt(result.getCreatedAt())
                .updatedAt(result.getUpdatedAt())
                .components(compResponses)
                .build();
    }
}
