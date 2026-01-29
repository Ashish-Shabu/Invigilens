const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const Student = require('../models/Student');

// --- Multer Storage Config ---
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        // Save to d:\Inviligens\data\students
        // We use path.resolve to go up from backend/routes to root/data/students
        const uploadPath = path.resolve(__dirname, '../../data/students');
        if (!fs.existsSync(uploadPath)) {
            fs.mkdirSync(uploadPath, { recursive: true });
        }
        cb(null, uploadPath);
    },
    filename: function (req, file, cb) {
        // Rename file to [RollNo].jpg
        // Note: req.body is populated AFTER multer, so we might need a workaround or just trust 'rollNo' is sent
        // Actually, multer processes file first. 
        // Strategy: Save as temp name, then rename after validation, or just use timestamp-rollno
        // For simplicity: Use timestamp + original extension, we store the path in DB.
        // User asked to rename to RollNo. Let's try to get rollNo from body.
        // Warning: req.body might be empty here in some configs. 
        // Safer: unique suffix.
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({ storage: storage });

// @desc    Add a new student (Photo + Details)
// @route   POST /api/students
router.post('/', upload.single('photo'), async (req, res) => {
    try {
        const { name, rollNo, className } = req.body;

        if (!req.file) {
            return res.status(400).json({ message: 'Please upload a photo' });
        }

        // Check if student exists
        const existingStudent = await Student.findOne({ rollNo });
        if (existingStudent) {
            // Optional: Update existing? For now, return error
            return res.status(400).json({ message: 'Student with this Roll No already exists' });
        }

        // Rename logic (User requested rename to RollNo)
        // We do this after validation to avoid overwriting existing files or invalid inputs
        const oldPath = req.file.path;
        const extension = path.extname(req.file.originalname);
        const newFilename = `${rollNo}${extension}`;
        const newPath = path.join(path.dirname(oldPath), newFilename);

        // Check if a file with this rollNo already exists, overwrite if so?
        // Since we checked DB, we assume it's safeish, but physical file might remain.
        if (fs.existsSync(newPath)) {
            fs.unlinkSync(newPath); // Delete old physical file if exists
        }

        fs.renameSync(oldPath, newPath);

        const student = await Student.create({
            name,
            rollNo,
            className,
            photoPath: newFilename // Store just the filename
        });

        res.status(201).json(student);

    } catch (error) {
        console.error(error);
        res.status(500).json({ message: error.message });
    }
});

// @desc    Get all unique classes (and count)
// @route   GET /api/students/classes
router.get('/classes', async (req, res) => {
    try {
        // Aggregate to find unique classNames and count students
        const classes = await Student.aggregate([
            {
                $group: {
                    _id: "$className",
                    studentCount: { $sum: 1 } // Count how many in this class
                }
            },
            { $sort: { _id: 1 } } // Sort alphabetically
        ]);

        // Format: [{ name: "10A", count: 5 }, ...]
        const formatted = classes.map(c => ({
            name: c._id,
            count: c.studentCount
        }));

        res.json(formatted);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// @desc    Get students by class
// @route   GET /api/students?class=10A
router.get('/', async (req, res) => {
    try {
        const { class: className } = req.query;
        let query = {};
        if (className) {
            query.className = className;
        }

        const students = await Student.find(query).sort({ rollNo: 1 });
        res.json(students);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
