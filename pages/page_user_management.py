"""
System Statistics Page - Admin only
System-wide analytics, database stats, and performance metrics
"""
from theme import apply_light_mode_css
apply_light_mode_css()
import streamlit as st
from auth_manager import prevent_url_manipulation, require_role, get_current_user
from auth_database import AuthDatabase
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# Security check - Admin only
prevent_url_manipulation()
#require_role(['admin'])


st.title("📊System Statistics - Admin")
# Get databases
auth_db = st.session_state.auth_db
db = st.session_state.db
user = get_current_user()

# Header
st.title("📊 System Statistics")
st.markdown("### System-wide Analytics & Performance Metrics")
st.markdown("---")

# Overview Statistics
st.markdown("### 🎯 System Overview")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    # User statistics
    user_stats = auth_db.get_user_statistics()
    st.metric("Total Users", user_stats['total_users'])

with col2:
    # Saved timetables
    tt_stats = auth_db.get_timetable_statistics()
    st.metric("Saved Timetables", tt_stats['total_saved'])

with col3:
    # Batches from main DB
    batches = db.get_all('batches')
    st.metric("Batches", len(batches))

with col4:
    # Faculty from main DB
    faculty = db.get_all('faculty')
    st.metric("Faculty", len(faculty))

with col5:
    # Rooms from main DB
    rooms = db.get_all('classrooms')
    st.metric("Rooms", len(rooms))

st.markdown("---")

# Tabs for different statistics
tabs = st.tabs([
    "👥 User Analytics",
    "💾 Timetable Analytics",
    "🗄️ Database Stats",
    "📈 Performance Metrics"
])

# ==================== USER ANALYTICS TAB ====================
with tabs[0]:
    st.markdown("### 👥 User Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # User role distribution
        st.markdown("#### User Role Distribution")
        role_data = pd.DataFrame(
            list(user_stats['by_role'].items()),
            columns=['Role', 'Count']
        )
        fig = px.pie(role_data, values='Count', names='Role',
                     title='Users by Role',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # User status distribution
        st.markdown("#### User Status Distribution")
        users = auth_db.get_all_users()
        active_count = len([u for u in users if u['is_active']])
        inactive_count = len([u for u in users if not u['is_active']])
        
        status_data = pd.DataFrame({
            'Status': ['Active', 'Inactive'],
            'Count': [active_count, inactive_count]
        })
        fig = px.pie(status_data, values='Count', names='Status',
                     title='Users by Status',
                     color_discrete_sequence=['#2ecc71', '#e74c3c'])
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # User creation timeline
    st.markdown("#### 📅 User Registration Timeline")
    
    # Parse creation dates
    user_dates = {}
    for usr in users:
        created_date = usr['created_at'].split()[0]  # Get date part
        user_dates[created_date] = user_dates.get(created_date, 0) + 1
    
    if user_dates:
        df_timeline = pd.DataFrame(
            list(user_dates.items()),
            columns=['Date', 'New Users']
        ).sort_values('Date')
        
        fig = px.line(df_timeline, x='Date', y='New Users',
                      title='User Registrations Over Time',
                      markers=True)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No user creation data available")
    
    st.markdown("---")
    
    # Recent logins
    st.markdown("#### 🔐 Recent Login Activity")
    recent_logins = [u for u in users if u['last_login']]
    recent_logins = sorted(recent_logins, key=lambda x: x['last_login'] or '', reverse=True)[:10]
    
    if recent_logins:
        login_data = []
        for usr in recent_logins:
            login_data.append({
                'Username': usr['username'],
                'Full Name': usr['full_name'],
                'Role': usr['role'].title(),
                'Last Login': usr['last_login']
            })
        
        df_logins = pd.DataFrame(login_data)
        st.dataframe(df_logins, use_container_width=True, hide_index=True)
    else:
        st.info("No login activity recorded")

# ==================== TIMETABLE ANALYTICS TAB ====================
with tabs[1]:
    st.markdown("### 💾 Timetable Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Saved Timetables", tt_stats['total_saved'])
    with col2:
        st.metric("Average Fitness Score", f"{tt_stats['average_fitness']:.2f}%")
    with col3:
        algorithms_used = len(tt_stats['by_algorithm'])
        st.metric("Algorithms Used", algorithms_used)
    
    st.markdown("---")
    
    # Algorithm distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Algorithm Usage Distribution")
        if tt_stats['by_algorithm']:
            algo_data = pd.DataFrame(
                list(tt_stats['by_algorithm'].items()),
                columns=['Algorithm', 'Count']
            )
            fig = px.bar(algo_data, x='Algorithm', y='Count',
                         title='Timetables by Algorithm',
                         color='Count',
                         color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timetable data available")
    
    with col2:
        st.markdown("#### Algorithm Distribution (Pie)")
        if tt_stats['by_algorithm']:
            fig = px.pie(algo_data, values='Count', names='Algorithm',
                         title='Algorithm Usage %',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timetable data available")
    
    st.markdown("---")
    
    # Timetable creation timeline
    st.markdown("#### 📅 Timetable Creation Timeline")
    
    all_timetables = auth_db.get_all_saved_timetables()
    
    if all_timetables:
        # Parse creation dates
        tt_dates = {}
        for tt in all_timetables:
            created_date = tt['created_at'].split()[0]
            tt_dates[created_date] = tt_dates.get(created_date, 0) + 1
        
        df_tt_timeline = pd.DataFrame(
            list(tt_dates.items()),
            columns=['Date', 'Timetables Created']
        ).sort_values('Date')
        
        fig = px.area(df_tt_timeline, x='Date', y='Timetables Created',
                      title='Timetable Creation Over Time',
                      color_discrete_sequence=['#3498db'])
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timetable creation data available")
    
    st.markdown("---")
    
    # Top creators
    st.markdown("#### 👑 Top Timetable Creators")
    
    if all_timetables:
        creator_counts = {}
        creator_names = {}
        
        for tt in all_timetables:
            creator_id = tt['created_by']
            creator_counts[creator_id] = creator_counts.get(creator_id, 0) + 1
            creator_names[creator_id] = tt['created_by_name']
        
        creator_data = []
        for creator_id, count in creator_counts.items():
            creator_data.append({
                'Creator': creator_names.get(creator_id, 'Unknown'),
                'Timetables Created': count
            })
        
        df_creators = pd.DataFrame(creator_data)
        df_creators = df_creators.sort_values('Timetables Created', ascending=False).head(10)
        
        fig = px.bar(df_creators, x='Creator', y='Timetables Created',
                     title='Top 10 Timetable Creators',
                     color='Timetables Created',
                     color_continuous_scale='Greens')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No creator data available")
    
    st.markdown("---")
    
    # Fitness score distribution
    st.markdown("#### 📊 Fitness Score Distribution")
    
    if all_timetables:
        fitness_scores = [tt['fitness_score'] for tt in all_timetables]
        
        fig = go.Figure(data=[go.Histogram(x=fitness_scores, nbinsx=20)])
        fig.update_layout(
            title='Fitness Score Distribution',
            xaxis_title='Fitness Score',
            yaxis_title='Count',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No fitness score data available")

# ==================== DATABASE STATS TAB ====================
with tabs[2]:
    st.markdown("### 🗄️ Database Statistics")
    
    # Main database stats
    st.markdown("#### Main Timetable Database")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        subjects = db.get_all('subjects')
        st.metric("Subjects", len(subjects))
    
    with col2:
        st.metric("Batches", len(batches))
    
    with col3:
        st.metric("Faculty", len(faculty))
    
    with col4:
        st.metric("Rooms", len(rooms))
    
    st.markdown("---")
    
    # Department distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Faculty by Department")
        dept_counts = {}
        for fac in faculty:
            dept = fac.get('department', 'Unknown')
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        if dept_counts:
            df_dept = pd.DataFrame(
                list(dept_counts.items()),
                columns=['Department', 'Faculty Count']
            )
            fig = px.bar(df_dept, x='Department', y='Faculty Count',
                         title='Faculty Distribution by Department',
                         color='Faculty Count',
                         color_continuous_scale='Viridis')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No department data available")
    
    with col2:
        st.markdown("#### Room Types")
        room_types = {}
        for room in rooms:
            room_type = room.get('type', 'Unknown')
            room_types[room_type] = room_types.get(room_type, 0) + 1
        
        if room_types:
            df_rooms = pd.DataFrame(
                list(room_types.items()),
                columns=['Room Type', 'Count']
            )
            fig = px.pie(df_rooms, values='Count', names='Room Type',
                         title='Room Distribution by Type',
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No room type data available")
    
    st.markdown("---")
    
    # Subject types
    st.markdown("#### Subject Type Distribution")
    subject_types = {}
    for subject in subjects:
        sub_type = subject.get('subject_type', 'Unknown')
        subject_types[sub_type] = subject_types.get(sub_type, 0) + 1
    
    if subject_types:
        df_subjects = pd.DataFrame(
            list(subject_types.items()),
            columns=['Subject Type', 'Count']
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(df_subjects, x='Subject Type', y='Count',
                         title='Theory vs Practical Subjects',
                         color='Count',
                         color_continuous_scale='Oranges')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df_subjects, use_container_width=True, hide_index=True)
    else:
        st.info("No subject type data available")
    
    st.markdown("---")
    
    # Auth database stats
    st.markdown("#### Authentication Database")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(users))
    with col2:
        st.metric("Saved Timetables", len(all_timetables))
    with col3:
        # Count login sessions
        st.metric("Login Sessions", "N/A")  # Can be implemented
    with col4:
        # Count activity logs
        activities = auth_db.get_recent_activities(limit=1000)
        st.metric("Activity Logs", len(activities))

# ==================== PERFORMANCE METRICS TAB ====================
with tabs[3]:
    st.markdown("### 📈 Performance Metrics")
    
    st.info("🚧 Performance monitoring features coming soon!")
    
    # Placeholder metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("System Uptime", "99.9%", delta="0.1%")
    with col2:
        st.metric("Avg Response Time", "125ms", delta="-15ms")
    with col3:
        st.metric("Database Size", "~15 MB", delta="2 MB")
    
    st.markdown("---")
    
    # Activity heatmap placeholder
    st.markdown("#### 📊 System Activity Heatmap")
    st.info("Activity heatmap will show user access patterns across days and hours")
    
    st.markdown("---")
    
    # Most accessed features
    st.markdown("#### 🔥 Most Used Features")
    
    # Count actions from activity logs
    if activities:
        action_counts = {}
        for activity in activities:
            action = activity['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        df_actions = pd.DataFrame(
            list(action_counts.items()),
            columns=['Action', 'Count']
        ).sort_values('Count', ascending=False).head(10)
        
        fig = px.bar(df_actions, x='Action', y='Count',
                     title='Top 10 System Actions',
                     color='Count',
                     color_continuous_scale='Reds')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activity data available")

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
    if st.button("📝 Activity Logs", use_container_width=True):
        st.switch_page("pages/page_activity_logs.py")
