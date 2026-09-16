package com.lms.result.repository;

import com.lms.result.entity.CourseResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface CourseResultRepository extends JpaRepository<CourseResult, UUID> {
    Optional<CourseResult> findByStudentIdAndCourseId(UUID studentId, UUID courseId);
    List<CourseResult> findByCourseId(UUID courseId);
    List<CourseResult> findByStudentId(UUID studentId);
}
