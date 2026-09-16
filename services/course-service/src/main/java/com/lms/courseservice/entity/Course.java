package com.lms.courseservice.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * JPA Entity — courses table
 *
 * Maps to the courses table created in migration 004.
 * Column names match exactly so Hibernate's validate mode does not fail.
 *
 * Relationship loading strategy:
 *   - enrollments: LAZY — we don't need the student list every time we load a course
 *   - announcements: LAZY — loaded only when explicitly queried
 */
@Entity
@Table(name = "courses")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Course {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "course_id", updatable = false, nullable = false)
    private UUID courseId;

    @Column(name = "course_code", nullable = false, unique = true, length = 20)
    private String courseCode;

    @Column(name = "course_name", nullable = false, length = 200)
    private String courseName;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "credits", nullable = false)
    private Short credits;

    @Column(name = "department", nullable = false, length = 100)
    private String department;

    @Column(name = "semester", nullable = false)
    private Short semester;

    // teacher_id refers to the teachers.teacher_id UUID.
    // We store the UUID directly — we don't JOIN to teachers from this service.
    // Teacher info is fetched from User Service when needed for display.
    @Column(name = "teacher_id", nullable = false)
    private UUID teacherId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private CourseStatus status;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    // Relationships — LAZY loaded, never fetched unless explicitly requested
    @OneToMany(mappedBy = "course", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    @Builder.Default
    private List<Enrollment> enrollments = new ArrayList<>();

    @OneToMany(mappedBy = "course", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    @Builder.Default
    private List<Announcement> announcements = new ArrayList<>();

    public enum CourseStatus {
        ACTIVE, INACTIVE, ARCHIVED
    }
}
