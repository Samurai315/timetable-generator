"""
Dashboard Page - Main landing page after login
Shows overview and quick actions
"""

import streamlit as st
from auth_manager import prevent_url_manipulation, get_current_user, logout_user, is_admin
from auth_database import AuthDatabase
import pandas as pd
from datetime import datetime

# Security check
prevent_url_manipulation()

st.set_page_config(
    page_title="Dashboard - Timetable Generator",
    page_icon="📊",
    layout="wide"
)

# Get databases
auth_db = st.session_state.auth_db
db = st.session_state.db  # Main timetable database

# Get current user
user = get_current_user()

# Header with user info
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.title(f"📊 Dashboard - Welcome, {user['full_name']}!")
with col2:
    st.markdown(f"**Role:** {user['role'].title()}")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        logout_user(auth_db)
        st.rerun()

st.markdown("---")

# Quick Stats
st.markdown("### 📈 Quick Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Count saved timetables
    saved_timetables = auth_db.get_all_saved_timetables()
    st.metric("💾 Saved Timetables", len(saved_timetables))

with col2:
    # Count active batches from main database
    batches = db.get_all_batches()
    st.metric("📅 Active Batches", len(batches))

with col3:
    # Count faculty from main database
    faculty = db.get_all_faculty()
    st.metric("👨‍🏫 Faculty Members", len(faculty))

with col4:
    # Count subjects from main database
    subjects = db.get_all_subjects()
    st.metric("📚 Subjects", len(subjects))

st.markdown("---")

# Recent Saved Timetables
st.markdown("### 📋 Recently Saved Timetables")

if saved_timetables:
    # Show only last 5
    recent_timetables = saved_timetables[:5]
    
    for tt in recent_timetables:
        with st.expander(f"📅 {tt['version_name']} - {tt['algorithm_used']} (Score: {tt['fitness_score']:.2f})"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Description:** {tt['version_description'] or 'No description'}")
                st.write(f"**Created by:** {tt['created_by_name']} ({tt['created_by_username']})")
                st.write(f"**Created at:** {tt['created_at']}")
                if tt['tags']:
                    st.write(f"**Tags:** {', '.join(tt['tags'])}")
            with col2:
                if st.button("📖 View Details", key=f"view_{tt['id']}"):
                    st.session_state.selected_timetable_id = tt['id']
                    st.switch_page("pages/page_saved_timetables.py")
else:
    st.info("No saved timetables yet. Generate and save your first timetable!")

st.markdown("---")

# Quick Actions
st.markdown("### ⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🆕 Generate New Timetable", use_container_width=True, type="primary"):
        st.switch_page("page_configure_generate.py")

with col2:
    if st.button("💾 View Saved Timetables", use_container_width=True):
        st.switch_page("pages/page_saved_timetables.py")

with col3:
    if st.button("📊 View & Export", use_container_width=True):
        st.switch_page("page_view_export.py")

st.markdown("---")

# Admin Section
if is_admin():
    st.markdown("### 👑 Admin Quick Access")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👥 User Management", use_container_width=True):
            st.switch_page("pages/page_user_management.py")
    
    with col2:
        if st.button("📊 System Statistics", use_container_width=True):
            st.switch_page("pages/page_system_stats.py")
    
    with col3:
        if st.button("📝 Activity Logs", use_container_width=True):
            st.switch_page("pages/page_activity_logs.py")

st.markdown("---")

# Recent Activity (if admin)
if is_admin():
    st.markdown("### 📝 Recent System Activity")
    activities = auth_db.get_recent_activities(limit=10)
    
    if activities:
        activity_data = []
        for act in activities:
            activity_data.append({
                'Time': act['timestamp'],
                'User': act['username'] or 'System',
                'Action': act['action'],
                'Details': act['details'] or '-'
            })
        
        df = pd.DataFrame(activity_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity")
