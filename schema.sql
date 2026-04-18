CREATE DATABASE IF NOT EXISTS sfras_db;
USE sfras_db;

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(50) UNIQUE NOT NULL,
    course VARCHAR(100),
    role VARCHAR(20) DEFAULT 'Student',
    email VARCHAR(120),
    password VARCHAR(255),
    face_encoding BLOB, -- To store the 128-D facial encoding as binary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    status VARCHAR(20) DEFAULT 'Present',
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
