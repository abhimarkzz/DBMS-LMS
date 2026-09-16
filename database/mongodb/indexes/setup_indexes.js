// =============================================================================
// MongoDB Schema and Index Setup — Notification Service
// =============================================================================
// Run this script using: mongosh < setup_indexes.js
// Or from the notification service initialization code.
//
// MongoDB is used for:
//   1. notifications — Real-time and persistent user notifications
//   2. activity_events — Application event stream for the notification service
//
// Design rationale:
//   Notifications have variable metadata shapes (assignment_id, course_id,
//   quiz_id depending on type) — document model fits naturally.
//   The notification service reads MongoDB and fans events out via Socket.IO.
//   No JOINs are needed on notification data, so MongoDB's document model
//   is the right fit here.
// =============================================================================

// Connect to the LMS notifications database
const db = db.getSiblingDB(process.env.MONGODB_DB || 'lms_notifications');

// =============================================================================
// Collection: notifications
// =============================================================================
// Document shape:
// {
//   _id: ObjectId,
//   recipientId: "uuid-string",       // user_id from PostgreSQL
//   senderId: "uuid-string",          // who triggered the notification
//   type: "ASSIGNMENT_CREATED",       // notification category
//   title: "New Assignment: ER Diagram",
//   message: "A new assignment has been uploaded for CS501.",
//   metadata: {
//     courseId: "uuid",
//     courseName: "Database Management Systems",
//     assignmentId: "uuid",           // present for assignment notifications
//     quizId: "uuid",                 // present for quiz notifications
//     materialId: "uuid"              // present for material notifications
//   },
//   read: false,
//   readAt: null,
//   createdAt: ISODate("2024-...")
// }

db.createCollection('notifications', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['recipientId', 'type', 'title', 'message', 'read', 'createdAt'],
            properties: {
                recipientId: {
                    bsonType: 'string',
                    description: 'UUID of the user receiving the notification'
                },
                senderId: {
                    bsonType: ['string', 'null'],
                    description: 'UUID of the user/service that triggered this'
                },
                type: {
                    bsonType: 'string',
                    enum: [
                        'ASSIGNMENT_CREATED',
                        'ASSIGNMENT_GRADED',
                        'RESULT_PUBLISHED',
                        'QUIZ_PUBLISHED',
                        'MATERIAL_UPLOADED',
                        'ANNOUNCEMENT_POSTED',
                        'ENROLLMENT_CONFIRMED',
                        'SYSTEM_MESSAGE'
                    ]
                },
                title: { bsonType: 'string' },
                message: { bsonType: 'string' },
                metadata: { bsonType: 'object' },
                read: { bsonType: 'bool' },
                readAt: { bsonType: ['date', 'null'] },
                createdAt: { bsonType: 'date' }
            }
        }
    }
});

// Index 1: Find all notifications for a recipient, newest first
// This is the primary query: "show me my notifications"
db.notifications.createIndex(
    { recipientId: 1, createdAt: -1 },
    { name: 'idx_recipient_created' }
);

// Index 2: Find unread notifications for a recipient
// Used for notification badge count and filtering unread items
db.notifications.createIndex(
    { recipientId: 1, read: 1 },
    { name: 'idx_recipient_read' }
);

// Index 3: Find notifications by type (admin monitoring)
db.notifications.createIndex(
    { type: 1, createdAt: -1 },
    { name: 'idx_type_created' }
);

// TTL index: auto-delete notifications older than 90 days
// Prevents unbounded growth of the notifications collection
db.notifications.createIndex(
    { createdAt: 1 },
    { expireAfterSeconds: 7776000, name: 'idx_ttl_90days' }  // 90 * 24 * 60 * 60
);


// =============================================================================
// Collection: activity_events
// =============================================================================
// Used by the notification service to pick up events from application services
// and fan them out to affected users via Socket.IO.
//
// Document shape:
// {
//   _id: ObjectId,
//   actorId: "uuid-string",           // who performed the action
//   eventType: "ASSIGNMENT_GRADED",
//   entityType: "submissions",
//   entityId: "uuid-string",
//   targetUserIds: ["uuid1", "uuid2"], // who should be notified
//   metadata: {
//     courseId: "uuid",
//     assignmentId: "uuid",
//     marksObtained: 17.0
//   },
//   processed: false,                  // false until notification service handles it
//   processedAt: null,
//   createdAt: ISODate("2024-...")
// }

db.createCollection('activity_events', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['eventType', 'processed', 'createdAt'],
            properties: {
                actorId: { bsonType: ['string', 'null'] },
                eventType: { bsonType: 'string' },
                entityType: { bsonType: ['string', 'null'] },
                entityId: { bsonType: ['string', 'null'] },
                targetUserIds: {
                    bsonType: 'array',
                    items: { bsonType: 'string' }
                },
                metadata: { bsonType: 'object' },
                processed: { bsonType: 'bool' },
                processedAt: { bsonType: ['date', 'null'] },
                createdAt: { bsonType: 'date' }
            }
        }
    }
});

// Index 1: Find unprocessed events (notification service polling)
db.activity_events.createIndex(
    { processed: 1, createdAt: 1 },
    { name: 'idx_unprocessed_events' }
);

// Index 2: Find events by actor (admin audit trail)
db.activity_events.createIndex(
    { actorId: 1, createdAt: -1 },
    { name: 'idx_actor_created' }
);

// Index 3: Find events by type (monitoring dashboards)
db.activity_events.createIndex(
    { eventType: 1, createdAt: -1 },
    { name: 'idx_eventtype_created' }
);

// TTL index: delete processed events after 30 days
db.activity_events.createIndex(
    { createdAt: 1 },
    { expireAfterSeconds: 2592000, name: 'idx_ttl_30days' }   // 30 * 24 * 60 * 60
);

print('MongoDB collections and indexes created successfully.');
