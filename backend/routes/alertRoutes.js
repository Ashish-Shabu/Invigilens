const express = require('express');
const router = express.Router();
const Alert = require('../models/Alert');
const fs = require('fs');
const path = require('path');


// @desc    Create a new alert
// @route   POST /api/alerts
// @access  Public (Internal Python Script)
router.post('/', async (req, res) => {
    try {
        const { studentId, violationType, confidence, evidencePath } = req.body;

        const alert = await Alert.create({
            studentId,
            violationType,
            confidence,
            evidencePath
        });

        res.status(201).json(alert);

    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// @desc    Get all alerts (supports ?status=pending filter)
// @route   GET /api/alerts
// @access  Public (Dashboard)
router.get('/', async (req, res) => {
    try {
        const { status } = req.query;
        let query = {};
        if (status) query.status = status;

        const alerts = await Alert.find(query).sort({ timestamp: -1 });
        res.json(alerts);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// @desc    Update alert status (Verify/Reject)
// @route   PUT /api/alerts/:id
// @access  Public (Dashboard)
router.put('/:id', async (req, res) => {
    try {
        const { status } = req.body;
        const alert = await Alert.findById(req.params.id);

        if (alert) {
            alert.status = status || alert.status;
            const updatedAlert = await alert.save();
            res.json(updatedAlert);
        } else {
            res.status(404).json({ message: 'Alert not found' });
        }
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// @desc    Delete ALL alerts (Clear History)
// @route   DELETE /api/alerts
router.delete('/', async (req, res) => {
    try {
        await Alert.deleteMany({});
        // Optional: Delete files from disk too? For now just DB to keep it safe.
        res.json({ message: 'All alerts cleared' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;

