"""
Activity Logs Page - Admin only
View recent and historical system actions from the auth database
"""

import streamlit as st
from auth_manager import prevent_url_manipulation, require_role, get_current_user
from auth_database import AuthDatabase
import pandas as pd
from datetime import datetime

# Security check - Admin only
prevent_url_manipulation()
require_role(['admin'])

st.set_page_config(
    page_title="Activity Logs - Admin",
    page_icon="📝",
    layout="wide"
)

# Get database
auth_db = st.session_state.auth_db
user = get_current_user()

st.title("📝 System Activity Logs")
st.markdown("### View and audit recent actions in the system")

# Time window filter
col1, col2 = st.columns([2, 1])
with col1:
    show_limit = st.selectbox(
        "Show Last N Activities",
        options=[25, 50, 100, 500, 1000],
        index=1
    )
with col2:
    role_filter = st.multiselect(
        "Filter by Role",
        options=['admin', 'faculty', 'viewer'],
        default=['admin', 'faculty', 'viewer']
    )

# Activity fetch
activity_logs = auth_db.get_recent_activities(limit=int(show_limit))

# Role filter
if role_filter:
    activity_logs = [act for act in activity_logs if act['role'] in role_filter if act['role']]

if not activity_logs:
    st.info("No activity logs found for the period/role selected.")
else:
    # Table
    st.markdown(f"**Showing {len(activity_logs)} activities**")
    log_data = []
    for act in activity_logs:
        log_data.append({
            'Time': act['timestamp'],
            'User': act['username'] or 'System',
            'Role': act.get('role', '-'),
            'Action': act['action'],
            'Entity': act.get('entity_type', '-'),
            'Entity ID': act.get('entity_id', '-'),
            'Details': act['details'] or '-'
        })
    df_logs = pd.DataFrame(log_data)
    st.dataframe(df_logs, use_container_width=True, hide_index=True, height=650)

# Navigation
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Dashboard", use_container_width=True):
        st.switch_page("pages/page_dashboard.py")
with col2:
    if st.button("👥 User Management", use_container_width=True):
        st.switch_page("pages/page_user_management.py")
with col3:
    if st.button("📊 System Stats", use_container_width=True):
        st.switch_page("pages/page_system_stats.py")
