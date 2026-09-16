package com.lms.courseservice;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

/**
 * Smoke test — verifies the Spring application context loads without errors.
 * Uses the "test" profile which connects to H2 instead of PostgreSQL.
 */
@SpringBootTest
@ActiveProfiles("test")
class CourseServiceApplicationTests {

    @Test
    void contextLoads() {
        // If the context fails to start (missing beans, config errors, etc.),
        // this test fails immediately — catches wiring issues early
    }
}
