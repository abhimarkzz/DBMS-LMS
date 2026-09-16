package com.lms.courseservice.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * Base class for application-defined exceptions.
 * Mirrors the pattern from the User Service for consistency.
 * All custom exceptions carry an HTTP status and an error code.
 */
@Getter
public class AppException extends RuntimeException {

    private final HttpStatus status;
    private final String code;

    public AppException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    // ---- Static factory methods for common cases ----

    public static AppException notFound(String message) {
        return new AppException(HttpStatus.NOT_FOUND, "NOT_FOUND", message);
    }

    public static AppException conflict(String message) {
        return new AppException(HttpStatus.CONFLICT, "CONFLICT", message);
    }

    public static AppException forbidden(String message) {
        return new AppException(HttpStatus.FORBIDDEN, "PERMISSION_DENIED", message);
    }

    public static AppException badRequest(String message) {
        return new AppException(HttpStatus.BAD_REQUEST, "BAD_REQUEST", message);
    }

    public static AppException courseNotFound(String courseCode) {
        return new AppException(
            HttpStatus.NOT_FOUND,
            "COURSE_NOT_FOUND",
            "Course not found: " + courseCode
        );
    }

    public static AppException courseCodeTaken(String courseCode) {
        return new AppException(
            HttpStatus.CONFLICT,
            "COURSE_CODE_TAKEN",
            "Course code is already in use: " + courseCode
        );
    }

    public static AppException alreadyEnrolled() {
        return new AppException(
            HttpStatus.CONFLICT,
            "ALREADY_ENROLLED",
            "Student is already enrolled in this course"
        );
    }

    public static AppException notEnrolled() {
        return new AppException(
            HttpStatus.FORBIDDEN,
            "NOT_ENROLLED",
            "Student is not enrolled in this course"
        );
    }
}
