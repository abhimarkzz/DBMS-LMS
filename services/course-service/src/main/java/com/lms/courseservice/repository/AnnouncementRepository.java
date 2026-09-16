package com.lms.courseservice.repository;

import com.lms.courseservice.entity.Announcement;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AnnouncementRepository extends JpaRepository<Announcement, UUID> {

    /**
     * Get all announcements for a course, pinned ones first, then newest first.
     * This is the primary query for the announcements list.
     */
    List<Announcement> findByCourse_CourseIdOrderByIsPinnedDescCreatedAtDesc(UUID courseId);

    /**
     * Count announcements in a course. Used for course overview stats.
     */
    long countByCourse_CourseId(UUID courseId);
}
