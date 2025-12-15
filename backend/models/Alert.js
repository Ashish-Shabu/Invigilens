const mongoose = require('mongoose');

const alertSchema = mongoose.Schema({
    studentId: {
        type: String,
        required: true,
        default: 'Unknown'
    },
    violationType: {
        type: String,
        required: true,
        enum: ['Giving object', 'Giving signal', 'Looking Friend', 'Moving', 'Normal', 'Using Phone']
    },
    confidence: {
        type: Number,
        required: true
    },
    timestamp: {
        type: Date,
        default: Date.now
    },
    evidencePath: {
        type: String,
        required: false
    },
    status: {
        type: String,
        enum: ['pending', 'verified', 'rejected'],
        default: 'pending'
    }
});


module.exports = mongoose.model('Alert', alertSchema);
