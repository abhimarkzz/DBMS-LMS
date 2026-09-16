package com.lms.result.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "result_components")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ResultComponent {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "component_id", updatable = false, nullable = false)
    private UUID componentId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "result_id", nullable = false)
    private CourseResult courseResult;

    @Enumerated(EnumType.STRING)
    @Column(name = "component_type", nullable = false)
    private ResultComponentType componentType;

    @Column(name = "component_name", length = 100, nullable = false)
    private String componentName;

    @Column(name = "marks_obtained", precision = 6, scale = 2, nullable = false)
    private BigDecimal marksObtained;

    @Column(name = "max_marks", precision = 6, scale = 2, nullable = false)
    private BigDecimal maxMarks;

    @Column(name = "weight_percentage", precision = 5, scale = 2, nullable = false)
    private BigDecimal weightPercentage;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;
}
