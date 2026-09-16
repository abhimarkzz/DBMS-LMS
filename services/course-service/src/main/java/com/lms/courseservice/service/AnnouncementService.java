package com.lms.courseservice.service;

import com.lms.courseservice.dto.request.CreateAnnouncementRequest;
import com.lms.courseservice.dto.response.AnnouncementResponse;
import com.lms.courseservice.entity.Announcement;
import com.lms.courseservice.entity.Course;
import com.lms.courseservice.exception.AppException;
import com.lms.courseservice.repository.AnnouncementRepository;
import com.lms.courseservice.repository.CourseRepository;
import com.lms.courseservice.security.AuthenticatedUser;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class AnnouncementService {

    private final CourseRepository courseRepository;
    private final AnnouncementRepository announcementRepository;

    /**
     * Post an announcement in a course.
     * Only the course teacher or an admin can post.
     */
    @Transactional
    public AnnouncementResponse createAnnouncement(
        UUID courseId,
        CreateAnnouncementRequest request,
        AuthenticatedUser author
    ) {
        Course course = courseRepository.findById(courseId)
            .orElseThrow(() -> AppException.notFound("Course not found: " + courseId));

        // Teachers can only post in their own course
        if (author.isTeacher()
                && !course.getTeacherId().toString().equals(author.getUserId())) {
            throw AppException.forbidden("You can only post announcements in your own courses");
        }

        Announcement announcement = Announcement.builder()
            .course(course)
            .postedBy(UUID.fromString(author.getUserId()))
            .title(request.getTitle())
            .content(request.getContent())
            .isPinned(request.isPinned())
            .build();

        announcement = announcementRepository.save(announcement);
        log.info("Announcement posted in course {} by {}", courseId, author.getUserId());

        return AnnouncementResponse.from(announcement);
    }

    /**
     * Get all announcements for a course (pinned first, then newest).
     * Accessible to any enrolled student, the teacher, or admin.
     */
    @Transactional(readOnly = true)
    public List<AnnouncementResponse> getCourseAnnouncements(UUID courseId) {
        if (!courseRepository.existsById(courseId)) {
            throw AppException.notFound("Course not found: " + courseId);
        }

        return announcementRepository
            .findByCourse_CourseIdOrderByIsPinnedDescCreatedAtDesc(courseId)
            .stream()
            .map(AnnouncementResponse::from)
            .collect(Collectors.toList());
    }

    /**
     * Delete an announcement.
     * Only the original poster or an admin can delete.
     */
    @Transactional
    public void deleteAnnouncement(UUID announcementId, AuthenticatedUser requestor) {
        Announcement announcement = announcementRepository.findById(announcementId)
            .orElseThrow(() -> AppException.notFound("Announcement not found: " + announcementId));

        boolean isOwner = announcement.getPostedBy().toString().equals(requestor.getUserId());

        if (!isOwner && !requestor.isAdmin()) {
            throw AppException.forbidden("You can only delete your own announcements");
        }

        announcementRepository.delete(announcement);
        log.info("Announcement {} deleted by {}", announcementId, requestor.getUserId());
    }
}
