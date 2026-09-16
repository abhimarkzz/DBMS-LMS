package com.lms.courseservice.dto.response;

import com.lms.courseservice.entity.Announcement;
import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@Builder
public class AnnouncementResponse {

    private UUID announcementId;
    private UUID courseId;
    private UUID postedBy;
    private String title;
    private String content;
    private Boolean isPinned;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public static AnnouncementResponse from(Announcement announcement) {
        return AnnouncementResponse.builder()
            .announcementId(announcement.getAnnouncementId())
            .courseId(announcement.getCourse().getCourseId())
            .postedBy(announcement.getPostedBy())
            .title(announcement.getTitle())
            .content(announcement.getContent())
            .isPinned(announcement.getIsPinned())
            .createdAt(announcement.getCreatedAt())
            .updatedAt(announcement.getUpdatedAt())
            .build();
    }
}
