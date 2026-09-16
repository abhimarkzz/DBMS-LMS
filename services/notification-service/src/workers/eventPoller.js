const ActivityEvent = require('../models/ActivityEvent');
const Notification = require('../models/Notification');

class EventPoller {
    constructor(io) {
        this.io = io;
        this.interval = null;
        this.isPolling = false;
    }

    start(pollIntervalMs = 5000) {
        console.log(`Starting event poller (interval: ${pollIntervalMs}ms)`);
        this.interval = setInterval(() => this.poll(), pollIntervalMs);
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            console.log('Event poller stopped');
        }
    }

    async poll() {
        if (this.isPolling) return;
        this.isPolling = true;

        try {
            const events = await ActivityEvent.find({ processed: false })
                .sort({ createdAt: 1 })
                .limit(50);

            if (events.length > 0) {
                console.log(`Found ${events.length} unprocessed activity events`);
                
                for (const event of events) {
                    await this.processEvent(event);
                }
            }
        } catch (error) {
            console.error('Error polling activity events:', error);
        } finally {
            this.isPolling = false;
        }
    }

    async processEvent(event) {
        try {
            const { title, message } = this.formatNotificationText(event);

            const notifications = event.targetUserIds.map(userId => ({
                recipientId: userId,
                senderId: event.actorId,
                type: event.eventType,
                title,
                message,
                metadata: event.metadata,
                read: false,
                createdAt: new Date()
            }));

            if (notifications.length > 0) {
                const inserted = await Notification.insertMany(notifications);
                
                inserted.forEach(notification => {
                    this.io.to(`user:${notification.recipientId}`).emit('notification', notification);
                });
            }

            event.processed = true;
            event.processedAt = new Date();
            await event.save();
        } catch (error) {
            console.error(`Failed to process event ${event._id}:`, error);
        }
    }

    formatNotificationText(event) {
        let title = 'System Notification';
        let message = 'You have a new notification.';

        switch(event.eventType) {
            case 'ASSIGNMENT_CREATED':
                title = 'New Assignment Available';
                message = event.metadata?.title ? `A new assignment "${event.metadata.title}" has been posted.` : 'A new assignment has been posted.';
                break;
            case 'ASSIGNMENT_GRADED':
                title = 'Assignment Graded';
                message = `Your assignment has been graded. Marks: ${event.metadata?.marksObtained || 'N/A'}`;
                break;
            case 'RESULT_PUBLISHED':
                title = 'Course Result Published';
                message = 'Your final result for the course has been published.';
                break;
            default:
                title = event.eventType.replace(/_/g, ' ');
                break;
        }

        return { title, message };
    }
}

module.exports = EventPoller;
