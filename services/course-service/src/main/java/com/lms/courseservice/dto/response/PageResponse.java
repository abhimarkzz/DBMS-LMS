package com.lms.courseservice.dto.response;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * Wrapper for paginated API responses.
 * Generic so it works for courses, students, announcements, etc.
 */
@Data
@Builder
public class PageResponse<T> {

    private List<T> content;
    private int page;
    private int pageSize;
    private long totalElements;
    private int totalPages;
    private boolean last;
}
