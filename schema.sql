-- ============================================================
-- Lost and Found Management System - Database Schema
-- College Mini Project
-- ============================================================

CREATE DATABASE IF NOT EXISTS lost_found_db;
USE lost_found_db;

-- Admin login table
CREATE TABLE IF NOT EXISTS admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(50) NOT NULL
);

-- Table to store reported LOST items
CREATE TABLE IF NOT EXISTS lost_items (
    lost_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    location_lost VARCHAR(100),
    date_lost DATE,
    reporter_name VARCHAR(100) NOT NULL,
    reporter_contact VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Pending',       -- Pending / Claimed
    date_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store reported FOUND items
CREATE TABLE IF NOT EXISTS found_items (
    found_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    location_found VARCHAR(100),
    date_found DATE,
    founder_name VARCHAR(100) NOT NULL,
    founder_contact VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Pending',       -- Pending / Claimed
    date_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to record when a lost item is matched/claimed against a found item
CREATE TABLE IF NOT EXISTS claims (
    claim_id INT AUTO_INCREMENT PRIMARY KEY,
    lost_id INT,
    found_id INT,
    claim_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lost_id) REFERENCES lost_items(lost_id) ON DELETE CASCADE,
    FOREIGN KEY (found_id) REFERENCES found_items(found_id) ON DELETE CASCADE
);

-- Default admin login (username: admin , password: admin123)
INSERT INTO admin (username, password)
SELECT 'admin', 'admin123'
WHERE NOT EXISTS (SELECT 1 FROM admin WHERE username = 'admin');

-- A few sample rows so the app has data to show immediately (optional)
INSERT INTO lost_items (item_name, category, description, location_lost, date_lost, reporter_name, reporter_contact)
VALUES ('Blue Water Bottle', 'Accessories', 'Steel bottle with a college sticker on it', 'Library', CURDATE(), 'Rahul Sharma', '9876543210');

INSERT INTO found_items (item_name, category, description, location_found, date_found, founder_name, founder_contact)
VALUES ('Water Bottle', 'Accessories', 'Blue steel bottle found near reading hall', 'Library', CURDATE(), 'Security Desk', '9123456780');
