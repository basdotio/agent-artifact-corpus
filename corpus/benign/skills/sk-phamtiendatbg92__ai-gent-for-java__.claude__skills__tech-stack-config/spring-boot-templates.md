# Spring Boot Templates and Code Examples

This file provides complete, copy-paste-ready code examples for common Spring Boot patterns used in this project.

---

## Complete Service Implementation Example

### Service Interface

```java
package com.example.hellospringboot.service;

import com.example.hellospringboot.dto.CourseResponse;
import com.example.hellospringboot.dto.CreateCourseRequest;

import java.util.List;

/**
 * Service interface for course operations
 */
public interface CourseService {

    /**
     * Get all courses
     * @return List of all courses
     */
    List<CourseResponse> getAllCourses();

    /**
     * Get course by ID
     * @param id Course ID
     * @return Course details
     * @throws com.example.hellospringboot.exception.CourseNotFoundException if course not found
     */
    CourseResponse getCourseById(Long id);

    /**
     * Create a new course
     * @param request Course creation request
     * @return Created course details
     */
    CourseResponse createCourse(CreateCourseRequest request);

    /**
     * Update an existing course
     * @param id Course ID
     * @param request Course update request
     * @return Updated course details
     * @throws com.example.hellospringboot.exception.CourseNotFoundException if course not found
     */
    CourseResponse updateCourse(Long id, CreateCourseRequest request);

    /**
     * Delete a course
     * @param id Course ID
     * @throws com.example.hellospringboot.exception.CourseNotFoundException if course not found
     */
    void deleteCourse(Long id);
}
```

### Service Implementation

```java
package com.example.hellospringboot.service;

import com.example.hellospringboot.dto.CourseResponse;
import com.example.hellospringboot.dto.CreateCourseRequest;
import com.example.hellospringboot.entity.Course;
import com.example.hellospringboot.exception.CourseNotFoundException;
import com.example.hellospringboot.repository.CourseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Service implementation for course operations
 * Implements: Business logic, error handling, logging
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class CourseServiceImpl implements CourseService {

    private final CourseRepository courseRepository;

    @Override
    @Transactional(readOnly = true)
    public List<CourseResponse> getAllCourses() {
        log.info("Fetching all courses");

        long startTime = System.currentTimeMillis();
        List<Course> courses = courseRepository.findAll();
        long queryTime = System.currentTimeMillis() - startTime;

        log.debug("Database query executed in {}ms, found {} courses", queryTime, courses.size());

        return courses.stream()
            .map(this::mapToResponse)
            .collect(Collectors.toList());
    }

    @Override
    @Transactional(readOnly = true)
    public CourseResponse getCourseById(Long id) {
        log.info("Fetching course with id: {}", id);

        Course course = courseRepository.findById(id)
            .orElseThrow(() -> {
                log.warn("Course not found: {}", id);
                return new CourseNotFoundException("Course with ID " + id + " not found");
            });

        log.info("Course retrieved successfully: ID={}, name={}", id, course.getName());
        return mapToResponse(course);
    }

    @Override
    @Transactional
    public CourseResponse createCourse(CreateCourseRequest request) {
        log.info("Creating new course: {}", request.getName());

        // Map request to entity
        Course course = new Course();
        course.setName(request.getName());
        course.setDescription(request.getDescription());
        course.setCredits(request.getCredits());

        // Save to database
        Course saved = courseRepository.save(course);
        log.info("Course created successfully: ID={}", saved.getId());

        return mapToResponse(saved);
    }

    @Override
    @Transactional
    public CourseResponse updateCourse(Long id, CreateCourseRequest request) {
        log.info("Updating course: ID={}", id);

        Course course = courseRepository.findById(id)
            .orElseThrow(() -> {
                log.warn("Course not found for update: {}", id);
                return new CourseNotFoundException("Course with ID " + id + " not found");
            });

        // Update fields
        course.setName(request.getName());
        course.setDescription(request.getDescription());
        course.setCredits(request.getCredits());

        Course updated = courseRepository.save(course);
        log.info("Course updated successfully: ID={}", id);

        return mapToResponse(updated);
    }

    @Override
    @Transactional
    public void deleteCourse(Long id) {
        log.info("Deleting course: ID={}", id);

        if (!courseRepository.existsById(id)) {
            log.warn("Course not found for deletion: {}", id);
            throw new CourseNotFoundException("Course with ID " + id + " not found");
        }

        courseRepository.deleteById(id);
        log.info("Course deleted successfully: ID={}", id);
    }

    /**
     * Private helper method to map entity to DTO
     */
    private CourseResponse mapToResponse(Course course) {
        CourseResponse response = new CourseResponse();
        response.setId(course.getId());
        response.setName(course.getName());
        response.setDescription(course.getDescription());
        response.setCredits(course.getCredits());
        return response;
    }
}
```

---

## Complete Controller Implementation Example

```java
package com.example.hellospringboot.controller;

import com.example.hellospringboot.dto.CourseResponse;
import com.example.hellospringboot.dto.CreateCourseRequest;
import com.example.hellospringboot.service.CourseService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for course operations
 * Implements: API endpoints, request validation, response formatting
 */
@RestController
@RequestMapping("/api/courses")
@RequiredArgsConstructor
@Slf4j
public class CourseController {

    private final CourseService courseService;

    /**
     * Get all courses
     * GET /api/courses
     */
    @GetMapping
    public ResponseEntity<List<CourseResponse>> getAllCourses() {
        log.info("Received request to get all courses");
        List<CourseResponse> courses = courseService.getAllCourses();
        return ResponseEntity.ok(courses);
    }

    /**
     * Get course by ID
     * GET /api/courses/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<CourseResponse> getCourse(@PathVariable Long id) {
        log.info("Received request to get course: ID={}", id);
        CourseResponse course = courseService.getCourseById(id);
        return ResponseEntity.ok(course);
    }

    /**
     * Create a new course
     * POST /api/courses
     */
    @PostMapping
    public ResponseEntity<CourseResponse> createCourse(@Valid @RequestBody CreateCourseRequest request) {
        log.info("Received request to create course: {}", request.getName());
        CourseResponse course = courseService.createCourse(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(course);
    }

    /**
     * Update an existing course
     * PUT /api/courses/{id}
     */
    @PutMapping("/{id}")
    public ResponseEntity<CourseResponse> updateCourse(
            @PathVariable Long id,
            @Valid @RequestBody CreateCourseRequest request) {
        log.info("Received request to update course: ID={}", id);
        CourseResponse course = courseService.updateCourse(id, request);
        return ResponseEntity.ok(course);
    }

    /**
     * Delete a course
     * DELETE /api/courses/{id}
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteCourse(@PathVariable Long id) {
        log.info("Received request to delete course: ID={}", id);
        courseService.deleteCourse(id);
        return ResponseEntity.noContent().build();
    }
}
```

---

## Complete Entity Example

```java
package com.example.hellospringboot.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * JPA entity for course table
 */
@Entity
@Table(name = "course")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Course {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "name", nullable = false, length = 255)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "credits", nullable = false)
    private Integer credits;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
```

---

## Complete Repository Example

```java
package com.example.hellospringboot.repository;

import com.example.hellospringboot.entity.Course;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for Course entity
 */
@Repository
public interface CourseRepository extends JpaRepository<Course, Long> {

    // Method name query - Spring Data auto-implements
    Optional<Course> findByName(String name);

    // Method name query for multiple results
    List<Course> findByCreditsGreaterThanEqual(Integer credits);

    // Custom JPQL query
    @Query("SELECT c FROM Course c WHERE c.name LIKE %:keyword%")
    List<Course> searchByName(@Param("keyword") String keyword);

    // Check existence
    boolean existsByName(String name);

    // Count query
    long countByCredits(Integer credits);
}
```

---

## DTO Examples

### Response DTO

```java
package com.example.hellospringboot.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Response DTO for course details
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CourseResponse {
    private Long id;
    private String name;
    private String description;
    private Integer credits;

    /**
     * Factory method to create from entity
     */
    public static CourseResponse from(Long id, String name, String description, Integer credits) {
        return new CourseResponse(id, name, description, credits);
    }
}
```

### Request DTO with Validation

```java
package com.example.hellospringboot.dto;

import jakarta.validation.constraints.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for creating/updating a course
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateCourseRequest {

    @NotBlank(message = "Course name is required")
    @Size(min = 3, max = 255, message = "Course name must be between 3 and 255 characters")
    private String name;

    @Size(max = 1000, message = "Description cannot exceed 1000 characters")
    private String description;

    @NotNull(message = "Credits are required")
    @Min(value = 1, message = "Credits must be at least 1")
    @Max(value = 10, message = "Credits cannot exceed 10")
    private Integer credits;
}
```

### Error Response DTO

```java
package com.example.hellospringboot.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

/**
 * Standardized error response DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ErrorResponse {

    private String code;
    private String message;
    private String traceId;

    /**
     * Factory method with auto-generated trace ID
     */
    public static ErrorResponse of(String code, String message) {
        return new ErrorResponse(
            code,
            message,
            UUID.randomUUID().toString()
        );
    }
}
```

---

## Exception Handling Examples

### Custom Exception

```java
package com.example.hellospringboot.exception;

/**
 * Exception thrown when a course is not found
 */
public class CourseNotFoundException extends RuntimeException {

    public CourseNotFoundException(String message) {
        super(message);
    }

    public CourseNotFoundException(String message, Throwable cause) {
        super(message, cause);
    }
}
```

### Global Exception Handler

```java
package com.example.hellospringboot.exception;

import com.example.hellospringboot.dto.ErrorResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.stream.Collectors;

/**
 * Global exception handler for all API errors
 */
@ControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    /**
     * Handle resource not found exceptions (404)
     */
    @ExceptionHandler(CourseNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleCourseNotFound(CourseNotFoundException ex) {
        log.warn("Course not found: {}", ex.getMessage());

        ErrorResponse error = ErrorResponse.of(
            "COURSE_NOT_FOUND",
            ex.getMessage()
        );

        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
    }

    /**
     * Handle validation errors (400)
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationException(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult()
            .getFieldErrors()
            .stream()
            .map(FieldError::getDefaultMessage)
            .collect(Collectors.joining(", "));

        log.warn("Validation error: {}", message);

        ErrorResponse error = ErrorResponse.of(
            "VALIDATION_ERROR",
            message
        );

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    /**
     * Handle type mismatch errors (400)
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        log.warn("Invalid parameter format: {}", ex.getValue());

        String message = String.format(
            "Invalid parameter '%s': expected %s but got '%s'",
            ex.getName(),
            ex.getRequiredType().getSimpleName(),
            ex.getValue()
        );

        ErrorResponse error = ErrorResponse.of(
            "INVALID_PARAMETER",
            message
        );

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    /**
     * Handle database errors (500)
     */
    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<ErrorResponse> handleDatabaseError(DataAccessException ex) {
        log.error("Database error: {}", ex.getMessage(), ex);

        ErrorResponse error = ErrorResponse.of(
            "DATABASE_ERROR",
            "Unable to process request due to database error"
        );

        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }

    /**
     * Handle all other unexpected errors (500)
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericError(Exception ex) {
        log.error("Unexpected error: {}", ex.getMessage(), ex);

        ErrorResponse error = ErrorResponse.of(
            "INTERNAL_ERROR",
            "An unexpected error occurred"
        );

        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}
```

---

## Test Examples

### Unit Test for Service

```java
package com.example.hellospringboot.service;

import com.example.hellospringboot.dto.CourseResponse;
import com.example.hellospringboot.dto.CreateCourseRequest;
import com.example.hellospringboot.entity.Course;
import com.example.hellospringboot.exception.CourseNotFoundException;
import com.example.hellospringboot.repository.CourseRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CourseServiceImplTest {

    @Mock
    private CourseRepository courseRepository;

    @InjectMocks
    private CourseServiceImpl courseService;

    @Test
    void getCourseById_Success() {
        // Given
        Long courseId = 1L;
        Course course = new Course();
        course.setId(courseId);
        course.setName("Spring Boot Basics");
        course.setCredits(3);

        when(courseRepository.findById(courseId))
            .thenReturn(Optional.of(course));

        // When
        CourseResponse response = courseService.getCourseById(courseId);

        // Then
        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(courseId);
        assertThat(response.getName()).isEqualTo("Spring Boot Basics");
        assertThat(response.getCredits()).isEqualTo(3);

        verify(courseRepository, times(1)).findById(courseId);
    }

    @Test
    void getCourseById_NotFound() {
        // Given
        Long courseId = 999L;
        when(courseRepository.findById(courseId))
            .thenReturn(Optional.empty());

        // When & Then
        assertThatThrownBy(() -> courseService.getCourseById(courseId))
            .isInstanceOf(CourseNotFoundException.class)
            .hasMessageContaining("Course with ID 999 not found");

        verify(courseRepository, times(1)).findById(courseId);
    }

    @Test
    void createCourse_Success() {
        // Given
        CreateCourseRequest request = new CreateCourseRequest();
        request.setName("Advanced Java");
        request.setDescription("Deep dive into Java");
        request.setCredits(4);

        Course savedCourse = new Course();
        savedCourse.setId(1L);
        savedCourse.setName(request.getName());
        savedCourse.setCredits(request.getCredits());

        when(courseRepository.save(any(Course.class)))
            .thenReturn(savedCourse);

        // When
        CourseResponse response = courseService.createCourse(request);

        // Then
        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(1L);
        assertThat(response.getName()).isEqualTo("Advanced Java");

        verify(courseRepository, times(1)).save(any(Course.class));
    }
}
```

### Integration Test for Controller

```java
package com.example.hellospringboot.controller;

import com.example.hellospringboot.entity.Course;
import com.example.hellospringboot.repository.CourseRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class CourseControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CourseRepository courseRepository;

    @BeforeEach
    void setUp() {
        courseRepository.deleteAll();
    }

    @Test
    void getCourse_Success() throws Exception {
        // Given: Insert test data
        Course course = new Course();
        course.setName("Test Course");
        course.setDescription("Test Description");
        course.setCredits(3);
        Course saved = courseRepository.save(course);

        // When & Then
        mockMvc.perform(get("/api/courses/" + saved.getId()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(saved.getId()))
            .andExpect(jsonPath("$.name").value("Test Course"))
            .andExpect(jsonPath("$.credits").value(3));
    }

    @Test
    void getCourse_NotFound() throws Exception {
        // When & Then
        mockMvc.perform(get("/api/courses/999"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.code").value("COURSE_NOT_FOUND"))
            .andExpect(jsonPath("$.traceId").exists());
    }

    @Test
    void createCourse_Success() throws Exception {
        // Given
        String requestBody = """
            {
                "name": "New Course",
                "description": "New Description",
                "credits": 4
            }
            """;

        // When & Then
        mockMvc.perform(post("/api/courses")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("New Course"))
            .andExpect(jsonPath("$.credits").value(4));
    }

    @Test
    void createCourse_ValidationError() throws Exception {
        // Given: Invalid request (name too short)
        String requestBody = """
            {
                "name": "AB",
                "credits": 4
            }
            """;

        // When & Then
        mockMvc.perform(post("/api/courses")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
    }
}
```

---

## Flyway Migration Template

```sql
-- V2__Add_course_table.sql

-- Create course table
CREATE TABLE course (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credits INTEGER NOT NULL CHECK (credits > 0 AND credits <= 10),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on name for faster searches
CREATE INDEX idx_course_name ON course(name);

-- Add unique constraint if needed
ALTER TABLE course ADD CONSTRAINT uk_course_name UNIQUE (name);

-- Insert sample data (optional)
INSERT INTO course (name, description, credits) VALUES
('Introduction to Programming', 'Learn the basics of programming', 3),
('Data Structures', 'Advanced data structures and algorithms', 4),
('Web Development', 'Build modern web applications', 3);
```

---

## Summary

These templates provide complete, ready-to-use code examples that follow the project's established patterns:
- ✅ Lombok annotations for boilerplate reduction
- ✅ Constructor injection with `@RequiredArgsConstructor`
- ✅ Logging with `@Slf4j`
- ✅ Transaction management with `@Transactional`
- ✅ Proper HTTP status codes
- ✅ Global exception handling
- ✅ Request validation
- ✅ Comprehensive testing
- ✅ Flyway database migrations

Use these templates as a starting point when implementing new features!
