package com.lms.courseservice.security;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * Holds the authenticated user's identity extracted from the JWT.
 * Available via SecurityContextHolder or @AuthenticationPrincipal in controllers.
 *
 * We use a dedicated class (not Spring's UserDetails) because:
 *   1. We don't need password or enabled/locked flags — JWT handles that
 *   2. We want direct access to userId (UUID string) without casting
 */
@Getter
@AllArgsConstructor
public class AuthenticatedUser {

    private final String userId;
    private final String role;

    public boolean isAdmin() {
        return "ADMIN".equals(role);
    }

    public boolean isTeacher() {
        return "TEACHER".equals(role);
    }

    public boolean isStudent() {
        return "STUDENT".equals(role);
    }
}
