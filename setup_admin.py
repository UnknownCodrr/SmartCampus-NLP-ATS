from database import register_user, get_connection


def create_master_admin():
    # This creates your first admin account so you aren't locked out of the fresh database
    success, msg = register_user("System Admin", "admin@smartcampus.edu", "admin123", "admin")

    # We also need to manually force the DB to accept registrations just in case
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO system_settings (setting_key, setting_value) VALUES ('allow_registration', '1') ON DUPLICATE KEY UPDATE setting_value = '1'")
    conn.commit()
    conn.close()

    print("✅ Database Seeded: Admin account created (admin@smartcampus.edu / admin123) and Registrations Opened.")


if __name__ == "__main__":
    create_master_admin()