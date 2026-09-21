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

    -- event planning details
    event_type VARCHAR(50),
    guest_count INT,
    duration_hours FLOAT,
    savory_selections VARCHAR(400),
    sweet_selections VARCHAR(400),
    enhancements VARCHAR(400),
    table_layout TEXT,               -- JSON array of {id,type,label,seats,shape,x,y}

    -- price tracking
    space_rental_total DECIMAL(10,2),
    menu_total DECIMAL(10,2),
    enhancements_total DECIMAL(10,2),
    subtotal DECIMAL(10,2),
    tax_total DECIMAL(10,2),
    gratuity_total DECIMAL(10,2),
    grand_total DECIMAL(10,2),
    deposit_amount DECIMAL(10,2),

    FOREIGN KEY (reviewed_by) REFERENCES admins(id)
);
