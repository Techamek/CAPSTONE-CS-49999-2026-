-- Reference schema. `flask init-db` creates these tables for you via SQLAlchemy
-- (and seeds default weekly hours) -- this file is here for manual setup.

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

    event_type VARCHAR(50),
    guest_count INT,
    duration_hours FLOAT,
    layout_choice VARCHAR(10),          -- '35-A'..'35-D' or '50-A'..'50-B'

    -- admin-only base-package estimate
    space_rental_total DECIMAL(10,2),
    menu_total DECIMAL(10,2),
    subtotal DECIMAL(10,2),
    tax_total DECIMAL(10,2),
    gratuity_total DECIMAL(10,2),
    grand_total DECIMAL(10,2),
    deposit_amount DECIMAL(10,2),

    FOREIGN KEY (reviewed_by) REFERENCES admins(id)
);

-- One row per weekday (0 = Monday ... 6 = Sunday)
CREATE TABLE IF NOT EXISTS weekly_hours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    weekday INT NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT 0,
    open_time TIME,
    close_time TIME
);

-- One-off closures or custom hours for a specific date
CREATE TABLE IF NOT EXISTS date_overrides (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    is_closed BOOLEAN NOT NULL DEFAULT 1,
    open_time TIME,
    close_time TIME,
    note VARCHAR(200)
);

-- Upgrading an existing database? Run this, then `flask init-db` (creates the two new tables):
--   ALTER TABLE events ADD COLUMN layout_choice VARCHAR(10);
-- Old columns (savory_selections, sweet_selections, enhancements, table_layout, enhancements_total)
-- are no longer used; they can stay or be dropped.
