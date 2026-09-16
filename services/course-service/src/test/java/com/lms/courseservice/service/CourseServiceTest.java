package com.lms.courseservice.service;

import com.lms.courseservice.dto.request.CreateCourseRequest;
import com.lms.courseservice.dto.response.CourseResponse;
import com.lms.courseservice.entity.Course;
import com.lms.courseservice.exception.AppException;
import com.lms.courseservice.repository.CourseRepository;
import com.lms.courseservice.repository.EnrollmentRepository;
import com.lms.courseservice.security.AuthenticatedUser;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for CourseService.
 *
 * Uses Mockito to isolate the service from the database.
 * No Spring context is loaded — tests run in milliseconds.
 */
@ExtendWith(MockitoExtension.class)
class CourseServiceTest {

    @Mock
    private CourseRepository courseRepository;

    @Mock
    private EnrollmentRepository enrollmentRepository;

    @InjectMocks
    private CourseService courseService;

    private AuthenticatedUser teacherUser;
    private AuthenticatedUser adminUser;
    private AuthenticatedUser anotherTeacher;
    private Course sampleCourse;

    @BeforeEach
    void setUp() {
        String teacherId = UUID.randomUUID().toString();
        String adminId = UUID.randomUUID().toString();
        String otherTeacherId = UUID.randomUUID().toString();

        teacherUser = new AuthenticatedUser(teacherId, "TEACHER");
        adminUser = new AuthenticatedUser(adminId, "ADMIN");
        anotherTeacher = new AuthenticatedUser(otherTeacherId, "TEACHER");

        sampleCourse = Course.builder()
            .courseId(UUID.randomUUID())
            .courseCode("CS501")
            .courseName("Data Structures and Algorithms")
            .credits((short) 4)
            .department("Computer Science and Engineering")
            .semester((short) 5)
            .teacherId(UUID.fromString(teacherId))
            .status(Course.CourseStatus.ACTIVE)
            .build();
    }

    // ---- Course Creation ----

    @Test
    @DisplayName("Creating a course with a unique code succeeds")
    void createCourse_uniqueCode_succeeds() {
        CreateCourseRequest request = buildCreateRequest("CS501");
        when(courseRepository.existsByCourseCode("CS501")).thenReturn(false);
        when(courseRepository.save(any(Course.class))).thenReturn(sampleCourse);
        when(enrollmentRepository.countActiveByCourseId(any())).thenReturn(0L);

        CourseResponse response = courseService.createCourse(request, teacherUser);

        assertThat(response.getCourseCode()).isEqualTo("CS501");
        assertThat(response.getTeacherId().toString()).isEqualTo(teacherUser.getUserId());
        verify(courseRepository).save(any(Course.class));
    }

    @Test
    @DisplayName("Creating a course with a duplicate code throws conflict error")
    void createCourse_duplicateCode_throwsConflict() {
        CreateCourseRequest request = buildCreateRequest("CS501");
        when(courseRepository.existsByCourseCode("CS501")).thenReturn(true);

        assertThatThrownBy(() -> courseService.createCourse(request, teacherUser))
            .isInstanceOf(AppException.class)
            .hasMessageContaining("CS501");

        verify(courseRepository, never()).save(any());
    }

    @Test
    @DisplayName("Teacher ID in response always comes from JWT, not request body")
    void createCourse_teacherIdFromJwt_notFromRequest() {
        CreateCourseRequest request = buildCreateRequest("CS601");
        when(courseRepository.existsByCourseCode("CS601")).thenReturn(false);
        when(courseRepository.save(any(Course.class))).thenAnswer(invocation -> {
            Course c = invocation.getArgument(0);
            // The teacherId in the saved entity should match teacherUser, not adminUser
            assertThat(c.getTeacherId().toString()).isEqualTo(teacherUser.getUserId());
            return c;
        });
        when(enrollmentRepository.countActiveByCourseId(any())).thenReturn(0L);

        courseService.createCourse(request, teacherUser);
    }

    // ---- Update ----

    @Test
    @DisplayName("Teacher can update their own course")
    void updateCourse_ownCourse_succeeds() {
        UUID courseId = sampleCourse.getCourseId();
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(sampleCourse));
        when(courseRepository.save(any())).thenReturn(sampleCourse);
        when(enrollmentRepository.countActiveByCourseId(courseId)).thenReturn(5L);

        var request = new com.lms.courseservice.dto.request.UpdateCourseRequest();
        request.setCourseName("Updated Name");

        CourseResponse response = courseService.updateCourse(courseId, request, teacherUser);

        verify(courseRepository).save(sampleCourse);
    }

    @Test
    @DisplayName("Teacher cannot update another teacher's course")
    void updateCourse_otherTeachersCourse_throwsForbidden() {
        UUID courseId = sampleCourse.getCourseId();
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(sampleCourse));

        var request = new com.lms.courseservice.dto.request.UpdateCourseRequest();
        request.setCourseName("Attempted Update");

        assertThatThrownBy(() -> courseService.updateCourse(courseId, request, anotherTeacher))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> {
                assertThat(((AppException) ex).getStatus().value()).isEqualTo(403);
            });

        verify(courseRepository, never()).save(any());
    }

    @Test
    @DisplayName("Admin can update any teacher's course")
    void updateCourse_adminCanUpdateAny_succeeds() {
        UUID courseId = sampleCourse.getCourseId();
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(sampleCourse));
        when(courseRepository.save(any())).thenReturn(sampleCourse);
        when(enrollmentRepository.countActiveByCourseId(courseId)).thenReturn(0L);

        var request = new com.lms.courseservice.dto.request.UpdateCourseRequest();
        request.setCourseName("Admin Updated Name");

        // Admin updating a course owned by teacherUser — should succeed
        assertThatNoException().isThrownBy(() ->
            courseService.updateCourse(courseId, request, adminUser)
        );
    }

    @Test
    @DisplayName("Updating a non-existent course throws NOT_FOUND")
    void updateCourse_nonExistent_throwsNotFound() {
        UUID fakeId = UUID.randomUUID();
        when(courseRepository.findById(fakeId)).thenReturn(Optional.empty());

        var request = new com.lms.courseservice.dto.request.UpdateCourseRequest();

        assertThatThrownBy(() -> courseService.updateCourse(fakeId, request, teacherUser))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> {
                assertThat(((AppException) ex).getStatus().value()).isEqualTo(404);
            });
    }

    @Test
    @DisplayName("Invalid status string throws BAD_REQUEST")
    void updateCourse_invalidStatus_throwsBadRequest() {
        UUID courseId = sampleCourse.getCourseId();
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(sampleCourse));

        var request = new com.lms.courseservice.dto.request.UpdateCourseRequest();
        request.setStatus("INVALID_STATUS");

        assertThatThrownBy(() -> courseService.updateCourse(courseId, request, adminUser))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> {
                assertThat(((AppException) ex).getStatus().value()).isEqualTo(400);
            });
    }

    // ---- Helper ----

    private CreateCourseRequest buildCreateRequest(String code) {
        CreateCourseRequest request = new CreateCourseRequest();
        request.setCourseCode(code);
        request.setCourseName("Test Course Name");
        request.setCredits((short) 4);
        request.setDepartment("Computer Science and Engineering");
        request.setSemester((short) 5);
        return request;
    }
}
