-- Reference schema. In practice, `flask init-db` creates these tables for you
-- via SQLAlchemy — this file is here if you'd rather set up MySQL manually.

CREATE DATABASE IF NOT EXISTS calendar_app CHARACTER SET utf8mb4;
USE calendar_app;

CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    submitter_name VARCHAR(120) NOT NULL,
    submitter_email VARCHAR(120) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME,
    location VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_by INT,
    reviewed_at DATETIME,
    FOREIGN KEY (reviewed_by) REFERENCES admins(id)
);
