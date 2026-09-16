package com.lms.courseservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

/**
 * Course Service — Spring Boot Entry Point
 *
 * Manages:
 *   - Course CRUD (teacher creates, admin manages)
 *   - Student enrollment and unenrollment
 *   - Course announcements
 *   - Course material metadata (actual upload handled by AI Search Service)
 *
 * Auth: Stateless JWT validation — no session state stored.
 *       The shared JWT secret from User Service is used to verify tokens locally.
 *       No network call to User Service on every request.
 *
 * Cache: Redis caches course details (10 min TTL) and enrollment lists (5 min TTL).
 *        Cache is invalidated on write operations.
 */
@SpringBootApplication
@EnableCaching
public class CourseServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(CourseServiceApplication.class, args);
    }
}
