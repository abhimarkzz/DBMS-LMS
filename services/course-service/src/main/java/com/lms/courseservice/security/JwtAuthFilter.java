package com.lms.courseservice.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * JWT Authentication Filter
 *
 * Runs once per request. Validates the JWT from the Authorization header
 * and sets the authentication context if the token is valid.
 *
 * This filter does NOT call the User Service — it verifies the JWT signature
 * using the shared secret. This keeps authentication stateless and fast.
 *
 * The user_id and role extracted from the JWT are placed in the security context
 * so controllers and services can access them via @AuthenticationPrincipal or
 * SecurityContextHolder.
 */
@Component
@Slf4j
public class JwtAuthFilter extends OncePerRequestFilter {

    private final byte[] jwtSecretBytes;

    public JwtAuthFilter(@Value("${jwt.secret}") String jwtSecret) {
        this.jwtSecretBytes = jwtSecret.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        String authHeader = request.getHeader("Authorization");

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            // No token — continue without setting authentication
            // Spring Security will reject the request if the endpoint requires auth
            filterChain.doFilter(request, response);
            return;
        }

        String token = authHeader.substring(7);

        try {
            Claims claims = Jwts.parser()
                .verifyWith(Keys.hmacShaKeyFor(jwtSecretBytes))
                .build()
                .parseSignedClaims(token)
                .getPayload();

            String userId = claims.getSubject();
            String role = claims.get("role", String.class);
            String tokenType = claims.get("type", String.class);

            // Reject non-access tokens (e.g., if someone sends a refresh token)
            if (!"access".equals(tokenType)) {
                sendUnauthorized(response, "Invalid token type");
                return;
            }

            if (userId == null || role == null) {
                sendUnauthorized(response, "Token missing required claims");
                return;
            }

            // Build Spring Security authentication — role becomes a granted authority
            // Spring Security expects roles prefixed with "ROLE_" for hasRole() checks
            var authorities = List.of(new SimpleGrantedAuthority("ROLE_" + role));

            // AuthenticatedUser carries the user_id and role for downstream use
            AuthenticatedUser principal = new AuthenticatedUser(userId, role);

            var authentication = new UsernamePasswordAuthenticationToken(
                principal,
                null,          // credentials (null for JWT — we don't need the raw token downstream)
                authorities
            );

            SecurityContextHolder.getContext().setAuthentication(authentication);

        } catch (JwtException ex) {
            log.debug("JWT validation failed: {}", ex.getMessage());
            sendUnauthorized(response, "Invalid or expired token");
            return;
        }

        filterChain.doFilter(request, response);
    }

    private void sendUnauthorized(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType("application/json");
        response.getWriter().write(
            String.format(
                "{\"success\":false,\"error\":{\"code\":\"UNAUTHORIZED\",\"message\":\"%s\"}}",
                message
            )
        );
    }
}
