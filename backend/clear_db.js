const mongoose = require('mongoose');
const dotenv = require('dotenv');
// Adjust path if necessary based on where we run this script
// Assumes running from d:\Inviligens\backend
const Alert = require('./models/Alert');

dotenv.config();

const connectDB = async () => {
    try {
        await mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/invigilens');
        console.log('MongoDB Connected');
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
};

const clearData = async () => {
    await connectDB();
    try {
        const result = await Alert.deleteMany({});
        console.log(`Success! Deleted ${result.deletedCount} alerts from the database.`);
        process.exit();
    } catch (error) {
        console.error(`Error deleting data: ${error.message}`);
        process.exit(1);
    }
};

clearData();
