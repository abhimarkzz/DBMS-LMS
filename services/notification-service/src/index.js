require('dotenv').config();
const express = require('express');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');

const connectDB = require('./config/db');
const notificationRoutes = require('./routes/notifications');
const EventPoller = require('./workers/eventPoller');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: '*', // For development
        methods: ['GET', 'POST']
    }
});

app.use(cors());
app.use(express.json());

// Connect DB
connectDB();

// API Routes
app.use('/api/v1/notifications', notificationRoutes);

// Health check
app.get('/health', (req, res) => res.status(200).json({ status: 'UP' }));

// Socket.io Auth Middleware
io.use((socket, next) => {
    const token = socket.handshake.auth.token;
    if (!token) {
        return next(new Error('Authentication error: No token provided'));
    }

    try {
        const secret = process.env.JWT_SECRET || 'super-secret-jwt-key-for-lms-development-environment';
        const decoded = jwt.verify(token, secret);
        socket.userId = decoded.sub;
        socket.role = decoded.role;
        next();
    } catch (err) {
        return next(new Error('Authentication error: Invalid token'));
    }
});

io.on('connection', (socket) => {
    console.log(`Socket connected: ${socket.id} for user ${socket.userId}`);
    
    // Join a specific room based on user ID for targeted notifications
    const userRoom = `user:${socket.userId}`;
    socket.join(userRoom);
    console.log(`Socket ${socket.id} joined room ${userRoom}`);

    socket.on('disconnect', () => {
        console.log(`Socket disconnected: ${socket.id}`);
    });
});

// Start the Event Poller
const poller = new EventPoller(io);
poller.start(process.env.POLL_INTERVAL_MS || 5000);

const PORT = process.env.PORT || 8004;

server.listen(PORT, () => {
    console.log(`Notification Service running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM signal received: closing HTTP server');
    poller.stop();
    server.close(() => {
        console.log('HTTP server closed');
        process.exit(0);
    });
});
