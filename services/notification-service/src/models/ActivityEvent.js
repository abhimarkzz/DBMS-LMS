const mongoose = require('mongoose');

const activityEventSchema = new mongoose.Schema({
    actorId: { type: String, default: null },
    eventType: { type: String, required: true },
    entityType: { type: String, default: null },
    entityId: { type: String, default: null },
    targetUserIds: { type: [String], default: [] },
    metadata: { type: mongoose.Schema.Types.Mixed, default: {} },
    processed: { type: Boolean, default: false },
    processedAt: { type: Date, default: null },
    createdAt: { type: Date, default: Date.now }
});

activityEventSchema.index({ processed: 1, createdAt: 1 });
activityEventSchema.index({ createdAt: 1 }, { expireAfterSeconds: 2592000 }); // 30 days

module.exports = mongoose.model('ActivityEvent', activityEventSchema);
