import streamlit as st
from database import register_user, authenticate_user, get_registration_status, register_new_session, \
    get_platform_stats, get_whitelist_status, is_whitelisted
import time
import uuid
from streamlit_cookies_controller import CookieController
import requests
from streamlit_lottie import st_lottie

# Initialize the global controller here for the login logic
controller = CookieController()


# ==========================================
# HELPER: LOTTIE ANIMATION LOADER
# ==========================================
@st.cache_data(show_spinner=False)
def load_lottieurl(url: str):
    """Fetches Lottie animation JSON from the web with caching for fast reloads."""
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


# ==========================================
# HELPER: TOP-RIGHT WATERMARK
# ==========================================
def render_watermark():
    """Pushes a sleek version tag to the absolute top right corner"""
    spacer, version_col = st.columns([5, 1])
    with version_col:
        st.caption("⚙️ **v1.0.0-Beta** *(Genesis)*")


# ==========================================
# HELPER: TOP-LEFT LOGO
# ==========================================
def render_top_left_logo():
    """Renders the college logo uniformly across auth pages."""
    logo_col, _ = st.columns([1, 5])
    with logo_col:
        st.image("its_logo.jpg", width=120)
    st.write("")


# ==========================================
# HELPER: GLOBAL FOOTER
# ==========================================
def render_footer():
    st.write("")
    st.write("")
    st.divider()

    foot_col1, foot_col2, foot_col3 = st.columns(3)
    with foot_col1:
        st.write("#### 🏢 About SmartCampus")
        st.caption(
            "A placement portal designed to bridge the gap between student skills and industry requirements using Natural Language Processing.")

        with st.expander("📝 View Release Notes"):
            st.markdown("""
            **[v1.0.0-Beta] - Genesis Build**
            * Suppressed native Streamlit loading artifacts for seamless UX.
            * Removed Home Page animations for a cleaner enterprise UI.
            * Integrated dynamic Lottie UI animations for Auth forms.
            * Implemented Native SPA Routing (Zero Flicker).
            * Enforced @its.edu.in Domain Whitelisting.
            """)

    with foot_col2:
        st.write("#### 📞 Reach Us")
        st.caption("📍 **Campus:** ITS Mohan Nagar, Ghaziabad, UP")
        st.caption("✉️ **Email:** [redacted]")
    with foot_col3:
        st.write("#### 🛠️ System Info")
        st.caption("👨‍💻 **Developed by:** Abhinav, Aryan, Manmohan")


# ==========================================
# PAGE 1: THE HOME / LANDING PAGE
# ==========================================
def show_home():
    render_watermark()
    render_top_left_logo()
    registration_open = get_registration_status()

    # --- CENTERED MAIN CONTENT (STATIC, NO ANIMATIONS) ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎓 Welcome to SmartCampus")
        st.caption("Hybrid Intelligence Framework for Career Placements")

        st.image("its_placeholder.png", use_container_width=True)

        st.divider()

        st.subheader("🚀 Start Your Journey")
        st.write("AI-powered resume analysis & smart placement system.")
        st.write("")

        if st.button("🔑 Login", use_container_width=True, type="primary"):
            st.switch_page(st.session_state.pages['login'])

        if registration_open:
            if st.button("📝 Register", use_container_width=True):
                st.switch_page(st.session_state.pages['register'])
        else:
            st.info("ℹ️ **Registrations Closed:** New account creation is currently paused by the administration.")

    render_footer()


# ==========================================
# PAGE 2: THE LOGIN PAGE
# ==========================================
def show_login():
    render_watermark()
    render_top_left_logo()

    st.toast("Authentication servers online 🟢", icon="🔒")

    img_col, form_col = st.columns([1, 1.2], gap="large")

    with img_col:
        st.title("Welcome Back!")
        st.write("Log in to access your AI resume analysis and placement dashboard.")
        st.write("")
        # Load the Login Animation
        lottie_login = load_lottieurl("https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json")
        if lottie_login:
            st_lottie(lottie_login, height=250, key="login_anim")

        st.divider()

        st.write("📊 **Live Platform Activity**")
        db_stats = get_platform_stats()

        row1_col1, row1_col2 = st.columns(2)
        row1_col1.metric(label="Active Drives", value=db_stats["active_drives"])
        row1_col2.metric(label="Partnered Companies", value=db_stats["total_companies"])

        st.write("")

        row2_col1, row2_col2 = st.columns(2)
        row2_col1.metric(label="Registered Students", value=db_stats["total_students"])
        row2_col2.metric(label="Resumes Processed ✨", value=db_stats["resumes_processed"])

        st.caption("✨ Data synced securely via SmartCampus MySQL DB")

    with form_col:
        with st.container(border=True):
            st.subheader("🔐 Sign in")

            with st.form("login_form"):
                email = st.text_input("Email Address")
                password = st.text_input("Password", type="password")

                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submitted:
                    if not email.strip().lower().endswith("@its.edu.in"):
                        st.error("🛑 Access Denied: This portal is strictly restricted to @its.edu.in accounts only.")
                    elif email and password:
                        user = authenticate_user(email, password)
                        if user:
                            new_token = str(uuid.uuid4())
                            register_new_session(user['id'], new_token)

                            st.session_state.logged_in = True
                            st.session_state.user_id = user['id']
                            st.session_state.user_name = user['name']
                            st.session_state.user_role = user['role']
                            st.session_state.session_token = new_token

                            controller.set('smartcampus_user', {
                                'id': user['id'],
                                'role': user['role'],
                                'name': user['name'],
                                'session_token': new_token
                            }, max_age=2592000)

                            with st.spinner("Authenticating..."):
                                time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    else:
                        st.warning("Please fill in all fields.")

        with st.expander("Forgot your password?"):
            st.warning("🔒 **Security Policy:** Password resets are handled by Administration.")
            st.write("Please visit the **Placement Cell** or contact your Course Coordinator.")
            st.caption("**Office:** IT Department, UG Campus, ITS Mohan Nagar")

        st.write("")
        if st.button("← Back to Home"):
            st.switch_page(st.session_state.pages['home'])

    render_footer()


# ==========================================
# PAGE 3: THE REGISTRATION PAGE
# ==========================================
def show_register():
    render_watermark()
    render_top_left_logo()

    registration_open = get_registration_status()
    if not registration_open:
        st.error("Registrations have been closed by the administration.")
        return

    st.toast("Ready to create your profile ✨", icon="📝")

    img_col, form_col = st.columns([1, 1.2], gap="large")

    with img_col:
        st.title("Join SmartCampus")
        st.write("Create your account to start matching your skills with top tech companies.")
        st.write("")
        # Load the Register Animation
        lottie_register = load_lottieurl("https://assets2.lottiefiles.com/packages/lf20_tfb3estd.json")
        if lottie_register:
            st_lottie(lottie_register, height=250, key="reg_anim")

        st.divider()

        st.write("📊 **Explore Your Future**")
        db_stats = get_platform_stats()

        analytics_1, analytics_2 = st.columns(2)
        analytics_1.metric(label="Open Openings", value=db_stats["active_drives"])
        analytics_2.metric(label="Hiring Partners", value=db_stats["total_companies"])
        st.write("")

        st.caption("✨ These companies are looking for your skills today.")
        st.divider()

        st.info("💡 **Security Notice:** You must use your official @its.edu.in college email address to register.")

    with form_col:
        with st.container(border=True):
            st.subheader("📝 Create Account")

            with st.form("register_form"):
                reg_name = st.text_input("Full Name")
                reg_email = st.text_input("Email Address")
                reg_password = st.text_input("Password", type="password")
                reg_role = st.selectbox("I am a:", ["student", "coordinator"])

                submitted = st.form_submit_button("Register Account", use_container_width=True, type="primary")

                if submitted:
                    # 1. ALWAYS Check Domain First
                    if not reg_email.strip().lower().endswith("@its.edu.in"):
                        st.error(
                            "🛑 Registration Blocked: You must use a valid @its.edu.in email address to create an account.")

                    # 2. CHECK THE GATEKEEPER TOGGLE & WHITELIST
                    elif reg_role == "student" and get_whitelist_status() and not is_whitelisted(reg_email):
                        st.error(
                            "🛑 Access Denied: The platform is currently in strict Invite-Only mode. Your email has not been pre-approved by the Placement Cell.")

                    # 3. Proceed to Database Insertion
                    elif reg_name and reg_email and reg_password:
                        success, message = register_user(reg_name, reg_email, reg_password, reg_role)
                        if success:
                            st.balloons()
                            st.success(message + " The coordinators will review your account soon.")
                            time.sleep(2)
                            st.switch_page(st.session_state.pages['login'])
                        else:
                            st.error(message)
                    else:
                        st.warning("Please fill out all fields.")

        st.write("")
        if st.button("← Back to Home"):
            st.switch_page(st.session_state.pages['home'])

    render_footer()