package com.lms.result.config;

import com.lms.result.security.JwtAuthFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security Configuration
 *
 * Strategy: Stateless JWT authentication.
 *   - No sessions (STATELESS policy)
 *   - No CSRF protection needed (CSRF is a session-based attack; JWTs are immune)
 *   - CORS handled by the API Gateway — not configured here
 *
 * Access rules:
 *   - GET /actuator/** — open for monitoring (Prometheus scraping)
 *   - GET /api-docs, /swagger-ui/** — open for documentation
 *   - GET /api/v1/courses — public catalog browsing
 *   - All other endpoints — require valid JWT
 *   - Role-specific rules enforced via @PreAuthorize in service/controller layer
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            .authorizeHttpRequests(auth -> auth
                // Monitoring endpoints — open for Prometheus
                .requestMatchers("/actuator/**").permitAll()
                // API documentation
                .requestMatchers("/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                // Public course catalog
                .requestMatchers(HttpMethod.GET, "/api/v1/courses").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/courses/{courseId}").permitAll()
                // Everything else requires authentication
                .anyRequest().authenticated()
            )
            // Our JWT filter runs before Spring's username/password filter
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
