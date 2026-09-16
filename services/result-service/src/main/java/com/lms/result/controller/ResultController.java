package com.lms.result.controller;

import com.lms.result.dto.ResultComponentRequest;
import com.lms.result.dto.ResultResponse;
import com.lms.result.security.AuthenticatedUser;
import com.lms.result.service.ResultService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/results")
@RequiredArgsConstructor
public class ResultController {

    private final ResultService resultService;

    @PostMapping("/course/{courseId}/student/{studentId}")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public ResultResponse initializeResult(@PathVariable UUID courseId, @PathVariable UUID studentId) {
        return resultService.initializeResult(courseId, studentId);
    }

    @PostMapping("/{resultId}/components")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public ResultResponse addComponent(@PathVariable UUID resultId, @Valid @RequestBody ResultComponentRequest request) {
        return resultService.addComponent(resultId, request);
    }

    @PostMapping("/{resultId}/calculate")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public ResultResponse calculateResult(@PathVariable UUID resultId) {
        return resultService.calculateResult(resultId);
    }

    @PatchMapping("/{resultId}/publish")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public ResultResponse publishResult(@PathVariable UUID resultId) {
        return resultService.publishResult(resultId);
    }

    @GetMapping("/course/{courseId}/student/{studentId}")
    public ResultResponse getResultForStudent(
            @PathVariable UUID courseId, 
            @PathVariable UUID studentId,
            @AuthenticationPrincipal AuthenticatedUser user) {
        
        // RBAC: Only TEACHER/ADMIN can view any student's result.
        // A STUDENT can only view their own result.
        if (user.getRole().equals("STUDENT") && !user.getUserId().equals(studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Students can only view their own results.");
        }
        
        return resultService.getResultForStudent(courseId, studentId);
    }

    @GetMapping("/course/{courseId}")
    @PreAuthorize("hasAnyRole('TEACHER', 'ADMIN')")
    public List<ResultResponse> getResultsForCourse(@PathVariable UUID courseId) {
        return resultService.getResultsForCourse(courseId);
    }
}
