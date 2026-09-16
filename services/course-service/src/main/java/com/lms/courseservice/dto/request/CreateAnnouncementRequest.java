package com.lms.courseservice.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Request payload for creating a new course announcement.
 */
@Data
public class CreateAnnouncementRequest {

    @NotBlank(message = "Title is required")
    @Size(min = 3, max = 300, message = "Title must be 3-300 characters")
    private String title;

    @NotBlank(message = "Content is required")
    @Size(min = 10, max = 10000, message = "Content must be 10-10000 characters")
    private String content;

    private boolean isPinned = false;
}
