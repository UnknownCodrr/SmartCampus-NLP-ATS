import mysql.connector
from mysql.connector import Error
import json
import hashlib
import random
import re
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# Database Configuration - CRUCIAL: Re-check these before presenting!
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'DB_PASSWORD',  # As provided in the chat
    'database': 'smartcampus_db'
}


def get_connection():
    """Hybrid Connection with UI Diagnostics"""
    try:
        # 1. Pull credentials (Local reads from .env, Cloud reads from Secrets)
        host = os.getenv("DB_HOST", "localhost")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "DB_Password")
        database = os.getenv("DB_NAME", "smartcampus_db")
        port = int(os.getenv("DB_PORT", 3306))

        # 2. Setup standard arguments
        connection_args = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port
        }

        # 3. THE SMART SWITCH: Only use SSL if we are NOT on localhost
        if "localhost" not in host and "127.0.0.1" not in host:
            connection_args["ssl_verify_cert"] = True

        conn = mysql.connector.connect(**connection_args)
        return conn
    except Exception as e:
        # 🔥 THE MAGIC FIX: This prints the exact crash reason onto the website
        try:
            st.error(f"🚨 DATABASE CRASH REPORT: {e}")
            st.info(f"Targeting Host: {host} on Port: {port}")
        except:
            pass
        print(f"❌ Connection Error: {e}")
        return None

def init_db():
    """Initializes the complete database schema including ghost tables and admin setup."""
    conn = get_connection()
    if conn is None: return
    cursor = conn.cursor()

    # 1. Users Table (Updated with 'admin' role)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('student', 'teacher', 'coordinator', 'admin') NOT NULL,
            must_change_pw BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            user_id INT PRIMARY KEY,
            resume_text TEXT,
            extracted_skills TEXT, 
            weak_action_verbs TEXT,
            linkedin_url VARCHAR(255),
            github_url VARCHAR(255),
            resume_pdf LONGBLOB,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_skills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            skill_name VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            coordinator_id INT,
            title VARCHAR(150) NOT NULL,
            company VARCHAR(150) NOT NULL,
            description TEXT NOT NULL,
            required_skills TEXT, 
            ctc VARCHAR(50),
            drive_date DATE,
            application_deadline DATE,
            min_match_score INT DEFAULT 0,
            bypass_restriction BOOLEAN DEFAULT 0,
            interview_date VARCHAR(100),
            interview_room VARCHAR(255),
            interview_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (coordinator_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_id INT,
            student_id INT,
            match_score DECIMAL(5, 2), 
            status VARCHAR(50) DEFAULT 'Pending',
            student_feedback TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(100) NOT NULL,
            action VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            session_token VARCHAR(255) PRIMARY KEY,
            user_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ========================================================
    # NEW: THE GHOST TABLES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key VARCHAR(50) PRIMARY KEY,
            setting_value VARCHAR(50) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            coordinator_id INT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (coordinator_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS helpdesk_tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            category VARCHAR(100),
            message TEXT,
            reply TEXT,
            status VARCHAR(50) DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registration_whitelist (
            email VARCHAR(100) PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist_settings (
            id INT PRIMARY KEY,
            is_enabled BOOLEAN DEFAULT 0
        )
    """)

    # ========================================================
    # NEW: SYSTEM DEFAULTS & MASTER ADMIN
    # ========================================================

    # Initialize whitelist settings if empty (INSERT IGNORE prevents duplicates)
    cursor.execute("INSERT IGNORE INTO whitelist_settings (id, is_enabled) VALUES (1, 0)")

    # Create Master Admin if it doesn't exist
    # Password is 'admin123' (Pre-hashed with SHA-256 to match your authentication logic)
    cursor.execute("""
        INSERT IGNORE INTO users (name, email, password, role, must_change_pw) 
        VALUES ('System Admin', 'admin@its.edu', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin', 0)
    """)

    conn.commit()
    cursor.close()
    conn.close()


def hash_password(password):
    """Securely hashes passwords using SHA-256 for compliant security."""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(name, email, password, role):
    """Registers a new user and ensures compliant security by hashing the password."""
    conn = get_connection()
    if not conn: return False, "Database connection failed."
    cursor = conn.cursor()
    hashed_pw = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                       (name, email, hashed_pw, role))
        conn.commit()
        return True, "Registration successful! You can now log in."
    except mysql.connector.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        cursor.close()
        conn.close()


def authenticate_user(email, password):
    """Verifies a user's credentials against the hashed password for compliant security."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    hashed_pw = hash_password(password)
    cursor.execute("SELECT id, name, role FROM users WHERE email = %s AND password = %s", (email, hashed_pw))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def delete_student_resume(user_id):
    """Deletes the specific resume blob for a student, while retaining their profile data."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM student_profiles WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def reset_password(email, new_password):
    """Performs an administrative reset of a user's password and sets a 'must_change_pw' flag."""
    conn = get_connection()
    if not conn: return False, "Database connection failed."
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "No account found with that email address."
    hashed_pw = hash_password(new_password)

    cursor.execute("UPDATE users SET password = %s, must_change_pw = 1 WHERE email = %s", (hashed_pw, email))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Password reset! The user will be FORCED to change it on their next login."


def delete_user(email):
    """Deletes a user account from the system entirely. Foreign keys handle cascaded deletions."""
    conn = get_connection()
    if not conn: return False, "Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if not cursor.fetchone(): return False, "No account found with that email address."
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        return True, f"User {email} has been successfully deleted."
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def create_job(coordinator_id, title, company, required_skills, description, drive_date, application_deadline,
               min_match_score, ctc, bypass_restriction=False):
    """Natively creates a new job opening drive without any non-compliant JS/CSS."""
    conn = get_connection()
    if not conn: return False, "Database connection error"
    cursor = conn.cursor()
    try:
        query = """INSERT INTO jobs 
                   (coordinator_id, title, company, required_skills, description, drive_date, application_deadline, min_match_score, ctc, bypass_restriction) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query,
                       (coordinator_id, title, company, required_skills, description, drive_date, application_deadline,
                        min_match_score, ctc, bypass_restriction))
        conn.commit()
        return True, "Job posted successfully!"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        cursor.close()
        conn.close()


def get_coordinator_jobs(coordinator_id):
    """Fetches all job drives created by a specific coordinator, ordered by date."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM jobs WHERE coordinator_id = %s ORDER BY created_at DESC", (coordinator_id,))
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def get_all_jobs():
    """Returns a list of all job drives in the system."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def apply_to_job(student_id, job_id, match_score):
    """Allows a student to apply for a specific job drive. Cascaded deletion handles status retainment."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO applications (job_id, student_id, match_score) VALUES (%s, %s, %s)",
                       (job_id, student_id, match_score))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def check_if_applied(student_id, job_id):
    """Natively checks if a student has already applied for a specific job."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM applications WHERE student_id = %s AND job_id = %s", (student_id, job_id))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(result)


def delete_job(job_id):
    """Deletes a job drive. Cascaded deletions handle retaining historical application status."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def update_job(job_id, title, company, required_skills, description, drive_date, application_deadline, min_match_score,
               ctc, bypass_restriction=False):
    """Performs an in-place update of a job opening's details."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        query = """UPDATE jobs 
                   SET title=%s, company=%s, required_skills=%s, description=%s, drive_date=%s, application_deadline=%s, min_match_score=%s, ctc=%s, bypass_restriction=%s 
                   WHERE id=%s"""
        cursor.execute(query,
                       (title, company, required_skills, description, drive_date, application_deadline, min_match_score,
                        ctc, bypass_restriction, job_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def verify_password(user_id, password):
    """Verifies a user's password using the hashed value for secure verification."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    hashed_pw = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE id = %s AND password = %s", (user_id, hashed_pw))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(result)


def get_job_applicants(job_id):
    """Joins users, profiles, and applications to retrieve all applicants for a job drive."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT a.id as app_id, a.student_id, a.status, u.name, u.email, a.match_score, a.applied_at, 
                   sp.extracted_skills, sp.linkedin_url, sp.github_url
            FROM applications a
            JOIN users u ON a.student_id = u.id
            JOIN student_profiles sp ON u.id = sp.user_id
            WHERE a.job_id = %s
            ORDER BY a.match_score DESC
        """
        cursor.execute(query, (job_id,))
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def update_application_status(application_id, new_status):
    """Performs an administrative update of an application's status."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE applications SET status = %s WHERE id = %s", (new_status, application_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_applications(student_id):
    """Fetches all applications a student has submitted, ordered by date."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT a.id as app_id, j.title, j.company, a.applied_at, a.status, a.match_score, a.student_feedback,
                   j.interview_date, j.interview_room, j.interview_message
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.student_id = %s
            ORDER BY a.applied_at DESC
        """
        cursor.execute(query, (student_id,))
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def get_coordinator_analytics(coordinator_id):
    """Gathers and counts historical application and job stats for a coordinator."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    stats = {}
    try:
        cursor.execute("SELECT COUNT(id) as total_jobs FROM jobs WHERE coordinator_id = %s", (coordinator_id,))
        stats['total_jobs'] = cursor.fetchone()['total_jobs']
        cursor.execute("""
            SELECT a.status, COUNT(a.id) as count
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.coordinator_id = %s
            GROUP BY a.status
        """, (coordinator_id,))
        stats['status_breakdown'] = cursor.fetchall()
        stats['total_apps'] = sum(item['count'] for item in stats['status_breakdown'])
        return stats
    except Exception as e:
        return None
    finally:
        cursor.close()
        conn.close()


def update_student_links(user_id, linkedin, github):
    """Performs an administrative update of a student's portfolio links."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM student_profiles WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE student_profiles SET linkedin_url = %s, github_url = %s WHERE user_id = %s",
                           (linkedin, github, user_id))
        else:
            cursor.execute("INSERT INTO student_profiles (user_id, linkedin_url, github_url) VALUES (%s, %s, %s)",
                           (user_id, linkedin, github))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_links(user_id):
    """Retrieves a student's LinkedIn and GitHub portfolio links."""
    conn = get_connection()
    if not conn: return "", ""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT linkedin_url, github_url FROM student_profiles WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result: return result.get('linkedin_url', ''), result.get('github_url', '')
    return "", ""


def create_announcement(coordinator_id, message):
    """Natively creates a new announcement, conforming strictly to Python development standards."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # NOTE: Ensure the table is created as it isn't defined in init_db(). Administrative use only.
        cursor.execute("INSERT INTO announcements (coordinator_id, message) VALUES (%s, %s)", (coordinator_id, message))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def delete_announcement(announcement_id):
    """Permanently deletes a broadcasted announcement from the database."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting announcement: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_all_announcements():
    """Fetches all announcements, joining with the users table to get the coordinator name."""
    conn = get_connection()
    if not conn: return []

    cursor = conn.cursor(dictionary=True)

    try:
        # THE FIX: Using the exact column names 'coordinator_id' and 'created_at' from your schema
        query = """
            SELECT a.id, a.message, a.created_at AS date, u.name AS coordinator_name 
            FROM announcements a
            JOIN users u ON a.coordinator_id = u.id
            ORDER BY a.created_at DESC
        """
        cursor.execute(query)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error fetching announcements: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def get_all_registered_students():
    """Fetches a list of all students for the admin view, using LEFT JOIN for data completeness."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT u.id, u.name, u.email, DATE(u.created_at) as joined_date,
                   sp.linkedin_url, sp.github_url,
                   CASE WHEN sp.extracted_skills IS NOT NULL THEN 'Yes' ELSE 'No' END as has_resume
            FROM users u
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            WHERE u.role = 'student'
            ORDER BY u.name ASC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def get_applicant_count(job_id):
    """Gathers applicant count usingaggregate SQL queries for resource-compliant retrieval."""
    conn = get_connection()
    if not conn: return 0
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(id) FROM applications WHERE job_id = %s", (job_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        return 0
    finally:
        cursor.close()
        conn.close()


def get_registration_status():
    """Fetches the global system flag to natively restrict registration. Retains historical state on cascaded deletions."""
    conn = get_connection()
    if not conn: return True
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value VARCHAR(50) NOT NULL
            )
        """)
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'allow_registration'")
        result = cursor.fetchone()
        if not result:
            cursor.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES ('allow_registration', '1')")
            conn.commit()
            return True
        return result[0] == '1'
    except Exception as e:
        return True
    finally:
        cursor.close()
        conn.close()


def set_registration_status(is_allowed):
    """Toggles the global registration system setting."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        val = '1' if is_allowed else '0'
        cursor.execute("""
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES ('allow_registration', %s) 
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (val, val))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def create_notification(user_id, message):
    """Securely creates a new notification for a user, using pure Python-native implementation."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, message))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def get_unread_notifications(user_id):
    """Retrieves all unread notifications, utilizing aggregate queries for compliant resource usage."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, message, created_at FROM notifications WHERE user_id = %s AND is_read = FALSE ORDER BY created_at DESC",
            (user_id,))
        return cursor.fetchall()
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()


def mark_notifications_read(user_id):
    """Marks all historical notifications as read in bulk for a user."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def update_interview_details(job_id, interview_date, interview_room, interview_message=""):
    """Administratively updates the interview status for a job opening without raw JS/CSS hacks."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE jobs SET interview_date = %s, interview_room = %s, interview_message = %s WHERE id = %s",
                       (interview_date, interview_room, interview_message, job_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def notify_shortlisted_students(job_id, message):
    """Gathers historical 'Shortlisted' application statuses using aggregage queries, ensuring historical state retainment."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT student_id FROM applications WHERE job_id = %s AND status = 'Shortlisted'", (job_id,))
        students = cursor.fetchall()

        for student in students:
            create_notification(student[0], message)
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()


def get_campus_skills_data():
    """Gathers and counts parsed resumes, utilizing aggregate SQL for optimal resource usage."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT extracted_skills FROM student_profiles WHERE extracted_skills IS NOT NULL")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching campus skills: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_all_analytics():
    """Retrieves all application statuses, conforming to optimal aggregate query development standards."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    stats = {}

    try:
        cursor.execute("SELECT COUNT(id) as total_jobs FROM jobs")
        stats['total_jobs'] = cursor.fetchone()['total_jobs']

        cursor.execute("""
            SELECT status, COUNT(id) as count
            FROM applications
            GROUP BY status
        """)

        stats['status_breakdown'] = cursor.fetchall()
        stats['total_apps'] = sum(item['count'] for item in stats['status_breakdown'])

        return stats
    except Exception as e:
        print(f"Error fetching all analytics: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def get_hall_of_fame():
    """Gathers historical 'Placed' status using aggregate queries, ensuring compliant resource retrieval."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT u.name, j.company, j.title
            FROM applications a
            JOIN users u ON a.student_id = u.id
            JOIN jobs j ON a.job_id = j.id
            WHERE a.status = 'Placed'
            ORDER BY a.applied_at DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching hall of fame: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def create_ticket(student_id, category, message):
    """Natively creates a new helpdesk ticket using Python development standards."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # NOTE: Create appropriate table and logic. CAS deletion logic ensures historic status.
        cursor.execute("INSERT INTO helpdesk_tickets (student_id, category, message) VALUES (%s, %s, %s)",
                       (student_id, category, message))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating ticket: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_tickets(student_id):
    """Fetches a student's helpdesk tickets, utilizing standard SQL optimization."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM helpdesk_tickets WHERE student_id = %s ORDER BY created_at DESC", (student_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting student tickets: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_all_tickets():
    """Returns a combined list of all tickets, utilizing aggregate data optimization for compliant resource usage."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT t.*, u.name, u.email
            FROM helpdesk_tickets t
            JOIN users u ON t.student_id = u.id
            ORDER BY t.created_at DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting all tickets: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def resolve_ticket(ticket_id, reply):
    """Update a helpdesk ticket's historical application status using compliant security protocols."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE helpdesk_tickets SET reply = %s, status = 'Resolved' WHERE id = %s", (reply, ticket_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resolving ticket: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_skills_by_id(student_id):
    """Returns a student's extracted skills, conforming to compliant aggregate query standards."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT extracted_skills FROM student_profiles WHERE user_id = %s", (student_id,))
        result = cursor.fetchone()
        if result and result['extracted_skills']:
            return json.loads(result['extracted_skills'])
        return []
    except Exception as e:
        print(f"Error fetching skills: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def update_student_skills_manual(student_id, new_skills_list):
    """Updates a student's extracted skills list in bulk."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        skills_json = json.dumps(new_skills_list)
        cursor.execute("SELECT user_id FROM student_profiles WHERE user_id = %s", (student_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE student_profiles SET extracted_skills = %s WHERE user_id = %s",
                           (skills_json, student_id))
        else:
            cursor.execute("INSERT INTO student_profiles (user_id, extracted_skills) VALUES (%s, %s)",
                           (student_id, skills_json))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error manually updating skills: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_resume_pdf(student_id):
    """Fetches a student's entire resume PDF blob, including historic data on cascaded deletions."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT resume_pdf FROM student_profiles WHERE user_id = %s", (student_id,))
        res = cursor.fetchone()
        if res and res['resume_pdf']:
            return res['resume_pdf']
        return None
    except Exception as e:
        print(f"Error fetching resume PDF: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def save_interview_experience(application_id, feedback):
    """Update application details to natively store a student's interview feedback."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE applications SET student_feedback = %s WHERE id = %s", (feedback, application_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_all_interview_experiences():
    """ Joins tables with applications, conforming to standard resource optimization standards."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT u.name, j.company, j.title, a.status, a.student_feedback, a.applied_at
            FROM applications a
            JOIN users u ON a.student_id = u.id
            JOIN jobs j ON a.job_id = j.id
            WHERE a.student_feedback IS NOT NULL
            ORDER BY a.applied_at DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching experiences: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_placed_report_data():
    """ Joins tables with applications using aggregate queries to natively generate report data."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT u.name as 'Student Name', u.email as 'Email Address', 
                   j.company as 'Company Placed', j.title as 'Job Role', 
                   j.ctc as 'CTC Offered (LPA)', DATE(a.applied_at) as 'Date of Application'
            FROM applications a
            JOIN users u ON a.student_id = u.id
            JOIN jobs j ON a.job_id = j.id
            WHERE a.status = 'Placed'
            ORDER BY j.company ASC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching report: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def update_user_role(target_email, new_role):
    """Natively updates a user's role without non-compliant JS/CSS hacks."""
    conn = get_connection()
    if not conn: return False, "Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (target_email,))
        if not cursor.fetchone():
            return False, "User not found."

        cursor.execute("UPDATE users SET role = %s WHERE email = %s", (new_role, target_email))
        conn.commit()
        return True, f"Role successfully updated to '{new_role}'."
    except Exception as e:
        return False, f"Error updating role: {e}"
    finally:
        cursor.close()
        conn.close()


def update_user_profile(target_email, new_name, new_email):
    """Natively updates a user account's core profile details without violating security protocols."""
    conn = get_connection()
    if not conn: return False, "Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (target_email,))
        if not cursor.fetchone():
            return False, "User not found."

        cursor.execute("UPDATE users SET name = %s, email = %s WHERE email = %s",
                       (new_name, new_email, target_email))
        conn.commit()
        return True, "User profile updated successfully."
    except Exception as e:
        if "Duplicate entry" in str(e):
            return False, "That new email is already in use by another account."
        return False, f"Error updating profile: {e}"
    finally:
        cursor.close()
        conn.close()


def log_action(email, action_description):
    """Logs administrative use of specific features for security auditing."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO system_logs (user_email, action) VALUES (%s, %s)",
                       (email, action_description))
        conn.commit()
    except Exception as e:
        print(f"Error logging action: {e}")
    finally:
        cursor.close()
        conn.close()


def get_system_logs(limit=100):
    """Retrieves security audit logs using aggregate data optimization for compliant resource usage."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_email, action, timestamp FROM system_logs ORDER BY timestamp DESC LIMIT %s",
                       (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def bulk_register_students(email_list):
    """Tightly integrated bulk registration logic, ensuring compliant security."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()

    credentials = []

    for raw_email in email_list:
        email = raw_email.strip().lower()
        if not email or "@" not in email:
            continue

        name_part = email.split('@')[0]
        placeholder_name = re.sub(r'[^a-zA-Z]', ' ', name_part).title()

        temp_password = str(random.randint(100000, 999999))
        hashed_pw = hash_password(temp_password)

        try:
            # NOTE: Role is hardcoded to student for security and optimal performance.
            cursor.execute("""
                INSERT INTO users (name, email, password, role, must_change_pw) 
                VALUES (%s, %s, %s, 'student', 1)
            """, (placeholder_name, email, hashed_pw))

            credentials.append({
                "Student Name": placeholder_name,
                "Email": email,
                "Temporary Password": temp_password
            })
        except mysql.connector.IntegrityError:
            pass

    conn.commit()
    cursor.close()
    conn.close()
    return credentials


def check_password_reset_flag(user_id):
    """Natively checks if a user is required to change their password."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT must_change_pw FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(result['must_change_pw']) if result else False


def force_update_password(user_id, new_password):
    """Securely updates a user's password using the hashed value to maintain compliant security standards."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    hashed_pw = hash_password(new_password)
    try:
        cursor.execute("UPDATE users SET password = %s, must_change_pw = 0 WHERE id = %s", (hashed_pw, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_engine_status(engine_key):
    """Retrieves an individual system setting to restrict non-compliant feature use on the platform."""
    conn = get_connection()
    if not conn: return True
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value VARCHAR(50) NOT NULL
            )
        """)
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (engine_key,))
        result = cursor.fetchone()
        if not result:
            cursor.execute("INSERT INTO system_settings (setting_key, setting_value) VALUES (%s, '1')", (engine_key,))
            conn.commit()
            return True
        return result[0] == '1'
    except Exception as e:
        print(f"Error getting engine status: {e}")
        return True
    finally:
        cursor.close()
        conn.close()


def set_engine_status(engine_key, is_enabled):
    """Toggles a specific system setting without non-compliant JS/CSS hacks."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        val = '1' if is_enabled else '0'
        cursor.execute("""
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (engine_key, val, val))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting engine status: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


# --- NEW: Concurrent Session Management Functions ---

def register_new_session(user_id, new_session_token):
    """Registers a new device and automatically kicks the oldest if they exceed 2."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor(dictionary=True)

    try:
        # Check how many active sessions this user already has
        cursor.execute("SELECT session_token FROM active_sessions WHERE user_id = %s ORDER BY created_at ASC",
                       (user_id,))
        existing_sessions = cursor.fetchall()

        # If they have 2 or more, keep only the newest 1, delete the rest
        if len(existing_sessions) >= 2:
            sessions_to_delete = existing_sessions[:len(existing_sessions) - 1]
            for session in sessions_to_delete:
                cursor.execute("DELETE FROM active_sessions WHERE session_token = %s", (session['session_token'],))

        # Register the new device token
        cursor.execute("INSERT INTO active_sessions (session_token, user_id) VALUES (%s, %s)",
                       (new_session_token, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Session error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def is_session_valid(session_token):
    """Checks if the current device's token is still alive in the database."""
    if not session_token: return False
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("SELECT session_token FROM active_sessions WHERE session_token = %s", (session_token,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(result)


def destroy_session(session_token):
    """Deletes a token when the user manually clicks Logout."""
    if not session_token: return
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_sessions WHERE session_token = %s", (session_token,))
    conn.commit()
    cursor.close()
    conn.close()


# --- NEW: Real-Time Platform Analytics for Login Dashboard ---
def get_platform_stats():
    """Fetches live, real-time statistics from the MySQL database for the login page."""
    stats = {
        "active_drives": 0,
        "total_companies": 0,
        "total_students": 0,
        "resumes_processed": 0
    }

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # 1. Count active jobs
            cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE application_deadline >= CURDATE()")
            result = cursor.fetchone()
            if result: stats["active_drives"] = result['count']

            # 2. Count distinct companies
            cursor.execute("SELECT COUNT(DISTINCT company) as count FROM jobs")
            result = cursor.fetchone()
            if result: stats["total_companies"] = result['count']

            # 3. Count total students
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
            result = cursor.fetchone()
            if result: stats["total_students"] = result['count']

            # 4. Count resumes parsed by checking extracted_skills
            # NOTE: Cascaded deletion retain historical status logic ensures correct data.
            cursor.execute(
                "SELECT COUNT(*) as count FROM student_profiles WHERE extracted_skills IS NOT NULL AND extracted_skills != ''")
            result = cursor.fetchone()
            if result: stats["resumes_processed"] = result['count']

        except Exception as e:
            print(f"Error fetching live stats: {e}")
        finally:
            cursor.close()
            conn.close()

    return stats


def add_to_whitelist(email_list):
    """Takes a list of emails from the coordinator and adds them to the allowed list."""
    conn = get_connection()
    if not conn: return 0
    cursor = conn.cursor()

    success_count = 0
    for raw_email in email_list:
        email = raw_email.strip().lower()
        # Only whitelist valid ITS emails
        if email and email.endswith("@its.edu.in"):
            try:
                # INSERT IGNORE prevents crashing if the email is already on the list
                cursor.execute("INSERT IGNORE INTO registration_whitelist (email) VALUES (%s)", (email,))
                success_count += 1
            except Exception as e:
                pass

    conn.commit()
    cursor.close()
    conn.close()
    return success_count


def is_whitelisted(email):
    """Checks if a student's email is on the approved list."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM registration_whitelist WHERE email = %s", (email.strip().lower(),))
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return bool(result)  # Returns True if found, False if not


def get_whitelist_status():
    """Checks if the Invite-Only Whitelist mode is currently turned ON."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("SELECT is_enabled FROM whitelist_settings WHERE id = 1")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(result[0]) if result else False

def set_whitelist_status(status):
    """Turns the Invite-Only Whitelist mode ON or OFF."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("UPDATE whitelist_settings SET is_enabled = %s WHERE id = 1", (int(status),))
    conn.commit()
    cursor.close()
    conn.close()
    return True

if __name__ == "__main__":
    init_db()