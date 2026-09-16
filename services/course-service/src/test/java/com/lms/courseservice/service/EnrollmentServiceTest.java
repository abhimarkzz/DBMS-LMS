package com.lms.courseservice.service;

import com.lms.courseservice.entity.Course;
import com.lms.courseservice.entity.Enrollment;
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

import java.math.BigDecimal;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class EnrollmentServiceTest {

    @Mock private CourseRepository courseRepository;
    @Mock private EnrollmentRepository enrollmentRepository;
    @InjectMocks private EnrollmentService enrollmentService;

    private UUID studentId;
    private UUID courseId;
    private Course activeCourse;
    private Course inactiveCourse;
    private Enrollment existingEnrollment;

    @BeforeEach
    void setUp() {
        studentId = UUID.randomUUID();
        courseId = UUID.randomUUID();

        activeCourse = Course.builder()
            .courseId(courseId)
            .courseCode("CS501")
            .courseName("DSA")
            .status(Course.CourseStatus.ACTIVE)
            .build();

        inactiveCourse = Course.builder()
            .courseId(UUID.randomUUID())
            .courseCode("CS999")
            .status(Course.CourseStatus.INACTIVE)
            .build();

        existingEnrollment = Enrollment.builder()
            .enrollmentId(UUID.randomUUID())
            .studentId(studentId)
            .course(activeCourse)
            .status(Enrollment.EnrollmentStatus.ENROLLED)
            .completionPercentage(BigDecimal.ZERO)
            .build();
    }

    @Test
    @DisplayName("Student can enroll in an active course")
    void enroll_activeCourse_succeeds() {
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(activeCourse));
        when(enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId))
            .thenReturn(Optional.empty());
        when(enrollmentRepository.save(any(Enrollment.class))).thenReturn(existingEnrollment);

        var response = enrollmentService.enroll(courseId, studentId);

        assertThat(response.getStudentId()).isEqualTo(studentId);
        assertThat(response.getCourseCode()).isEqualTo("CS501");
        verify(enrollmentRepository).save(any(Enrollment.class));
    }

    @Test
    @DisplayName("Enrolling in an inactive course throws BAD_REQUEST")
    void enroll_inactiveCourse_throwsBadRequest() {
        UUID inactiveCourseId = inactiveCourse.getCourseId();
        when(courseRepository.findById(inactiveCourseId)).thenReturn(Optional.of(inactiveCourse));

        assertThatThrownBy(() -> enrollmentService.enroll(inactiveCourseId, studentId))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> assertThat(((AppException) ex).getStatus().value()).isEqualTo(400));

        verify(enrollmentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Enrolling twice in the same course throws CONFLICT")
    void enroll_alreadyEnrolled_throwsConflict() {
        when(courseRepository.findById(courseId)).thenReturn(Optional.of(activeCourse));
        when(enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId))
            .thenReturn(Optional.of(existingEnrollment));

        assertThatThrownBy(() -> enrollmentService.enroll(courseId, studentId))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> {
                AppException appEx = (AppException) ex;
                assertThat(appEx.getStatus().value()).isEqualTo(409);
                assertThat(appEx.getCode()).isEqualTo("ALREADY_ENROLLED");
            });
    }

    @Test
    @DisplayName("Course not found returns NOT_FOUND on enroll")
    void enroll_courseNotFound_throwsNotFound() {
        when(courseRepository.findById(courseId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> enrollmentService.enroll(courseId, studentId))
            .isInstanceOf(AppException.class)
            .satisfies(ex -> assertThat(((AppException) ex).getStatus().value()).isEqualTo(404));
    }

    @Test
    @DisplayName("Student can drop their own enrollment")
    void dropEnrollment_selfDrop_succeeds() {
        when(enrollmentRepository.dropEnrollment(studentId, courseId)).thenReturn(1);
        when(enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId))
            .thenReturn(Optional.of(existingEnrollment));

        var response = enrollmentService.dropEnrollment(courseId, studentId, studentId, false);

        assertThat(response).isNotNull();
        verify(enrollmentRepository).dropEnrollment(studentId, courseId);
    }

    @Test
    @DisplayName("Student cannot drop another student's enrollment")
    void dropEnrollment_otherStudent_throwsForbidden() {
        UUID otherStudentId = UUID.randomUUID();

        assertThatThrownBy(() ->
            enrollmentService.dropEnrollment(courseId, otherStudentId, studentId, false)
        )
            .isInstanceOf(AppException.class)
            .satisfies(ex -> assertThat(((AppException) ex).getStatus().value()).isEqualTo(403));
    }

    @Test
    @DisplayName("Admin can drop any student's enrollment")
    void dropEnrollment_adminCanDropAny_succeeds() {
        UUID adminId = UUID.randomUUID();
        when(enrollmentRepository.dropEnrollment(studentId, courseId)).thenReturn(1);
        when(enrollmentRepository.findByStudentIdAndCourse_CourseId(studentId, courseId))
            .thenReturn(Optional.of(existingEnrollment));

        assertThatNoException().isThrownBy(() ->
            enrollmentService.dropEnrollment(courseId, studentId, adminId, true)
        );
    }

    @Test
    @DisplayName("isStudentEnrolled returns correct boolean from repository")
    void isStudentEnrolled_delegatesToRepository() {
        when(enrollmentRepository.existsByStudentIdAndCourse_CourseIdAndStatus(
            studentId, courseId, Enrollment.EnrollmentStatus.ENROLLED
        )).thenReturn(true);

        assertThat(enrollmentService.isStudentEnrolled(studentId, courseId)).isTrue();
    }
}
