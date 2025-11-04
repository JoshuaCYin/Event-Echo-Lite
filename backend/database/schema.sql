-- Deletes old tables to start fresh
DROP TABLE IF EXISTS rsvps, event_category_map, event_ratings, media_documents, saved_reports, audit_log, notifications, events, users, venues, event_categories CASCADE;

-- Stores user accounts
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'attendee',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- New profile fields
    major_department VARCHAR(100),
    phone_number VARCHAR(20),
    hobbies TEXT,
    bio TEXT,
    profile_picture TEXT
);

-- Stores physical locations (on-campus)
CREATE TABLE venues (
    venue_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    building VARCHAR(100),
    room_number VARCHAR(50),
    -- A link for Google Maps
    google_maps_link TEXT
);

-- Stores event types (e.g., "Workshop", "Social")
CREATE TABLE event_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Stores all event information
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    
    -- Hybrid location solution
    location_type VARCHAR(20) DEFAULT 'venue', -- 'venue' or 'custom'
    venue_id INT REFERENCES venues(venue_id) ON DELETE SET NULL, -- For on-campus
    custom_location_address TEXT, -- For off-campus
    google_maps_link TEXT, -- User-provided link
    
    -- Personal calendar solution
    visibility VARCHAR(20) DEFAULT 'public', -- 'public' or 'private'
    
    -- Links and status
    organizer_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'upcoming', -- e.g., upcoming, cancelled
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES users(user_id) ON DELETE SET NULL
);

-- Stores who is going to what event
CREATE TABLE rsvps (
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    event_id INT REFERENCES events(event_id) ON DELETE CASCADE,
    rsvp_status VARCHAR(50), -- 'going', 'maybe', 'canceled'
    PRIMARY KEY (user_id, event_id) -- Ensures one RSVP per user/event
);

-- Links events to one or more categories
CREATE TABLE event_category_map (
    event_id INT REFERENCES events(event_id) ON DELETE CASCADE,
    category_id INT REFERENCES event_categories(category_id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, category_id)
);

-- Basic audit logging
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL, -- e.g., 'user_login', 'event_create'
    target_type VARCHAR(50), -- e.g., 'event', 'user'
    target_id INT,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
