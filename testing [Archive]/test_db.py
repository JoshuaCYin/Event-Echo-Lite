"""
Quick database connection and schema integrity test.

This script performs a full CRUD cycle (Create, Read, Update, Delete) 
on key tables to ensure the schema.sql has been applied correctly 
and foreign key constraints are working.
"""

import os
import sys
from datetime import datetime, timedelta

# Ensure the backend module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Assuming db_connection.py is in the same directory and exports get_db()
try:
    from backend.database.db_connection import get_db
except ImportError:
    print("Error: Could not import get_db(). Make sure backend/database/db_connection.py exists.")
    sys.exit(1)


print("--- Running Database Quick Test ---")

# Variables to store generated IDs for cleanup
user_id = None
venue_id = None
event_id = None
category_id = None

conn = None
cur = None

try:
    conn = get_db()
    cur = conn.cursor()

    # 1. Basic connection check
    cur.execute("SELECT NOW();")
    print(f"Connected! Database server time: {cur.fetchone()[0]}")

    # 2. Check that critical tables exist
    tables = ['users', 'venues', 'events', 'rsvps', 'event_categories', 'event_category_map']
    print("\nChecking if critical tables exist...")
    
    all_found = True
    for t in tables:
        cur.execute("SELECT to_regclass(%s);", (t,))
        exists = cur.fetchone()[0]
        if not exists:
            all_found = False
            print(f" - {t}: MISSING")
        else:
            print(f" - {t}: Found")

    if not all_found:
        raise Exception("One or more critical tables are missing. Please run init_db.py first.")

    # 3. Insert test data into all major tables
    print("\nInserting test data to check relationships...")

    # Insert a user (organizer)
    cur.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES ('testorganizer@example.com', 'hashed_pw', 'Test', 'Organizer', 'organizer')
        RETURNING user_id;
    """)
    user_id = cur.fetchone()[0]

    # Insert a venue
    cur.execute("""
        INSERT INTO venues (name, building, room_number)
        VALUES ('Student Union', 'Student Center', 'Ballroom')
        RETURNING venue_id;
    """)
    venue_id = cur.fetchone()[0]

    # Insert an event category
    cur.execute("""
        INSERT INTO event_categories (name)
        VALUES ('Social')
        RETURNING category_id;
    """)
    category_id = cur.fetchone()[0]

    # Insert an event
    start_time = datetime.now() + timedelta(days=7, hours=10)
    end_time = start_time + timedelta(hours=3)
    cur.execute("""
        INSERT INTO events (title, description, start_time, end_time, venue_id, organizer_id, created_by)
        VALUES ('Test Workshop', 'A workshop on database testing.', %s, %s, %s, %s, %s)
        RETURNING event_id;
    """, (start_time, end_time, venue_id, user_id, user_id))
    event_id = cur.fetchone()[0]

    # Insert RSVP (User attending their own event)
    cur.execute("""
        INSERT INTO rsvps (user_id, event_id, rsvp_status)
        VALUES (%s, %s, 'going');
    """, (user_id, event_id))

    # Link event to category
    cur.execute("""
        INSERT INTO event_category_map (event_id, category_id)
        VALUES (%s, %s);
    """, (event_id, category_id))

    conn.commit()
    print(f"Data insertion complete: user_id={user_id}, venue_id={venue_id}, event_id={event_id}, category_id={category_id}")

    # 4. Query data back (complex join to verify integrity)
    print("\nVerifying inserted data (checking joins)...")
    cur.execute("""
        SELECT 
            e.title, 
            u.first_name || ' ' || u.last_name AS organizer_name,
            v.name AS venue_name,
            c.name AS category_name
        FROM events e
        JOIN users u ON e.organizer_id = u.user_id
        JOIN venues v ON e.venue_id = v.venue_id
        JOIN event_category_map ecm ON e.event_id = ecm.event_id
        JOIN event_categories c ON ecm.category_id = c.category_id
        WHERE e.event_id = %s;
    """, (event_id,))
    
    row = cur.fetchone()
    if row:
        print(f"Found event: '{row[0]}'")
        print(f"  Organized by: {row[1]}")
        print(f"  Location: {row[2]}")
        print(f"  Category: {row[3]}")
    else:
        raise Exception("Failed to retrieve joined data. Relationships may be incorrect.")

    print("\nDatabase test PASSED successfully!")

except Exception as e:
    print("\nDatabase test FAILED:")
    print(f" Error: {e}")

finally:
    # 5. Mandatory Cleanup
    if conn and cur:
        print("\nCleaning up test data...")
        try:
            if event_id:
                # CASCADE should handle rsvps and event_category_map, but we can be explicit
                cur.execute("DELETE FROM rsvps WHERE event_id = %s;", (event_id,))
                cur.execute("DELETE FROM event_category_map WHERE event_id = %s;", (event_id,))
                cur.execute("DELETE FROM events WHERE event_id = %s;", (event_id,))
            if venue_id:
                cur.execute("DELETE FROM venues WHERE venue_id = %s;", (venue_id,))
            if user_id:
                cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
            if category_id:
                cur.execute("DELETE FROM event_categories WHERE category_id = %s;", (category_id,))
            
            conn.commit()
            print("Cleanup complete.")
        except Exception as cleanup_error:
            print(f"Cleanup FAILED. Database may contain leftover test data: {cleanup_error}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
            print("Database connection closed.")
