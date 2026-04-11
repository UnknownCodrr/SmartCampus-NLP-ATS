import random
from database import reset_password, delete_user, get_registration_status, set_registration_status, get_connection, \
    get_engine_status, set_engine_status


def init_admin_settings():
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value VARCHAR(50) NOT NULL
            )
        """)
        cursor.execute(
            "INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES ('maintenance_mode', '0')")
        conn.commit()
    except Exception as e:
        print(f"DB Init Error: {e}")
    finally:
        cursor.close()
        conn.close()


def get_maintenance_mode():
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_mode'")
        res = cursor.fetchone()
        return res[0] == '1' if res else False
    except:
        return False
    finally:
        cursor.close()
        conn.close()


def set_maintenance_mode(is_active):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    val = '1' if is_active else '0'
    try:
        cursor.execute("UPDATE system_settings SET setting_value = %s WHERE setting_key = 'maintenance_mode'", (val,))
        conn.commit()
        return True
    except:
        return False
    finally:
        cursor.close()
        conn.close()


def run_cli_toolkit():
    print("\n=== SmartCampus Admin Toolkit ===")
    print("1. Force Password Reset (Auto-Generate PIN)")
    print("2. Delete a user account")
    print("3. Toggle New Account Registrations")
    print("4. Toggle Maintenance Mode")
    print("5. Toggle AI Engines (ML / LLM / API)")

    choice = input("\nSelect an option (1, 2, 3, 4, or 5): ")

    if choice == '1':
        target_email = input("Enter the user's email address: ")
        temp_pin = str(random.randint(100000, 999999))
        success, message = reset_password(target_email, temp_pin)

        if success:
            print(f"\n✅ SUCCESS: Account Locked & Reset!")
            print(f"🎫 TEMPORARY PIN: {temp_pin}")
            print("The user MUST change this on their next login.")
        else:
            print(f"\n❌ FAILED: {message}")

    elif choice == '2':
        target_email = input("Enter the email of the account to DELETE: ")
        confirm = input(f"Are you sure you want to delete {target_email}? (y/n): ")
        if confirm.lower() == 'y':
            success, message = delete_user(target_email)
            print(f"\nResult: {message}")
        else:
            print("\nDeletion cancelled.")

    elif choice == '3':
        current_status = get_registration_status()
        print(f"\nCurrent Registration Status: {'OPEN' if current_status else 'CLOSED'}")
        print("1. OPEN Registrations")
        print("2. CLOSE Registrations")
        toggle_choice = input("Select an option (1 or 2): ")
        set_registration_status(True if toggle_choice == '1' else False)
        print("\nResult: Registration status updated.")

    elif choice == '4':
        current_maint = get_maintenance_mode()
        print(f"\nCurrent Maintenance Status: {'ACTIVE' if current_maint else 'OFF'}")
        print("1. ACTIVATE Maintenance Mode (Lock site)")
        print("2. DEACTIVATE Maintenance Mode (Unlock site)")
        toggle_choice = input("Select an option (1 or 2): ")
        set_maintenance_mode(True if toggle_choice == '1' else False)
        print("\nResult: Maintenance mode updated.")

    elif choice == '5':
        print("\n--- AI Engine Status ---")
        print(f"ML Engine:  {'ON' if get_engine_status('ml_engine') else 'OFF'}")
        print(f"LLM Engine: {'ON' if get_engine_status('llm_engine') else 'OFF'}")
        print(f"API Engine: {'ON' if get_engine_status('api_engine') else 'OFF'}")

        print("\n1. Toggle ML Engine")
        print("2. Toggle LLM Engine")
        print("3. Toggle API Engine")
        eng_choice = input("Select an option (1, 2, or 3): ")

        if eng_choice == '1':
            curr = get_engine_status('ml_engine')
            set_engine_status('ml_engine', not curr)
            print(f"\nResult: ML Engine is now {'OFF' if curr else 'ON'}")
        elif eng_choice == '2':
            curr = get_engine_status('llm_engine')
            set_engine_status('llm_engine', not curr)
            print(f"\nResult: LLM Engine is now {'OFF' if curr else 'ON'}")
        elif eng_choice == '3':
            curr = get_engine_status('api_engine')
            set_engine_status('api_engine', not curr)
            print(f"\nResult: API Engine is now {'OFF' if curr else 'ON'}")


if __name__ == "__main__":
    init_admin_settings()
    run_cli_toolkit()