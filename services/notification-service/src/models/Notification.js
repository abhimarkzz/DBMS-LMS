const mongoose = require('mongoose');

const notificationSchema = new mongoose.Schema({
    recipientId: { type: String, required: true },
    senderId: { type: String, default: null },
    type: { 
        type: String, 
        required: true,
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
    title: { type: String, required: true },
    message: { type: String, required: true },
    metadata: { type: mongoose.Schema.Types.Mixed, default: {} },
    read: { type: Boolean, default: false },
    readAt: { type: Date, default: null },
    createdAt: { type: Date, default: Date.now }
});

notificationSchema.index({ recipientId: 1, createdAt: -1 });
notificationSchema.index({ recipientId: 1, read: 1 });
notificationSchema.index({ createdAt: 1 }, { expireAfterSeconds: 7776000 }); // 90 days

module.exports = mongoose.model('Notification', notificationSchema);
