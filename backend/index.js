const express = require('express');
const path = require('path');
const dotenv = require('dotenv');

const cors = require('cors');
const connectDB = require('./config/db');
const alertRoutes = require('./routes/alertRoutes');

// Load env vars
dotenv.config();

// Connect to Database
connectDB();

const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http, {
    cors: {
        origin: "*", // Allow all origins for dev
        methods: ["GET", "POST"]
    },
    maxHttpBufferSize: 1e8 // Allow large messages (video frames)
});

// Middleware

app.use(cors());
app.use(express.json());

// Serve Frontend
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve Static Files (Evidence Images)
app.use('/evidence', express.static('../data/processed'));
// Maps http://localhost:5000/evidence/filename.jpg -> d:\Inviligens\data\processed\filename.jpg

// Routes
app.use('/api/alerts', alertRoutes);


// Socket.io Connection
io.on('connection', (socket) => {
    console.log('User connected to socket');

    // Relay video frame from Python to Frontend
    socket.on('video_frame', (data) => {
        // Broadcast to all clients (except sender)
        socket.broadcast.emit('live_stream', data);
    });

    // Relay Monitoring Status (Frontend -> Python)
    socket.on('set_monitoring', (data) => {
        // Broadcast to all, including Python
        io.emit('set_monitoring', data);
    });

    // Relay Camera Start/Stop (Frontend -> Python)
    socket.on('camera_control', (data) => {
        io.emit('camera_control', data);
    });

    socket.on('disconnect', () => {


        console.log('User disconnected');
    });
});

const PORT = process.env.PORT || 5000;

http.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

