// =============================================================================
// MongoDB Seed Data — Development Only
// =============================================================================
// Run: mongosh < seed_notifications.js
// =============================================================================

const db = db.getSiblingDB(process.env.MONGODB_DB || 'lms_notifications');

const now = new Date();

// =============================================================================
// Sample Notifications
// =============================================================================
db.notifications.insertMany([
    {
        recipientId: 'c0000000-0000-0000-0000-000000000001',   // student1
        senderId: 'b0000000-0000-0000-0000-000000000001',       // teacher1
        type: 'ASSIGNMENT_CREATED',
        title: 'New Assignment: ER Diagram Assignment',
        message: 'A new assignment "ER Diagram Assignment" has been posted in Database Management Systems. Due in 14 days.',
        metadata: {
            courseId: 'f0000000-0000-0000-0000-000000000001',
            courseName: 'Database Management Systems',
            courseCode: 'CS501',
            assignmentId: 'g0000000-0000-0000-0000-000000000001',
            assignmentTitle: 'ER Diagram Assignment',
            totalMarks: 20
        },
        read: false,
        readAt: null,
        createdAt: new Date(now - 2 * 24 * 60 * 60 * 1000)     // 2 days ago
    },
    {
        recipientId: 'c0000000-0000-0000-0000-000000000002',   // student2
        senderId: 'b0000000-0000-0000-0000-000000000001',
        type: 'ASSIGNMENT_CREATED',
        title: 'New Assignment: ER Diagram Assignment',
        message: 'A new assignment "ER Diagram Assignment" has been posted in Database Management Systems. Due in 14 days.',
        metadata: {
            courseId: 'f0000000-0000-0000-0000-000000000001',
            courseName: 'Database Management Systems',
            courseCode: 'CS501',
            assignmentId: 'g0000000-0000-0000-0000-000000000001',
            assignmentTitle: 'ER Diagram Assignment',
            totalMarks: 20
        },
        read: true,
        readAt: new Date(now - 1 * 24 * 60 * 60 * 1000),
        createdAt: new Date(now - 2 * 24 * 60 * 60 * 1000)
    },
    {
        recipientId: 'c0000000-0000-0000-0000-000000000001',   // student1
        senderId: 'b0000000-0000-0000-0000-000000000001',
        type: 'ASSIGNMENT_GRADED',
        title: 'Assignment Graded: ER Diagram Assignment',
        message: 'Your submission for "ER Diagram Assignment" has been graded. You scored 17/20.',
        metadata: {
            courseId: 'f0000000-0000-0000-0000-000000000001',
            courseName: 'Database Management Systems',
            courseCode: 'CS501',
            assignmentId: 'g0000000-0000-0000-0000-000000000001',
            submissionId: 'h0000000-0000-0000-0000-000000000001',
            marksObtained: 17,
            totalMarks: 20,
            feedback: 'Good work on identifying entities.'
        },
        read: false,
        readAt: null,
        createdAt: new Date(now - 1 * 24 * 60 * 60 * 1000)
    },
    {
        recipientId: 'c0000000-0000-0000-0000-000000000002',   // student2
        senderId: 'b0000000-0000-0000-0000-000000000001',
        type: 'ASSIGNMENT_GRADED',
        title: 'Assignment Graded: ER Diagram Assignment',
        message: 'Your submission for "ER Diagram Assignment" has been graded. You scored 19/20.',
        metadata: {
            courseId: 'f0000000-0000-0000-0000-000000000001',
            courseName: 'Database Management Systems',
            courseCode: 'CS501',
            assignmentId: 'g0000000-0000-0000-0000-000000000001',
            submissionId: 'h0000000-0000-0000-0000-000000000002',
            marksObtained: 19,
            totalMarks: 20,
            feedback: 'Excellent ER diagram.'
        },
        read: false,
        readAt: null,
        createdAt: new Date(now - 12 * 60 * 60 * 1000)         // 12 hours ago
    }
]);

// =============================================================================
// Sample Activity Events (unprocessed — notification service will handle these)
// =============================================================================
db.activity_events.insertMany([
    {
        actorId: 'b0000000-0000-0000-0000-000000000001',
        eventType: 'MATERIAL_UPLOADED',
        entityType: 'course_materials',
        entityId: 'k0000000-0000-0000-0000-000000000001',
        targetUserIds: [
            'c0000000-0000-0000-0000-000000000001',
            'c0000000-0000-0000-0000-000000000002',
            'c0000000-0000-0000-0000-000000000003'
        ],
        metadata: {
            courseId: 'f0000000-0000-0000-0000-000000000001',
            courseName: 'Database Management Systems',
            materialTitle: 'DBMS Chapter 1 - Introduction to Databases',
            materialType: 'PDF'
        },
        processed: true,
        processedAt: new Date(now - 3 * 24 * 60 * 60 * 1000),
        createdAt: new Date(now - 3 * 24 * 60 * 60 * 1000)
    }
]);

print('MongoDB seed data inserted successfully.');
