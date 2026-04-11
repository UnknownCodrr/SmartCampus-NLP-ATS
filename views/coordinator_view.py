import streamlit as st
import time
import datetime
import json
import pandas as pd
import plotly.express as px
from database import create_job, get_all_jobs, delete_job, update_job, verify_password, get_job_applicants, \
    update_application_status, get_all_analytics, create_announcement, get_all_announcements, \
    get_all_registered_students, \
    get_applicant_count, get_registration_status, set_registration_status, create_notification, \
    update_interview_details, notify_shortlisted_students, get_campus_skills_data, get_hall_of_fame, \
    get_all_tickets, resolve_ticket, get_student_skills_by_id, update_student_skills_manual, get_student_resume_pdf, \
    get_all_interview_experiences, get_placed_report_data, bulk_register_students, \
    check_password_reset_flag, force_update_password, is_session_valid, destroy_session, \
    add_to_whitelist, get_whitelist_status, set_whitelist_status, delete_announcement
import re


# ==========================================
# HELPER: TOP-RIGHT WATERMARK
# ==========================================
def render_watermark():
    """Pushes a sleek version tag to the absolute top right corner"""
    spacer, version_col = st.columns([5, 1])
    with version_col:
        st.caption("⚙️ **v1.0.0-Beta** *(Genesis)*")


def render_coordinator_dashboard(controller):
    render_watermark()  # <--- Added the version watermark here!

    # --- NUKED THE DUPLICATE LOGOUT BUTTON ---
    st.title("👨‍💼 Placement Dashboard")
    st.write(f"Welcome back, **{st.session_state.user_name}**!")

    st.divider()

    # --- 🛑 THE CONCURRENT SESSION INTERCEPTOR (TRIPWIRE) 🛑 ---
    if not is_session_valid(st.session_state.get('session_token')):
        st.error("🚨 Session Expired! You have been logged out because you signed in on too many other devices.")
        time.sleep(3)

        try:
            controller.remove('smartcampus_user')
        except:
            pass
        st.session_state.clear()
        st.rerun()
    # --------------------------------------------------------

    # --- 🛑 THE SECURITY INTERCEPTOR (FOR COORDINATORS) 🛑 ---
    if check_password_reset_flag(st.session_state.user_id):
        st.subheader("🔒 Mandatory Security Update")
        st.warning(
            "Your password was reset by a System Admin or you are logging in with a temporary PIN. To secure your coordinator account, you must set a personalized password right now.")

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
        # ----------------------------------------

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        ["📢 Drives", "➕ Post Drive", "📊 Analytics", "📣 Broadcast", "🧑‍🎓 Directory", "🏆 Hall of Fame", "🎫 HelpDesk",
         "💬 Experiences"])

    with tab1:
        st.subheader("All Campus Placement Drives")

        search_col, sort_col = st.columns([3, 1])
        with search_col:
            search_term = st.text_input("🔍 Search drives by company or title...", key="coord_search")
        with sort_col:
            sort_order = st.selectbox("Sort By", ["Newest First", "Oldest First", "Company (A-Z)"], key="coord_sort")

        st.divider()

        jobs = get_all_jobs()

        if jobs:
            if search_term:
                search_lower = search_term.lower()
                jobs = [job for job in jobs if
                        search_lower in job['title'].lower() or search_lower in job['company'].lower()]

            if sort_order == "Oldest First":
                jobs = jobs[::-1]
            elif sort_order == "Company (A-Z)":
                jobs = sorted(jobs, key=lambda x: x['company'].lower())

            if not jobs:
                st.warning("No drives match your search criteria.")
            else:
                for job in jobs:
                    with st.container(border=True):
                        title_prefix = "🔓 [OPEN] " if job.get('bypass_restriction') else "🏢 "
                        st.subheader(f"{title_prefix}{job['company']} - {job['title']}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"📅 **Drive Date:** {job['drive_date']}")
                            st.write(
                                f"⏳ **Deadline:** {job['application_deadline'] if job.get('application_deadline') else 'Not specified'}")
                        with col2:
                            if job.get('bypass_restriction'):
                                st.write("🔓 **Policy:** Open for All (Score Bypassed)")
                            else:
                                st.write(f"🔒 **Min. Score:** {job.get('min_match_score', 0)}%")
                            st.write(f"🎯 **Skills:** `{job['required_skills']}`")
                        with col3:
                            st.write(f"💰 **CTC Offered:** {job.get('ctc', 0)} LPA")

                        st.write(f"📝 **Description:** {job['description']}")
                        st.divider()

                        with st.expander("📅 Manage Interview Schedule for this Drive"):
                            st.info(
                                "💡 Set the interview details here. It will automatically apply to all students you mark as 'Shortlisted'.")

                            int_col1, int_col2 = st.columns(2)
                            with int_col1:
                                i_date = st.date_input("Interview Date", key=f"jdate_{job['id']}")
                                i_time = st.time_input("Interview Time", key=f"jtime_{job['id']}")
                            with int_col2:
                                i_room = st.text_input("Room No. / Meet Link", value=job.get('interview_room') or "",
                                                       key=f"jroom_{job['id']}")

                            i_msg = st.text_area("Additional Instructions (Optional)",
                                                 value=job.get('interview_message') or "",
                                                 placeholder="e.g., Bring 2 hard copies of your resume...",
                                                 key=f"jmsg_{job['id']}")

                            if st.button("Save & Notify Shortlisted Students", type="primary",
                                         key=f"jsave_{job['id']}"):
                                dt_str = f"{i_date.strftime('%B %d, %Y')} at {i_time.strftime('%I:%M %p')}"
                                if update_interview_details(job['id'], dt_str, i_room, i_msg):
                                    notify_msg = f"📅 Interview Update: {job['company']} has scheduled your interview for {dt_str} in {i_room}."
                                    notify_shortlisted_students(job['id'], notify_msg)
                                    st.success("Saved! All shortlisted students have been notified.")
                                    time.sleep(1)
                                    st.rerun()

                            if job.get('interview_date'):
                                st.success(
                                    f"**Current Schedule:** {job['interview_date']} | **Location:** {job['interview_room']}")
                                if job.get('interview_message'):
                                    st.caption(f"**Instructions:** {job['interview_message']}")

                        act_col1, act_col2, act_col3 = st.columns(3)
                        with act_col1:
                            app_count = get_applicant_count(job['id'])
                            view_apps = st.toggle(f"👥 View Applicants ({app_count})", key=f"view_toggle_{job['id']}")
                        with act_col2:
                            edit_mode = st.toggle("✏️ Edit Drive", key=f"edit_toggle_{job['id']}")
                        with act_col3:
                            delete_mode = st.toggle("🗑️ Delete Drive", key=f"del_toggle_{job['id']}")

                        if view_apps:
                            st.markdown("#### 📄 Student Applications")
                            applicants = get_job_applicants(job['id'])
                            if applicants:
                                df_export = pd.DataFrame(applicants)
                                cols_wanted = ['name', 'email', 'match_score', 'status', 'applied_at', 'linkedin_url',
                                               'github_url', 'extracted_skills']
                                cols_present = [c for c in cols_wanted if c in df_export.columns]
                                df_export = df_export[cols_present]
                                csv = df_export.to_csv(index=False).encode('utf-8')
                                st.download_button(label="📥 Download Applicant Data (CSV)", data=csv,
                                                   file_name=f"{job['company']}_{job['title']}_applicants.csv",
                                                   mime="text/csv", type="secondary", key=f"dl_csv_{job['id']}")

                                st.markdown("##### ⚡ AI Automation")
                                min_req_score = float(job.get('min_match_score', 0))

                                if st.button(f"⚡ Auto-Shortlist Candidates (Score ≥ {int(min_req_score)}%)",
                                             type="primary",
                                             key=f"auto_{job['id']}", use_container_width=True):
                                    shortlisted_count = 0
                                    with st.spinner("Analyzing scores and updating statuses..."):
                                        for app in applicants:
                                            app_score = float(app['match_score']) if app['match_score'] else 0.0

                                            if app_score >= min_req_score and app['status'] in ["Pending",
                                                                                                "Under Review"]:
                                                if update_application_status(app['app_id'], "Shortlisted"):
                                                    msg = f"🌟 Great news! Your application for {job['title']} at {job['company']} has been automatically **Shortlisted** due to your high AI match score!"
                                                    create_notification(app['student_id'], msg)
                                                    shortlisted_count += 1

                                    if shortlisted_count > 0:
                                        st.success(f"Successfully auto-shortlisted {shortlisted_count} students!")
                                    else:
                                        st.info("No pending candidates met the minimum score criteria.")
                                    time.sleep(1.5)
                                    st.rerun()
                                st.divider()

                                for app in applicants:
                                    with st.container(border=True):
                                        st.write(f"**Student:** {app['name']} ({app['email']})")

                                        link_col1, link_col2 = st.columns(2)
                                        with link_col1:
                                            if app.get('linkedin_url'): st.markdown(
                                                f"🔗 [LinkedIn Profile]({app['linkedin_url']})")
                                        with link_col2:
                                            if app.get('github_url'): st.markdown(
                                                f"💻 [GitHub Portfolio]({app['github_url']})")

                                        resume_bytes = get_student_resume_pdf(app['student_id'])
                                        if resume_bytes:
                                            st.download_button(label="📥 Download Original Resume PDF",
                                                               data=resume_bytes,
                                                               file_name=f"{app['name'].replace(' ', '_')}_Resume.pdf",
                                                               mime="application/pdf", key=f"dl_pdf_{app['app_id']}")

                                        st.write(f"**AI Match Score:** {app['match_score']}%")

                                        try:
                                            skills_list = json.loads(app['extracted_skills'])
                                            st.write(f"**Extracted Resume Skills:** `{', '.join(skills_list)}`")
                                        except:
                                            st.write(f"**Extracted Resume Skills:** `{app['extracted_skills']}`")

                                        st.caption(f"Applied on: {app['applied_at']}")
                                        st.divider()

                                        status_col, btn_col = st.columns([3, 1])
                                        states = ["Pending", "Under Review", "Shortlisted", "Placed", "Rejected"]
                                        current_index = states.index(app['status']) if app['status'] in states else 0

                                        with status_col:
                                            new_status = st.selectbox("Application Status", states, index=current_index,
                                                                      key=f"status_{app['app_id']}_{app['status']}")
                                        with btn_col:
                                            st.write("")
                                            st.write("")
                                            if st.button("Save Status", key=f"save_stat_{app['app_id']}",
                                                         use_container_width=True):
                                                if update_application_status(app['app_id'], new_status):
                                                    if new_status == "Placed":
                                                        msg = f"🏆 MASSIVE CONGRATULATIONS! You have been PLACED at {job['company']} for the role of {job['title']}! The Placement Cell will contact you with offer details."
                                                    else:
                                                        msg = f"🔔 Update: Your application for {job['title']} at {job['company']} has been marked as **{new_status}**."

                                                    create_notification(app['student_id'], msg)
                                                    st.session_state[f"status_{app['app_id']}"] = new_status
                                                    st.success("Updated!")
                                                    time.sleep(0.5)
                                                    st.rerun()
                            else:
                                st.info("No students have applied for this drive yet.")

                        if edit_mode:
                            with st.container(border=True):
                                st.caption("Update Drive Details")
                                new_title = st.text_input("Job Title", value=job['title'], key=f"title_{job['id']}")
                                new_company = st.text_input("Company", value=job['company'], key=f"comp_{job['id']}")
                                new_skills = st.text_input("Required Skills", value=job['required_skills'],
                                                           key=f"skills_{job['id']}")
                                d_col1, d_col2 = st.columns(2)
                                with d_col1:
                                    new_drive_date = st.date_input("Drive Date", value=job['drive_date'] if job[
                                        'drive_date'] else datetime.date.today(), key=f"ddate_{job['id']}")
                                with d_col2:
                                    new_deadline = st.date_input("Application Deadline",
                                                                 value=job['application_deadline'] if job[
                                                                     'application_deadline'] else datetime.date.today(),
                                                                 key=f"ddead_{job['id']}")

                                c_col1, c_col2, c_col3 = st.columns([1, 1, 1])
                                with c_col1:
                                    new_min_score = st.slider("Min Match Score", 0, 100,
                                                              int(job.get('min_match_score', 0)), step=5,
                                                              key=f"score_{job['id']}")
                                with c_col2:
                                    new_ctc = st.number_input("CTC Offered (LPA)", value=float(job.get('ctc', 0)),
                                                              step=0.5, format="%.2f", key=f"ctc_{job['id']}")
                                with c_col3:
                                    st.write("**Policy**")
                                    new_bypass = st.toggle("🔓 Bypass Restriction",
                                                           value=bool(job.get('bypass_restriction')),
                                                           key=f"bypass_edit_{job['id']}")

                                new_desc = st.text_area("Description", value=job['description'],
                                                        key=f"desc_{job['id']}")
                                st.divider()
                                edit_pw = st.text_input("🔒 Enter your password to save changes:", type="password",
                                                        key=f"edit_pw_{job['id']}")
                                if st.button("💾 Verify & Save Changes", type="primary", key=f"save_{job['id']}"):
                                    if verify_password(st.session_state.user_id, edit_pw):
                                        if update_job(job['id'], new_title, new_company, new_skills, new_desc,
                                                      new_drive_date, new_deadline, new_min_score, new_ctc, new_bypass):
                                            st.success("Drive securely updated!")
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error("Incorrect password.")

                        if delete_mode:
                            with st.container(border=True):
                                st.error(
                                    "⚠️ Danger Zone: Deleting this drive will also delete all student applications tied to it.")
                                del_pw = st.text_input("🔒 Enter your password to permanently delete:", type="password",
                                                       key=f"del_pw_{job['id']}")
                                if st.button("🚨 Verify & Delete Drive", type="primary", key=f"conf_del_{job['id']}"):
                                    if verify_password(st.session_state.user_id, del_pw):
                                        if delete_job(job['id']):
                                            st.success("Drive securely deleted!")
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error("Incorrect password.")
        else:
            st.info("No placement drives have been posted to the platform yet.")

    with tab2:
        st.subheader("Create a New Placement Drive")
        with st.container(border=True):
            company = st.text_input("Company Name", placeholder="e.g., TCS, Infosys, Wipro")
            title = st.text_input("Job Title", placeholder="e.g., Junior Software Engineer")
            required_skills = st.text_input("Required Skills", placeholder="e.g., Python, MySQL, NLP, React")
            col1, col2 = st.columns(2)
            with col1:
                drive_date = st.date_input("Drive Date (When the event happens)")
            with col2:
                application_deadline = st.date_input("Application Deadline (Last day to apply)")

            st.divider()

            score_col, ctc_col, bypass_col = st.columns([2, 2, 1])
            with score_col:
                min_match_score = st.slider("Minimum Match Score Required (%)", 0, 100, 60, step=5)
            with ctc_col:
                ctc_offered = st.number_input("CTC Offered (in LPA)", min_value=0.0, max_value=100.0, value=0.0,
                                              step=0.5, format="%.2f")
            with bypass_col:
                st.write("**Policy**")
                bypass_mode = st.toggle("🔓 Open for All", value=False,
                                        help="Bypass SmartScore restriction for this drive.")

            if bypass_mode:
                st.warning("⚠️ **Open-Door Policy Enabled:** All students can apply regardless of their AI SmartScore.")

            st.divider()
            description = st.text_area("Job Description / Additional Details")
            if st.button("Post Drive", type="primary", use_container_width=True):
                if company and title and required_skills:
                    success, msg = create_job(st.session_state.user_id, title, company, required_skills, description,
                                              drive_date, application_deadline, min_match_score, ctc_offered,
                                              bypass_mode)
                    if success:
                        st.success("✅ " + msg)
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill in the Company, Title, and Required Skills.")

    with tab3:
        st.subheader("Global Placement Analytics")
        stats = get_all_analytics()
        all_jobs = get_all_jobs()

        if stats and stats['total_jobs'] > 0:
            avg_ctc = sum(float(j.get('ctc') or 0) for j in all_jobs) / len(all_jobs) if all_jobs else 0

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Total Posted Drives", stats['total_jobs'])
            m_col2.metric("Total Applications Received", stats['total_apps'])
            shortlisted = next((item['count'] for item in stats['status_breakdown'] if item['status'] == 'Shortlisted'),
                               0)
            placed = next((item['count'] for item in stats['status_breakdown'] if item['status'] == 'Placed'), 0)
            rate = ((shortlisted + placed) / stats['total_apps'] * 100) if stats['total_apps'] > 0 else 0
            m_col3.metric("Overall Success Rate", f"{rate:.1f}%")
            m_col4.metric("Average Campus CTC", f"₹{avg_ctc:.2f} LPA")
            st.divider()

            st.subheader("📥 Accreditation Reports (NAAC/NBA)")
            report_data = get_placed_report_data()
            if report_data:
                df_report = pd.DataFrame(report_data)
                csv_report = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Dean's Report (Placed Students CSV)",
                    data=csv_report,
                    file_name=f"Deans_Placement_Report_{datetime.date.today()}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.info("No students have been placed yet to generate a report.")

            st.divider()

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.markdown("**Application Status Pipeline**")
                if stats['total_apps'] > 0:
                    df_status = pd.DataFrame(stats['status_breakdown'])
                    color_map = {'Pending': '#fecb4d', 'Under Review': '#0078ff', 'Shortlisted': '#00c853',
                                 'Placed': '#ffd700', 'Rejected': '#ff3d00'}
                    fig_pie = px.pie(df_status, values='count', names='status', color='status',
                                     color_discrete_map=color_map, hole=0.4)
                    fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No student applications yet.")

            with chart_col2:
                st.markdown("**🔥 Campus Skill Heatmap (Top 10)**")
                skills_data = get_campus_skills_data()

                if skills_data:
                    all_skills = []
                    for row in skills_data:
                        try:
                            skills = json.loads(row['extracted_skills'])
                            all_skills.extend([s.title() for s in skills])
                        except:
                            pass

                    if all_skills:
                        skill_counts = {}
                        for s in all_skills: skill_counts[s] = skill_counts.get(s, 0) + 1
                        top_10_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                        df_skills = pd.DataFrame(top_10_skills, columns=['Skill', 'Student Count'])

                        fig_bar = px.bar(df_skills, x='Student Count', y='Skill', orientation='h',
                                         color='Student Count', color_continuous_scale='Blues')
                        fig_bar.update_xaxes(dtick=1)
                        fig_bar.update_coloraxes(colorbar_dtick=1)
                        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'},
                                              margin=dict(t=20, b=20, l=20, r=20))
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info("No valid skills extracted yet.")
                else:
                    st.info("No students have uploaded resumes yet.")
        else:
            st.info("Post some placement drives to unlock the analytics dashboard!")

    with tab4:
        st.subheader("📣 Campus Announcements")
        announcements = get_all_announcements()
        if announcements:
            with st.container(border=True):
                st.markdown("**Recent Announcements History**")
                for ann in announcements:
                    # Create two columns: 10 parts for the message, 1 part for the delete button
                    msg_col, del_col = st.columns([10, 1])

                    with msg_col:
                        st.info(f"**{ann['coordinator_name']}** ({ann['date']}): {ann['message']}")

                    with del_col:
                        st.write("")  # Tiny spacer to align the button
                        # The button uses the announcement ID to know exactly which one to delete
                        if st.button("🗑️", key=f"del_ann_{ann['id']}", help="Delete this announcement"):
                            if delete_announcement(ann['id']):
                                st.success("Deleted!")
                                time.sleep(1)
                                st.rerun()
        else:
            st.info("No announcements have been broadcasted yet.")

        st.divider()

        st.subheader("Broadcast a New Announcement")
        with st.container(border=True):
            announcement_text = st.text_area("Announcement Message",
                                             placeholder="e.g., Please carry 2 hard copies of your resume for tomorrow's TCS drive.",
                                             key="broadcast_msg_box")
            if st.button("📢 Post Announcement", type="primary", key="post_announcement_btn"):
                if announcement_text:
                    if create_announcement(st.session_state.user_id, announcement_text):
                        st.success("Announcement broadcasted to all students successfully!")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.warning("Please enter a message to broadcast.")

    with tab5:
        st.subheader("Registered Students Directory")

        with st.expander("⚙️ System Settings (Admin Controls)", expanded=False):
            current_status = get_registration_status()
            new_status = st.toggle("Allow New Account Registrations", value=current_status)
            if new_status != current_status:
                if set_registration_status(new_status):
                    st.success(f"Registration is now {'OPEN' if new_status else 'CLOSED'}.")
                    time.sleep(1)
                    st.rerun()

        st.divider()

        # --- NEW: THE WHITELIST MANAGER WITH MASTER TOGGLE ---
        with st.expander("🛡️ Manage Registration Whitelist (Invite-Only Access)", expanded=False):

            # The Master Toggle Switch
            current_w_status = get_whitelist_status()
            new_w_status = st.toggle("🔒 Enforce Invite-Only Mode", value=current_w_status,
                                     help="If turned ON, students CANNOT register unless their email is in the database below.")

            if new_w_status != current_w_status:
                if set_whitelist_status(new_w_status):
                    st.success(f"Invite-Only Mode is now {'ACTIVE' if new_w_status else 'DISABLED'}.")
                    time.sleep(1)
                    st.rerun()

            st.divider()

            # The Whitelist Input Area
            st.info("Paste the official @its.edu.in emails of approved students below.")
            whitelist_emails = st.text_area("Approved Student Emails (Comma or newline separated)",
                                            key="whitelist_input")

            if st.button("➕ Add to Approved Whitelist", type="primary"):
                if whitelist_emails.strip():
                    email_list = re.split(r'[,\n\r]+', whitelist_emails)
                    added_count = add_to_whitelist(email_list)
                    st.success(f"✅ Successfully added {added_count} new emails to the secure whitelist!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Please enter at least one email.")
        st.divider()

        with st.expander("📝 Bulk Pre-Register Students (Placement Batch)", expanded=False):
            st.info(
                "Paste a list of eligible student emails below. The system will create their accounts with a random 6-digit temporary PIN and FORCE them to change it on their first login.")

            bulk_emails = st.text_area("Student Emails (Separate with commas or new lines)",
                                       placeholder="student1@college.edu, student2@college.edu")

            if st.button("🚀 Process Bulk Registration", type="primary"):
                if bulk_emails.strip():
                    with st.spinner("Creating accounts and generating secure PINs..."):
                        email_list = re.split(r'[,\n\r]+', bulk_emails)
                        credentials = bulk_register_students(email_list)

                    if credentials:
                        st.success(f"✅ Successfully registered {len(credentials)} new students.")

                        df_creds = pd.DataFrame(credentials)
                        csv_creds = df_creds.to_csv(index=False).encode('utf-8')

                        st.download_button(
                            label="📥 Download Temporary Passwords (CSV)",
                            data=csv_creds,
                            file_name=f"student_credentials_{datetime.date.today()}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                        st.warning(
                            "⚠️ Download this file now! For security reasons, these temporary passwords are only shown once.")
                    else:
                        st.warning("No new accounts created. Emails might already be registered or invalid.")
                else:
                    st.warning("Please enter at least one email address.")

        st.divider()

        students = get_all_registered_students()
        if not students:
            st.info("No students have registered on the platform yet.")
        else:
            st.metric("Total Registered Students", len(students))
            st.divider()

            with st.expander("🛠️ Manual Skill Override (Fix AI Extraction Errors)", expanded=False):
                st.info(
                    "Use this tool if the AI missed a skill on a student's resume, or if a student raises a HelpDesk ticket asking to add a new certification.")
                student_options = {f"{s['name']} ({s['email']})": s for s in students}
                selected_student_label = st.selectbox("Select a Student to Edit", list(student_options.keys()))

                if selected_student_label:
                    selected_student = student_options[selected_student_label]
                    current_skills = get_student_skills_by_id(selected_student['id'])
                    current_skills_str = ", ".join([skill.title() for skill in current_skills])

                    st.write(f"**Editing skills for:** {selected_student['name']}")
                    new_skills_str = st.text_area("Edit Skills (Separate each skill with a comma)",
                                                  value=current_skills_str)

                    if st.button("💾 Save & Override Skills", type="primary", use_container_width=True):
                        updated_skills_list = [s.strip().lower() for s in new_skills_str.split(",") if s.strip()]
                        if update_student_skills_manual(selected_student['id'], updated_skills_list):
                            st.success(f"Skills successfully updated for {selected_student['name']}!")
                            create_notification(selected_student['id'],
                                                "🛠️ Good news! The Placement Cell has manually reviewed and updated the skills on your profile.")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Database error occurred while updating skills.")

            st.divider()
            st.write("#### 🧑‍🎓 Global Directory")
            search_student = st.text_input("🔍 Search students by name or email...", key="student_search")
            display_students = students.copy()
            if search_student:
                term = search_student.lower()
                display_students = [s for s in display_students if
                                    term in s['name'].lower() or term in s['email'].lower()]
            if not display_students:
                st.warning("No students match your search.")
            else:
                df_students = pd.DataFrame(display_students)
                df_students = df_students.rename(
                    columns={'name': 'Student Name', 'email': 'Email Address', 'joined_date': 'Date Registered',
                             'has_resume': 'Resume Uploaded?', 'linkedin_url': 'LinkedIn', 'github_url': 'GitHub'})
                df_students = df_students.drop(columns=['id'])
                st.dataframe(df_students, use_container_width=True, hide_index=True)
                csv_dir = df_students.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Directory (CSV)", data=csv_dir,
                                   file_name=f"smartcampus_student_directory_{datetime.date.today()}.csv",
                                   mime="text/csv", type="secondary")

    with tab6:
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
                st.write("#### 🎓 All Placed Students")
                for entry in hall_of_fame[3:]:
                    st.info(
                        f"**{entry['name']}** secured a position as **{entry['title']}** at **🏢 {entry['company']}**!")
        else:
            st.info("The Placement Hall of Fame is currently empty. Start approving offers to see students here!")

    with tab7:
        st.subheader("🎫 HelpDesk Management")
        tickets = get_all_tickets()

        if not tickets:
            st.info("No tickets raised by students yet.")
        else:
            open_tickets = [t for t in tickets if t['status'] == 'Open']
            resolved_tickets = [t for t in tickets if t['status'] == 'Resolved']

            st.write(f"### 🔴 Action Required: Open Tickets ({len(open_tickets)})")
            if open_tickets:
                for t in open_tickets:
                    with st.container(border=True):
                        st.markdown(
                            f"**From:** {t['name']} ({t['email']})  |  **Category:** `{t['category']}`  |  **Date:** {t['created_at'].strftime('%b %d')}")
                        st.write(f"**Issue:** {t['message']}")

                        if t['category'] == "Profile Correction":
                            st.warning("🛠️ **Profile Correction Request Detected**")
                            current_skills = get_student_skills_by_id(t['student_id'])
                            current_skills_str = ", ".join([s.title() for s in current_skills])

                            new_skills_str = st.text_area("Edit Student's Extracted Skills (Comma separated)",
                                                          value=current_skills_str, key=f"edit_skills_{t['id']}")
                            reply = st.text_area("Write your reply to the student...", key=f"reply_box_{t['id']}")

                            if st.button("💾 Update Skills & Resolve Ticket", type="primary",
                                         key=f"resolve_skill_{t['id']}"):
                                if reply:
                                    updated_skills_list = [s.strip().lower() for s in new_skills_str.split(",") if
                                                           s.strip()]
                                    if update_student_skills_manual(t['student_id'],
                                                                    updated_skills_list) and resolve_ticket(t['id'],
                                                                                                            reply):
                                        create_notification(t['student_id'],
                                                            f"🎫 Your HelpDesk ticket has been resolved and your skills have been updated!")
                                        st.success("Skills updated and ticket successfully resolved!")
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.warning("Please type a reply before resolving the ticket.")
                        else:
                            reply = st.text_area("Write your reply to the student...", key=f"reply_box_{t['id']}")

                            if st.button("Send Reply & Mark Resolved", type="primary", key=f"resolve_btn_{t['id']}"):
                                if reply:
                                    if resolve_ticket(t['id'], reply):
                                        create_notification(t['student_id'],
                                                            f"🎫 Your HelpDesk ticket regarding '{t['category']}' has been answered and resolved!")
                                        st.success("Ticket successfully resolved!")
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.warning("Please type a reply before resolving the ticket.")
            else:
                st.success("All caught up! You have no open tickets to review.")

            st.divider()

            with st.expander(f"🟢 View Archive: Resolved Tickets ({len(resolved_tickets)})"):
                for t in resolved_tickets:
                    st.markdown(f"**{t['name']}** - `{t['category']}`")
                    st.write(f"**Student Asked:** {t['message']}")
                    st.info(f"**Coordinator Answered:** {t['reply']}")
                    st.divider()

    with tab8:
        st.subheader("💬 Campus Interview Experiences")
        st.caption("Read real interview experiences and tips shared by your students.")

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
            st.info("No interview experiences have been shared yet.")