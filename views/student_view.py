import streamlit as st
import json
import pandas as pd
import time
import datetime
import requests  # Required for the Cloud API calls
from database import get_connection, delete_student_resume, apply_to_job, check_if_applied, get_student_applications, \
    update_student_links, get_student_links, get_all_announcements, get_unread_notifications, mark_notifications_read, \
    get_hall_of_fame, create_ticket, get_student_tickets, save_interview_experience, get_all_interview_experiences, \
    check_password_reset_flag, force_update_password, get_engine_status, is_session_valid, destroy_session
from matcher import calculate_match_score
import experimental_llm_engine
import custom_ner_engine
from nlp_engine import extract_text_from_pdf, extract_skills, extract_skills_basic, grade_resume
import os
from dotenv import load_dotenv

# Securely load environment variables from the .env file
load_dotenv()

# ==========================================
# HELPER: TOP-RIGHT WATERMARK
# ==========================================
def render_watermark():
    """Pushes a sleek version tag to the absolute top right corner"""
    spacer, version_col = st.columns([5, 1])
    with version_col:
        st.caption("⚙️ **v1.1.0-Beta** *(Genesis)*")


def save_student_profile(user_id, text, skills, pdf_bytes):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    skills_json = json.dumps(skills)
    try:
        cursor.execute("SELECT user_id FROM student_profiles WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE student_profiles SET extracted_skills = %s, resume_pdf = %s WHERE user_id = %s",
                           (skills_json, pdf_bytes, user_id))
        else:
            cursor.execute("INSERT INTO student_profiles (user_id, extracted_skills, resume_pdf) VALUES (%s, %s, %s)",
                           (user_id, skills_json, pdf_bytes))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving profile: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_student_skills(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT extracted_skills FROM student_profiles WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result['extracted_skills']: return json.loads(result['extracted_skills'])
    return []


def get_all_jobs():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    jobs = cursor.fetchall()
    conn.close()
    return jobs


def render_student_dashboard(controller):
    render_watermark()

    st.title("🎓 Student Dashboard")
    st.write(f"Welcome back, **{st.session_state.user_name}**!")

    st.divider()

    # --- 🛑 THE CONCURRENT SESSION INTERCEPTOR (TRIPWIRE) 🛑 ---
    if not is_session_valid(st.session_state.get('session_token')):
        st.error("🚨 Session Expired! You have been logged out because you signed in on too many other devices.")
        time.sleep(3)

        # Clean up the cookies and state to PREVENT the loop
        try:
            controller.remove('smartcampus_user')
        except:
            pass
        st.session_state.clear()
        st.rerun()
    # --------------------------------------------------------

    if check_password_reset_flag(st.session_state.user_id):
        st.subheader("🔒 Mandatory Security Update")
        st.warning(
            "You are logging in with a temporary Placement Cell PIN. To secure your account and access the dashboard, you must set a personalized password right now.")

        with st.container(border=True):
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")

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
        st.stop()

    notifications = get_unread_notifications(st.session_state.user_id)
    if notifications:
        for notif in notifications:
            if "PLACED" in notif['message']:
                st.balloons()
            st.toast(notif['message'], icon="🔔")
            st.info(notif['message'])
        mark_notifications_read(st.session_state.user_id)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📄 Profile", "💼 Jobs", "📊 Track Apps", "🏆 Hall of Fame", "🎫 HelpDesk", "💬 Experiences"])

    with tab1:
        prof_col1, prof_col2 = st.columns([2, 1])
        with prof_col1:
            st.subheader("Professional Links")
            with st.container(border=True):
                current_li, current_gh = get_student_links(st.session_state.user_id)
                new_li = st.text_input("🔗 LinkedIn URL", value=current_li if current_li else "",
                                       placeholder="https://linkedin.com/in/yourprofile")
                new_gh = st.text_input("💻 GitHub URL", value=current_gh if current_gh else "",
                                       placeholder="https://github.com/yourusername")

                if st.button("Save Links", type="secondary"):
                    if update_student_links(st.session_state.user_id, new_li, new_gh):
                        st.success("Links saved successfully!")
                        time.sleep(1)
                        st.rerun()

            st.divider()
            st.subheader("Update Resume")

            # --- 4-OPTION DYNAMIC SELECTOR ---
            available_engines = ["Deterministic Lexical Matcher (Exact Match)"]

            if get_engine_status('ml_engine'):
                available_engines.append("Contextual NER Engine (Machine Learning) ~underprocess")

            if get_engine_status('llm_engine'):
                available_engines.append("Generative LLM Parser (Gemma 2B) ~For tech resume only")

            if get_engine_status('api_engine'):
                available_engines.append("Cloud API Parser (Free Public Endpoint)")

            engine_choice = st.radio(
                "🧠 Select Processing Engine:",
                available_engines,
                help="Mega-Dictionary is always available. Other AI models may be disabled by the Admin to save server resources."
            )
            # -------------------------------------------

            uploaded_file = st.file_uploader("Drag and drop your resume (PDF only)", type=["pdf"])

            if uploaded_file is not None:
                if st.button("Extract Skills & Save", type="primary", use_container_width=True):
                    resume_text = extract_text_from_pdf(uploaded_file)
                    pdf_bytes = uploaded_file.getvalue()
                    extracted_skills = []

                    if engine_choice == "Deterministic Lexical Matcher (Exact Match)":
                        with st.spinner("🔍 Scanning against known skills..."):
                            extracted_skills = extract_skills_basic(resume_text)

                    elif engine_choice == "Contextual NER Engine (Machine Learning) ~underprocess":
                        with st.spinner("🧠 Running text through Custom Trained Neural Network..."):
                            extracted_skills = custom_ner_engine.extract_skills(resume_text)

                    elif engine_choice == "Generative LLM Parser (Gemma 2B) ~For tech resume only":
                        with st.spinner("🤖 Analyzing with Local AI... (This may take a few seconds)"):
                            extracted_skills = experimental_llm_engine.extract_skills(resume_text)

                    elif engine_choice == "Cloud API Parser (Free Public Endpoint)":
                        with st.spinner("🌐 Routing to Blazing Fast Groq API (Llama 3.1)..."):
                            try:
                                # SECURITY UPDATE: Fetching key dynamically from .env
                                GROQ_API_KEY = os.getenv("GROQ_API_KEY")

                                if not GROQ_API_KEY:
                                    extracted_skills = ["Error: Groq API Key not found. Please add GROQ_API_KEY to your .env file."]
                                elif not resume_text.strip():
                                    extracted_skills = [
                                        "Error: Could not read any text from the PDF. Is it an image-based PDF?"]
                                else:
                                    headers = {
                                        "Authorization": f"Bearer {GROQ_API_KEY}",
                                        "Content-Type": "application/json"
                                    }
                                    prompt = f"Extract a comma-separated list of technical and professional skills from this text. Return ONLY the skills separated by commas, no introductory text, no bullet points. Text: {resume_text[:2000]}"
                                    payload = {
                                        "model": "llama-3.1-8b-instant",
                                        "messages": [{"role": "user", "content": prompt}],
                                        "temperature": 0.1
                                    }

                                    response = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                                             headers=headers, json=payload)

                                    if response.status_code == 200:
                                        raw_skills = response.json()['choices'][0]['message']['content']
                                        extracted_skills = [s.strip().title() for s in raw_skills.split(',') if
                                                            s.strip()]
                                    else:
                                        try:
                                            error_detail = response.json().get('error', {}).get('message',
                                                                                                response.text)
                                        except:
                                            error_detail = response.text
                                        extracted_skills = [f"API Error {response.status_code}: {error_detail}"]

                            except Exception as e:
                                extracted_skills = [f"Error: API Unreachable - {e}"]
                    # --------------------------------------

                    if extracted_skills and not extracted_skills[0].startswith("Error"):
                        if save_student_profile(st.session_state.user_id, resume_text, extracted_skills, pdf_bytes):
                            st.success("✅ Extraction Complete! Resume processed! Check your Recommended Jobs.")
                            st.divider()

                            score, feedback = grade_resume(resume_text)

                            st.write(f"### 🤖 AI Resume Score: {score}/100")
                            st.progress(score / 100)

                            for item in feedback:
                                if item['type'] == 'warning':
                                    st.warning(f"**{item['title']}**\n\n{item['desc']}")
                                elif item['type'] == 'info':
                                    st.info(f"**{item['title']}**\n\n{item['desc']}")
                                else:
                                    st.success(f"**{item['title']}**\n\n{item['desc']}")
                        else:
                            st.error("Database error while saving resume.")
                    else:
                        st.error(
                            f"Extraction failed: {extracted_skills[0] if extracted_skills else 'No skills found.'}")

        with prof_col2:
            st.subheader("💡 Your Extracted Skills")
            current_skills = get_student_skills(st.session_state.user_id)
            if current_skills:
                # --- THE DEDUPLICATION FIX ---
                unique_skills = list(dict.fromkeys([s.strip().title() for s in current_skills]))

                for i, skill in enumerate(unique_skills):
                    st.button(skill, key=f"skill_{i}_{skill}", disabled=True, use_container_width=True)
                # -----------------------------

                st.divider()
                if st.button("🗑️ Delete My Resume Data", type="primary", use_container_width=True):
                    if delete_student_resume(st.session_state.user_id):
                        st.success("Resume data deleted! Please upload a new one.")
                        st.rerun()
            else:
                st.info("Upload a resume to extract your skills.")

    with tab2:
        st.subheader("Placement Drives & AI Match Scores")

        announcements = get_all_announcements()
        if announcements:
            with st.expander("📣 **Latest Announcements from Placement Cell**", expanded=True):
                for ann in announcements: st.info(f"**{ann['coordinator_name']}** ({ann['date']}): {ann['message']}")
            st.divider()

        student_skills = get_student_skills(st.session_state.user_id)
        jobs = get_all_jobs()

        if not student_skills:
            st.warning(
                "⚠️ Please upload your resume in the 'My Profile' tab first so we can calculate your match scores!")
        elif not jobs:
            st.info("No placement drives have been posted yet. Check back later!")
        else:
            processed_jobs = []
            for job in jobs:
                try:
                    job_skills = json.loads(job['required_skills']) if job['required_skills'] else []
                except:
                    job_skills = [s.strip() for s in job['required_skills'].split(",")] if job[
                        'required_skills'] else []

                match_score, missing_skills = calculate_match_score(student_skills, job_skills)
                job['match_score'] = match_score
                job['missing_skills'] = missing_skills
                job['job_skills_list'] = job_skills
                processed_jobs.append(job)

            search_col, filter_col, sort_col = st.columns([2, 1, 1])
            with search_col:
                search_term = st.text_input("🔍 Search drives, companies, or skills...", key="stu_search")
            with filter_col:
                drive_filter = st.selectbox("Drive Status", ["All Drives", "Active / Upcoming Only"], key="stu_filter")
            with sort_col:
                sort_order = st.selectbox("Sort By",
                                          ["Best Match First", "Highest Salary (CTC)", "Drive Date (Earliest)",
                                           "Company (A-Z)"], key="stu_sort")

            st.divider()

            if search_term:
                term = search_term.lower()
                processed_jobs = [j for j in processed_jobs if
                                  term in j['title'].lower() or term in j['company'].lower() or (
                                          j['required_skills'] and term in j['required_skills'].lower())]

            today = datetime.date.today()
            if drive_filter == "Active / Upcoming Only":
                processed_jobs = [j for j in processed_jobs if j['drive_date'] and j['drive_date'] >= today]

            if sort_order == "Best Match First":
                processed_jobs.sort(key=lambda x: x['match_score'], reverse=True)
            elif sort_order == "Highest Salary (CTC)":
                processed_jobs.sort(key=lambda x: float(x.get('ctc') or 0), reverse=True)
            elif sort_order == "Drive Date (Earliest)":
                processed_jobs.sort(key=lambda x: x['drive_date'] if x['drive_date'] else datetime.date.max)
            elif sort_order == "Company (A-Z)":
                processed_jobs.sort(key=lambda x: x['company'].lower())

            if not processed_jobs:
                st.warning("No placement drives match your current search and filter criteria.")
            else:
                for job in processed_jobs:
                    with st.container(border=True):
                        title_prefix = "🔓 [OPEN] " if job.get('bypass_restriction') else ""
                        st.write(f"### {title_prefix}{job['title']} at {job['company']}")

                        jcol1, jcol2, jcol3 = st.columns(3)
                        with jcol1:
                            st.write(f"📅 **Drive Date:** {job['drive_date']}")
                            st.write(
                                f"⏳ **Deadline:** {job['application_deadline'] if job.get('application_deadline') else 'Not specified'}")
                        with jcol2:
                            if job.get('bypass_restriction'):
                                st.write("🔓 **Policy:** Open for All (Score Bypassed)")
                            else:
                                st.write(f"🔒 **Min. Score Required:** {job.get('min_match_score', 0)}%")
                        with jcol3:
                            st.write(f"💰 **CTC Offered:** {job.get('ctc', 0)} LPA")

                        st.write(f"{job['description']}")
                        st.write(f"**Your AI Match Score: {job['match_score']}%**")
                        st.progress(job['match_score'] / 100)

                        with st.expander("📊 See AI Match Breakdown"):
                            xai_col1, xai_col2 = st.columns(2)
                            lower_student = [s.lower().strip() for s in student_skills]
                            matched = [s.title() for s in job['job_skills_list'] if s.lower().strip() in lower_student]

                            with xai_col1:
                                st.markdown(f"**✅ Matched Skills ({len(matched)})**")
                                if matched:
                                    for m in matched: st.write(f"- {m}")
                                else:
                                    st.caption("No matching skills found.")

                            with xai_col2:
                                st.markdown(f"**❌ Missing Skills ({len(job['missing_skills'])})**")
                                if job['missing_skills']:
                                    for m in job['missing_skills']: st.write(f"- {m.title()}")
                                else:
                                    st.caption("You have all required skills!")

                        st.divider()

                        deadline = job.get('application_deadline')
                        min_score = job.get('min_match_score', 0)
                        is_bypassed = bool(job.get('bypass_restriction'))
                        is_closed = False

                        if deadline:
                            if isinstance(deadline, datetime.datetime):
                                is_closed = deadline.date() < today
                            else:
                                is_closed = deadline < today

                        if check_if_applied(st.session_state.user_id, job['id']):
                            st.button("✅ Application Submitted", key=f"applied_{job['id']}", disabled=True,
                                      use_container_width=True)
                        elif is_closed:
                            st.button("🚫 Applications Closed", key=f"closed_{job['id']}", disabled=True,
                                      use_container_width=True)
                        elif not is_bypassed and job['match_score'] < min_score:
                            st.button(f"🔒 Score too low to apply (Requires {min_score}%)", key=f"blocked_{job['id']}",
                                      disabled=True, use_container_width=True)
                        else:
                            btn_text = "🔓 Apply Now (Open Drive)" if is_bypassed and job[
                                'match_score'] < min_score else "🚀 Apply Now"

                            if st.button(btn_text, key=f"apply_{job['id']}", type="primary", use_container_width=True):
                                if apply_to_job(st.session_state.user_id, job['id'], job['match_score']):
                                    st.success("Application successfully submitted to the Placement Cell!")
                                    time.sleep(1)
                                    st.rerun()

    with tab3:
        st.subheader("My Application History")
        my_apps = get_student_applications(st.session_state.user_id)

        if not my_apps:
            st.info("You haven't applied to any placement drives yet.")
        else:
            for app in my_apps:
                with st.container(border=True):
                    status = app['status']

                    if status == "Pending":
                        badge = "🟡 **PENDING**"
                    elif status == "Under Review":
                        badge = "🔵 **UNDER REVIEW**"
                    elif status == "Shortlisted":
                        badge = "🟢 **SHORTLISTED 🎉**"
                    elif status == "Placed":
                        badge = "🏆 **PLACED! 🎓**"
                    elif status == "Rejected":
                        badge = "🔴 **REJECTED**"
                    else:
                        badge = f"⚪ **{status.upper()}**"

                    app_col1, app_col2 = st.columns([3, 1])
                    with app_col1:
                        st.write(f"### {app['title']} at {app['company']}")
                        st.write(f"📅 **Applied On:** {app['applied_at']}")
                        st.caption(f"Your AI Match Score for this role was {app['match_score']}%")

                        if status == 'Shortlisted' and app.get('interview_date'):
                            st.success(
                                f"**📅 Interview Scheduled:** {app['interview_date']} \n\n **📍 Location:** {app['interview_room']}")
                            if app.get('interview_message'): st.info(
                                f"**📝 Instructions from Coordinator:**\n\n{app['interview_message']}")
                        elif status == 'Placed':
                            st.success(
                                "🎉 **OFFER RECEIVED!** Please check your registered email or visit the Placement Cell to collect your official offer letter.")

                        if status in ['Placed', 'Rejected']:
                            st.divider()
                            if app.get('student_feedback'):
                                st.info(f"**Your Shared Experience:**\n\n*{app['student_feedback']}*")
                            else:
                                with st.expander("🗣️ Help future students! Share your interview experience."):
                                    feedback_text = st.text_area("What questions were asked? Any tips?",
                                                                 key=f"feed_{app['app_id']}")
                                    if st.button("Share Experience to Community", key=f"btn_feed_{app['app_id']}",
                                                 type="primary"):
                                        if save_interview_experience(app['app_id'], feedback_text):
                                            st.success("Thank you for sharing your experience!")
                                            time.sleep(1)
                                            st.rerun()

                    with app_col2:
                        st.write("")
                        st.subheader(badge)

    with tab4:
        st.subheader("🏆 Placement Hall of Fame")
        hall_of_fame = get_hall_of_fame()

        if hall_of_fame:
            st.write("### 🌟 Latest Success Stories")
            recent_winners = hall_of_fame[:3]
            cols = st.columns(len(recent_winners))

            for i, entry in enumerate(recent_winners):
                with cols[i]:
                    st.success(
                        f"🎓 **{entry['name']}**\n\n🏢 **Company:** {entry['company']}\n\n💼 **Role:** {entry['title']}\n\n🎉 **Status:** PLACED!")

            st.divider()

            if len(hall_of_fame) > 3:
                st.write("#### 🎓 Alumni Wall of Fame")
                for entry in hall_of_fame[3:]:
                    st.info(
                        f"**{entry['name']}** secured a position as **{entry['title']}** at **🏢 {entry['company']}**!")
        else:
            st.info("The Placement Hall of Fame is currently empty. Our next success story could be yours!")

    with tab5:
        st.subheader("🎫 Placement HelpDesk")
        st.write("Need help or have a query? Raise a ticket and the Placement Cell will get back to you directly.")

        with st.container(border=True):
            category = st.selectbox("Issue Category",
                                    ["Interview Reschedule Request", "Profile Correction", "Drive Query",
                                     "Technical Issue", "Other"])
            message = st.text_area("Describe your issue...")

            if st.button("Submit Ticket", type="primary"):
                if message:
                    if create_ticket(st.session_state.user_id, category, message):
                        st.success("Ticket raised successfully! A coordinator will review it shortly.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Failed to submit ticket.")
                else:
                    st.warning("Please describe your issue before submitting.")

        st.divider()
        st.subheader("My Support Tickets")
        tickets = get_student_tickets(st.session_state.user_id)

        if tickets:
            for t in tickets:
                icon = "🟢" if t['status'] == 'Resolved' else "🔴"
                state_text = "RESOLVED" if t['status'] == 'Resolved' else "OPEN"

                with st.expander(f"{icon} [{state_text}] {t['category']} - {t['created_at'].strftime('%b %d, %Y')}"):
                    st.write(f"**Your Message:**\n{t['message']}")
                    st.divider()
                    if t['reply']:
                        st.info(f"**Coordinator Reply:**\n{t['reply']}")
                    else:
                        st.caption("⏳ Waiting for coordinator response...")
        else:
            st.info("You haven't raised any tickets yet.")

    with tab6:
        st.subheader("💬 Campus Interview Experiences")
        st.caption(
            "Learn from your seniors and peers! Read real interview experiences and tips shared by students who have already faced the panel.")

        experiences = get_all_interview_experiences()
        if experiences:
            for exp in experiences:
                with st.container(border=True):
                    st.markdown(f"#### 🏢 {exp['company']} - {exp['title']}")
                    st.write(f"👤 **Student:** {exp['name']}")

                    if exp['status'] == 'Placed':
                        st.success(f"**Outcome:** 🏆 Placed! | **Shared On:** {exp['applied_at'].strftime('%b %d, %Y')}")
                    else:
                        st.warning(
                            f"**Outcome:** 🔴 Not Selected | **Shared On:** {exp['applied_at'].strftime('%b %d, %Y')}")

                    st.info(f"**Interview Feedback & Tips:**\n\n*{exp['student_feedback']}*")
        else:
            st.info(
                "No interview experiences have been shared yet. As students complete interviews, their tips will appear here!")