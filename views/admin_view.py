import streamlit as st
import pandas as pd
import time
import random
from database import get_connection, get_registration_status, set_registration_status, reset_password, delete_user, \
    update_user_role, update_user_profile, log_action, get_system_logs, get_engine_status, set_engine_status, \
    is_session_valid, destroy_session, check_password_reset_flag, force_update_password
from admin_tools import get_maintenance_mode, set_maintenance_mode

# ==========================================
# HELPER: TOP-RIGHT WATERMARK
# ==========================================
def render_watermark():
    """Pushes a sleek version tag to the absolute top right corner"""
    spacer, version_col = st.columns([5, 1])
    with version_col:
        st.caption("⚙️ **v1.1.0-Beta** *(Genesis)*")


def get_all_users_admin():
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, email, role, DATE(created_at) as joined FROM users ORDER BY role, name")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def render_admin_dashboard(controller):
    render_watermark()

    admin_email = st.session_state.get('user_name', 'Admin')

    # --- NUKED THE DUPLICATE LOGOUT BUTTON ---
    st.title("🛡️ Super Admin Control Center")
    st.write(f"Welcome, **{admin_email}**. You have full system access.")

    st.divider()

    # --- 🛑 THE CONCURRENT SESSION INTERCEPTOR (TRIPWIRE) 🛑 ---
    if not is_session_valid(st.session_state.get('session_token')):
        st.error(
            "🚨 Security Alert: Session Expired! You have been securely logged out because your account was accessed from another device.")
        time.sleep(2.5)

        try:
            controller.remove('smartcampus_user')
        except Exception:
            pass

        st.session_state.clear()
        st.rerun()
    # --------------------------------------------------------

    # --- 🛑 THE PASSWORD SECURITY INTERCEPTOR 🛑 ---
    if check_password_reset_flag(st.session_state.user_id):
        st.subheader("🔒 Mandatory Security Update")
        st.warning(
            "Your password was reset by the System Toolkit. To secure your Super Admin account, you must set a personalized password right now.")

        with st.container(border=True):
            new_pw = st.text_input("New Password", type="password", key="admin_new_pw")
            confirm_pw = st.text_input("Confirm New Password", type="password", key="admin_conf_pw")

            if st.button("Update Password & Access Dashboard", type="primary", use_container_width=True):
                if not new_pw or not confirm_pw:
                    st.error("Please fill in both fields.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match. Please try again.")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    if force_update_password(st.session_state.user_id, new_pw):
                        st.success("✅ Password successfully secured! Redirecting...")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Database error while updating password.")

        # CRITICAL: Stops the Admin from seeing the dashboard until they reset
        st.stop()
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ System Settings", "🔐 User Management", "📋 System Audit", "📜 Activity Logs"])

    with tab1:
        st.subheader("Global Platform Toggles")
        st.write("Control access to the platform in real-time.")

        col_reg, col_maint = st.columns(2)

        with col_reg:
            with st.container(border=True):
                st.markdown("### 📝 Account Registrations")
                current_reg = get_registration_status()
                if current_reg:
                    st.success("Status: **OPEN**")
                else:
                    st.warning("Status: **CLOSED**")

                if st.toggle("Allow New Student Sign-ups", value=current_reg, key="toggle_reg"):
                    if not current_reg:
                        set_registration_status(True)
                        log_action(admin_email, "OPENED account registrations")
                        st.rerun()
                else:
                    if current_reg:
                        set_registration_status(False)
                        log_action(admin_email, "CLOSED account registrations")
                        st.rerun()

        with col_maint:
            with st.container(border=True):
                st.markdown("### 🔴 Maintenance Mode")
                current_maint = get_maintenance_mode()
                if current_maint:
                    st.error("Status: **ACTIVE**")
                else:
                    st.info("Status: **OFF**")

                if st.toggle("Activate Maintenance Lock", value=current_maint, key="toggle_maint"):
                    if not current_maint:
                        set_maintenance_mode(True)
                        log_action(admin_email, "ACTIVATED Maintenance Mode")
                        st.rerun()
                else:
                    if current_maint:
                        set_maintenance_mode(False)
                        log_action(admin_email, "DEACTIVATED Maintenance Mode")
                        st.rerun()

        st.divider()

        # --- UPDATED: 3-COLUMN AI ENGINE TOGGLES ---
        st.markdown("### 🧠 AI Engine Resource Management")
        st.caption("Turn off heavy models to save server RAM. The Exact-Match Dictionary is always active.")

        with st.container(border=True):
            ml_status = get_engine_status('ml_engine')
            llm_status = get_engine_status('llm_engine')
            api_status = get_engine_status('api_engine')

            col_ml, col_llm, col_api = st.columns(3)
            with col_ml:
                new_ml_status = st.toggle("Contextual NER (ML)", value=ml_status)
                if new_ml_status != ml_status:
                    set_engine_status('ml_engine', new_ml_status)
                    log_action(admin_email, f"{'ENABLED' if new_ml_status else 'DISABLED'} ML Engine")
                    st.success(f"ML Engine is now {'ON' if new_ml_status else 'OFF'}.")
                    time.sleep(0.5)
                    st.rerun()

            with col_llm:
                new_llm_status = st.toggle("Gemma 2B (LLM)", value=llm_status)
                if new_llm_status != llm_status:
                    set_engine_status('llm_engine', new_llm_status)
                    log_action(admin_email, f"{'ENABLED' if new_llm_status else 'DISABLED'} LLM Engine")
                    st.success(f"LLM Engine is now {'ON' if new_llm_status else 'OFF'}.")
                    time.sleep(0.5)
                    st.rerun()

            with col_api:
                new_api_status = st.toggle("Cloud API (Free)", value=api_status)
                if new_api_status != api_status:
                    set_engine_status('api_engine', new_api_status)
                    log_action(admin_email, f"{'ENABLED' if new_api_status else 'DISABLED'} API Engine")
                    st.success(f"API Engine is now {'ON' if new_api_status else 'OFF'}.")
                    time.sleep(0.5)
                    st.rerun()
        # ----------------------------------------

    with tab2:
        st.subheader("Account Operations")

        edit_col, role_col = st.columns(2)
        with edit_col:
            with st.container(border=True):
                st.markdown("#### ✏️ Edit User Details")
                target_edit_email = st.text_input("Current Email Address", key="edit_target")
                new_name = st.text_input("New Name", key="edit_name")
                new_email = st.text_input("New Email Address", key="edit_new_email")

                if st.button("Update Profile", type="primary", use_container_width=True):
                    if target_edit_email and new_name and new_email:
                        success, msg = update_user_profile(target_edit_email, new_name, new_email)
                        if success:
                            log_action(admin_email, f"Edited profile for {target_edit_email} (New Email: {new_email})")
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill out all fields.")

        with role_col:
            with st.container(border=True):
                st.markdown("#### 🔄 Change Account Role")
                role_email = st.text_input("User's Email Address", key="role_email")
                new_role = st.selectbox("Select New Role", ["student", "coordinator", "admin"], key="role_select")

                if st.button("Update Role", type="primary", use_container_width=True):
                    if role_email:
                        if role_email == admin_email and new_role != 'admin':
                            st.error("You cannot demote your own active Admin account.")
                        else:
                            success, msg = update_user_role(role_email, new_role)
                            if success:
                                log_action(admin_email, f"Changed role of {role_email} to {new_role}")
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.warning("Please provide an email address.")

        st.divider()

        op_col1, op_col2 = st.columns(2)
        with op_col1:
            with st.container(border=True):
                st.markdown("#### 🔑 Force Password Reset")
                st.caption("Auto-generates a 6-digit PIN and locks the user until they change it.")
                reset_email = st.text_input("User's Email Address", key="reset_em")

                if st.button("🚨 Generate PIN & Reset", type="primary", use_container_width=True):
                    if reset_email:
                        temp_pin = str(random.randint(100000, 999999))
                        success, msg = reset_password(reset_email.strip(), temp_pin)

                        if success:
                            log_action(admin_email, f"Force reset password for {reset_email}")
                            st.success(f"✅ Account Locked & Reset! The user MUST change this on their next login.")
                            st.error(f"🎫 TEMPORARY PIN: **{temp_pin}**")
                            st.caption("Copy this PIN and securely send it to the user. It will not be shown again.")
                        else:
                            st.warning(msg)
                    else:
                        st.warning("Please enter an email address.")

        with op_col2:
            with st.container(border=True):
                st.markdown("#### 🗑️ Delete User Account")
                del_email = st.text_input("Account Email to Delete", key="del_em")
                confirm_del = st.checkbox("I confirm I want to permanently delete this account.", key="del_confirm")

                if st.button("Delete Account", type="primary", use_container_width=True):
                    if del_email and confirm_del:
                        if del_email == admin_email:
                            st.error("You cannot delete your own active Admin account.")
                        else:
                            success, msg = delete_user(del_email)
                            if success:
                                log_action(admin_email, f"Permanently deleted account: {del_email}")
                                st.success(msg)
                            else:
                                st.error(msg)
                    elif not confirm_del:
                        st.warning("You must check the confirmation box.")

    with tab3:
        st.subheader("Platform Directory")
        all_users = get_all_users_admin()
        if all_users:
            df_users = pd.DataFrame(all_users)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Accounts", len(df_users))
            m2.metric("Students", len(df_users[df_users['role'] == 'student']))
            m3.metric("Coordinators", len(df_users[df_users['role'] == 'coordinator']))
            m4.metric("Admins", len(df_users[df_users['role'] == 'admin']))

            st.divider()
            search = st.text_input("🔍 Search by name or email...", key="admin_search")
            if search:
                term = search.lower()
                df_users = df_users[df_users['name'].str.lower().str.contains(term) |
                                    df_users['email'].str.lower().str.contains(term)]

            df_display = df_users.rename(
                columns={'id': 'ID', 'name': 'Name', 'email': 'Email', 'role': 'Role', 'joined': 'Join Date'})
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No users found in the database.")

    with tab4:
        st.subheader("System Activity Logs")
        st.write("Review recent administrative and system actions.")

        if st.button("🔄 Refresh Logs"):
            st.rerun()

        logs = get_system_logs()
        if logs:
            df_logs = pd.DataFrame(logs)
            df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_logs = df_logs.rename(columns={
                'timestamp': 'Date & Time',
                'user_email': 'Performed By',
                'action': 'Action Description'
            })
            df_logs = df_logs[['Date & Time', 'Performed By', 'Action Description']]
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("No activity logs found. Try performing an action in the User Management tab!")