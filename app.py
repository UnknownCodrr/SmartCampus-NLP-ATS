import streamlit as st
import time
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Configure the main page (MUST be the absolute first Streamlit command)
st.set_page_config(
    page_title="SmartCampus | AI Placement Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* Adaptive background and border using semi-transparent grey */
    .stTextInput div[data-baseweb="input"],
    .stTextArea div[data-baseweb="textarea"],
    .stNumberInput div[data-baseweb="input"],
    .stSelectbox div[data-baseweb="select"],
    .stDateInput div[data-baseweb="input"] {
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        background-color: rgba(128, 128, 128, 0.05) !important;
        border-radius: 6px !important;
        padding: 2px;
    }

    /* Use Streamlit's native primary color for the glow so it matches automatically */
    .stTextInput div[data-baseweb="input"]:focus-within,
    .stTextArea div[data-baseweb="textarea"]:focus-within,
    .stNumberInput div[data-baseweb="input"]:focus-within,
    .stSelectbox div[data-baseweb="select"]:focus-within,
    .stDateInput div[data-baseweb="input"]:focus-within {
        border: 1px solid var(--primary-color) !important;
        box-shadow: 0 0 0 1px var(--primary-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ADVANCED UI: GLOBAL PAGE TRANSITION & CLEANUP ENGINE ---
st.markdown("""
<style>
/* 1. Smooth Fade & Slide Transition */
@keyframes smoothFade {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0px); }
}
[data-testid="stAppViewContainer"] {
    animation: smoothFade 0.4s ease-out;
}
</style>
""", unsafe_allow_html=True)
# ------------------------------------------------------------

from streamlit_cookies_controller import CookieController
from views.auth_view import show_home, show_login, show_register
from views.student_view import render_student_dashboard
from views.coordinator_view import render_coordinator_dashboard
from views.admin_view import render_admin_dashboard
from admin_tools import init_admin_settings, get_maintenance_mode
from database import authenticate_user, register_new_session, destroy_session, is_session_valid, init_db

# 2. Initialize the controller
controller = CookieController()


def init_session_state():
    def apply_defaults():
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.session_token = None

    if 'logged_in' not in st.session_state:
        apply_defaults()

    saved_user = controller.get('smartcampus_user')

    if saved_user and not st.session_state.logged_in:
        token = saved_user.get('session_token')

        if not token or not is_session_valid(token):
            try:
                controller.remove('smartcampus_user')
            except Exception:
                pass
            st.session_state.clear()
            apply_defaults()
            return

        st.session_state.logged_in = True
        st.session_state.user_id = saved_user['id']
        st.session_state.user_role = saved_user['role']
        st.session_state.user_name = saved_user['name']
        st.session_state.session_token = token


# --- WRAPPER FUNCTIONS ---
def student_dash():
    render_student_dashboard(controller)


def coordinator_dash():
    render_coordinator_dashboard(controller)


def admin_dash():
    render_admin_dashboard(controller)


# -------------------------


def main():
    init_db()
    init_admin_settings()
    init_session_state()

    # ==========================================
    # THE GATEKEEPER: MAINTENANCE MODE
    # ==========================================
    if get_maintenance_mode():
        if st.session_state.get('user_role') != 'admin':
            st.empty()
            st.title("🚧 Site Under Maintenance")
            st.warning("SmartCampus is currently undergoing scheduled IT maintenance. We'll be back online shortly.")
            st.info("Your application progress and profile data are safely stored in our database.")
            st.divider()

            with st.expander("Super Admin Override"):
                st.caption("Only accounts with the 'admin' role can unlock the platform.")
                admin_email = st.text_input("Admin Email", key="maint_em")
                admin_pw = st.text_input("Admin Password", type="password", key="maint_pw")

                if st.button("Bypass Lock", type="primary"):
                    user = authenticate_user(admin_email, admin_pw)
                    if user and user['role'] == 'admin':
                        st.session_state.logged_in = True
                        st.session_state.user_role = user['role']
                        st.session_state.user_id = user['id']
                        st.session_state.user_name = user['name']

                        new_token = str(uuid.uuid4())
                        register_new_session(user['id'], new_token)
                        st.session_state.session_token = new_token

                        st.success("Admin access granted.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Access Denied. Invalid credentials or insufficient permissions.")

            st.stop()

    # ==========================================
    # NATIVE STREAMLIT ROUTING (NO SIDEBAR)
    # ==========================================
    if not st.session_state.logged_in:
        p_home = st.Page(show_home, title="Welcome", icon="🏠", default=True)
        p_login = st.Page(show_login, title="Login", icon="🔑")
        p_register = st.Page(show_register, title="Register", icon="📝")

        if 'pages' not in st.session_state:
            st.session_state.pages = {
                'home': p_home,
                'login': p_login,
                'register': p_register
            }

        pg = st.navigation([p_home, p_login, p_register], position="hidden")
        pg.run()

    else:
        role = st.session_state.user_role

        if role == 'student':
            pg = st.navigation([st.Page(student_dash, title="Student Dashboard", icon="🎓")], position="hidden")
        elif role == 'coordinator':
            pg = st.navigation([st.Page(coordinator_dash, title="Coordinator Dashboard", icon="👔")], position="hidden")
        elif role == 'admin':
            pg = st.navigation([st.Page(admin_dash, title="Admin Control Center", icon="🛡️")], position="hidden")

        pg.run()

        st.divider()
        if st.button("🚪 Secure Logout", type="primary"):
            destroy_session(st.session_state.get('session_token'))
            try:
                controller.remove('smartcampus_user')
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()


if __name__ == "__main__":
    main()