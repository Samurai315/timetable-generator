"""
Analytics Page - Comprehensive analytics for timetables
Workload distribution, constraint violations, utilization metrics
"""

import streamlit as st
from auth_manager import prevent_url_manipulation, get_current_user
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import json

# Security check
prevent_url_manipulation()

st.set_page_config(
    page_title="Analytics",
    page_icon="📈",
    layout="wide"
)

# Get databases
db = st.session_state.db
auth_db = st.session_state.auth_db
user = get_current_user()

# Helper function to get timetable data
def get_timetable_data():
    """Get current or selected timetable data"""
    if st.session_state.get('generated_timetable'):
        return st.session_state.generated_timetable
    elif st.session_state.get('selected_timetable_id'):
        tt = auth_db.get_timetable_by_id(st.session_state.selected_timetable_id)
        return tt['timetable_data'] if tt else None
    return None

# Header
st.title("📈 Timetable Analytics")
st.markdown("### Comprehensive analysis and insights")
st.markdown("---")

# Check if timetable exists
timetable_data = get_timetable_data()

if not timetable_data:
    st.warning("⚠️ No timetable loaded for analysis!")
    st.info("Please generate a timetable or load a saved one first.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 Generate New Timetable", use_container_width=True, type="primary"):
            st.switch_page("page_configure_generate.py")
    with col2:
        if st.button("💾 Load Saved Timetable", use_container_width=True):
            st.switch_page("pages/page_saved_timetables.py")
    st.stop()

# Analytics tabs
tabs = st.tabs([
    "📊 Overview",
    "👨‍🏫 Faculty Workload",
    "🏛️ Room Utilization",
    "📅 Batch Distribution",
    "⚠️ Constraint Analysis"
])

# ==================== OVERVIEW TAB ====================
with tabs[0]:
    st.markdown("### 📊 Timetable Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_slots = len(timetable_data)
        st.metric("Total Scheduled Slots", total_slots)
    
    with col2:
        unique_batches = len(set([slot['batch_id'] for slot in timetable_data]))
        st.metric("Active Batches", unique_batches)
    
    with col3:
        unique_faculty = len(set([slot['faculty_id'] for slot in timetable_data]))
        st.metric("Faculty Involved", unique_faculty)
    
    with col4:
        unique_rooms = len(set([slot['room_id'] for slot in timetable_data]))
        st.metric("Rooms Used", unique_rooms)
    
    st.markdown("---")
    
    # Distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 Slots per Day")
        day_distribution = {}
        for slot in timetable_data:
            day = slot.get('day', 'Unknown')
            day_distribution[day] = day_distribution.get(day, 0) + 1
        
        df_days = pd.DataFrame(list(day_distribution.items()), columns=['Day', 'Slots'])
        fig = px.bar(df_days, x='Day', y='Slots', 
                     title='Classes per Day',
                     color='Slots',
                     color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏰ Slots per Time Period")
        time_distribution = {}
        for slot in timetable_data:
            time_slot = slot.get('time_slot', 'Unknown')
            time_distribution[time_slot] = time_distribution.get(time_slot, 0) + 1
        
        df_times = pd.DataFrame(list(time_distribution.items()), columns=['Time Slot', 'Count'])
        fig = px.bar(df_times, x='Time Slot', y='Count',
                     title='Classes per Time Slot',
                     color='Count',
                     color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Subject type distribution
    st.markdown("#### 📚 Subject Type Distribution")
    subject_type_dist = {}
    for slot in timetable_data:
        subject_id = slot.get('subject_id')
        subject = db.get_subject_by_id(subject_id)
        if subject:
            subject_type = subject.get('subject_type', 'Unknown')
            subject_type_dist[subject_type] = subject_type_dist.get(subject_type, 0) + 1
    
    df_subject_types = pd.DataFrame(list(subject_type_dist.items()), columns=['Type', 'Count'])
    fig = px.pie(df_subject_types, values='Count', names='Type',
                 title='Theory vs Practical Distribution',
                 color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig, use_container_width=True)

# ==================== FACULTY WORKLOAD TAB ====================
with tabs[1]:
    st.markdown("### 👨‍🏫 Faculty Workload Analysis")
    
    # Calculate faculty workload
    faculty_workload = {}
    faculty_details = {}
    
    for slot in timetable_data:
        faculty_id = slot.get('faculty_id')
        if faculty_id:
            faculty_workload[faculty_id] = faculty_workload.get(faculty_id, 0) + 1
            
            if faculty_id not in faculty_details:
                faculty = db.get_faculty_by_id(faculty_id)
                if faculty:
                    faculty_details[faculty_id] = {
                        'name': faculty['name'],
                        'department': faculty['department']
                    }
    
    # Create workload dataframe
    workload_data = []
    for faculty_id, classes in faculty_workload.items():
        if faculty_id in faculty_details:
            workload_data.append({
                'Faculty': faculty_details[faculty_id]['name'],
                'Department': faculty_details[faculty_id]['department'],
                'Classes per Week': classes
            })
    
    df_workload = pd.DataFrame(workload_data)
    df_workload = df_workload.sort_values('Classes per Week', ascending=False)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Faculty", len(faculty_workload))
    with col2:
        avg_workload = sum(faculty_workload.values()) / len(faculty_workload) if faculty_workload else 0
        st.metric("Average Workload", f"{avg_workload:.1f} classes/week")
    with col3:
        max_workload = max(faculty_workload.values()) if faculty_workload else 0
        st.metric("Max Workload", f"{max_workload} classes/week")
    with col4:
        min_workload = min(faculty_workload.values()) if faculty_workload else 0
        st.metric("Min Workload", f"{min_workload} classes/week")
    
    st.markdown("---")
    
    # Workload distribution chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(df_workload, x='Faculty', y='Classes per Week',
                     color='Classes per Week',
                     title='Faculty Workload Distribution',
                     color_continuous_scale='RdYlGn_r',
                     hover_data=['Department'])
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Faculty Workload Table")
        st.dataframe(df_workload, use_container_width=True, hide_index=True, height=400)
    
    st.markdown("---")
    
    # Department-wise distribution
    st.markdown("#### 🏛️ Department-wise Workload")
    dept_workload = {}
    for data in workload_data:
        dept = data['Department']
        classes = data['Classes per Week']
        dept_workload[dept] = dept_workload.get(dept, 0) + classes
    
    df_dept = pd.DataFrame(list(dept_workload.items()), columns=['Department', 'Total Classes'])
    fig = px.pie(df_dept, values='Total Classes', names='Department',
                 title='Classes by Department',
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

# ==================== ROOM UTILIZATION TAB ====================
with tabs[2]:
    st.markdown("### 🏛️ Room Utilization Analysis")
    
    # Calculate room utilization
    room_usage = {}
    room_details = {}
    
    for slot in timetable_data:
        room_id = slot.get('room_id')
        if room_id:
            room_usage[room_id] = room_usage.get(room_id, 0) + 1
            
            if room_id not in room_details:
                room = db.get_room_by_id(room_id)
                if room:
                    room_details[room_id] = {
                        'name': room['name'],
                        'type': room.get('type', 'N/A'),
                        'capacity': room.get('capacity', 'N/A')
                    }
    
    # Calculate total available slots
    college_info = db.get_college_info()
    if college_info:
        time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
        working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
        total_slots = len(time_slots) * len(working_days)
    else:
        total_slots = 50  # Default fallback
    
    # Create utilization dataframe
    utilization_data = []
    for room_id, used_slots in room_usage.items():
        if room_id in room_details:
            utilization_pct = (used_slots / total_slots * 100) if total_slots > 0 else 0
            utilization_data.append({
                'Room': room_details[room_id]['name'],
                'Type': room_details[room_id]['type'],
                'Capacity': room_details[room_id]['capacity'],
                'Used Slots': used_slots,
                'Utilization %': round(utilization_pct, 1)
            })
    
    df_utilization = pd.DataFrame(utilization_data)
    df_utilization = df_utilization.sort_values('Utilization %', ascending=False)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Rooms", len(room_usage))
    with col2:
        avg_utilization = df_utilization['Utilization %'].mean() if not df_utilization.empty else 0
        st.metric("Avg Utilization", f"{avg_utilization:.1f}%")
    with col3:
        max_util = df_utilization['Utilization %'].max() if not df_utilization.empty else 0
        st.metric("Max Utilization", f"{max_util:.1f}%")
    with col4:
        min_util = df_utilization['Utilization %'].min() if not df_utilization.empty else 0
        st.metric("Min Utilization", f"{min_util:.1f}%")
    
    st.markdown("---")
    
    # Utilization chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(df_utilization, x='Room', y='Utilization %',
                     color='Utilization %',
                     title='Room Utilization Rate',
                     color_continuous_scale='RdYlGn',
                     hover_data=['Type', 'Capacity', 'Used Slots'])
        fig.add_hline(y=avg_utilization, line_dash="dash", line_color="red",
                      annotation_text="Average")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Room Utilization Table")
        st.dataframe(df_utilization, use_container_width=True, hide_index=True, height=400)
    
    st.markdown("---")
    
    # Room type distribution
    st.markdown("#### 🏛️ Room Type Distribution")
    type_usage = {}
    for data in utilization_data:
        room_type = data['Type']
        used_slots = data['Used Slots']
        type_usage[room_type] = type_usage.get(room_type, 0) + used_slots
    
    df_type = pd.DataFrame(list(type_usage.items()), columns=['Room Type', 'Total Usage'])
    fig = px.pie(df_type, values='Total Usage', names='Room Type',
                 title='Usage by Room Type',
                 color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig, use_container_width=True)

# ==================== BATCH DISTRIBUTION TAB ====================
with tabs[3]:
    st.markdown("### 📅 Batch Distribution Analysis")
    
    # Calculate batch distribution
    batch_classes = {}
    batch_details = {}
    
    for slot in timetable_data:
        batch_id = slot.get('batch_id')
        if batch_id:
            batch_classes[batch_id] = batch_classes.get(batch_id, 0) + 1
            
            if batch_id not in batch_details:
                batch = db.get_batch_by_id(batch_id)
                if batch:
                    batch_details[batch_id] = {
                        'name': batch['name'],
                        'semester': batch['semester'],
                        'year': batch.get('year', 'N/A')
                    }
    
    # Create distribution dataframe
    batch_data = []
    for batch_id, classes in batch_classes.items():
        if batch_id in batch_details:
            batch_data.append({
                'Batch': batch_details[batch_id]['name'],
                'Semester': batch_details[batch_id]['semester'],
                'Year': batch_details[batch_id]['year'],
                'Classes per Week': classes
            })
    
    df_batches = pd.DataFrame(batch_data)
    df_batches = df_batches.sort_values('Classes per Week', ascending=False)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Batches", len(batch_classes))
    with col2:
        avg_classes = sum(batch_classes.values()) / len(batch_classes) if batch_classes else 0
        st.metric("Avg Classes", f"{avg_classes:.1f}/week")
    with col3:
        max_classes = max(batch_classes.values()) if batch_classes else 0
        st.metric("Max Classes", f"{max_classes}/week")
    with col4:
        min_classes = min(batch_classes.values()) if batch_classes else 0
        st.metric("Min Classes", f"{min_classes}/week")
    
    st.markdown("---")
    
    # Distribution chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(df_batches, x='Batch', y='Classes per Week',
                     color='Semester',
                     title='Classes per Batch',
                     barmode='group',
                     hover_data=['Year'])
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Batch Distribution Table")
        st.dataframe(df_batches, use_container_width=True, hide_index=True, height=400)

# ==================== CONSTRAINT ANALYSIS TAB ====================
with tabs[4]:
    st.markdown("### ⚠️ Constraint Analysis")
    st.info("Analyzing potential conflicts and constraint violations...")
    
    # Check for conflicts
    conflicts = []
    
    # 1. Faculty double booking
    faculty_schedule = {}
    for slot in timetable_data:
        day = slot.get('day')
        time_slot = slot.get('time_slot')
        faculty_id = slot.get('faculty_id')
        
        key = f"{day}_{time_slot}_{faculty_id}"
        if key in faculty_schedule:
            faculty = db.get_faculty_by_id(faculty_id)
            conflicts.append({
                'Type': 'Faculty Double Booking',
                'Entity': faculty['name'] if faculty else 'Unknown',
                'Day': day,
                'Time Slot': time_slot,
                'Severity': 'High'
            })
        else:
            faculty_schedule[key] = True
    
    # 2. Room double booking
    room_schedule = {}
    for slot in timetable_data:
        day = slot.get('day')
        time_slot = slot.get('time_slot')
        room_id = slot.get('room_id')
        
        key = f"{day}_{time_slot}_{room_id}"
        if key in room_schedule:
            room = db.get_room_by_id(room_id)
            conflicts.append({
                'Type': 'Room Double Booking',
                'Entity': room['name'] if room else 'Unknown',
                'Day': day,
                'Time Slot': time_slot,
                'Severity': 'High'
            })
        else:
            room_schedule[key] = True
    
    # 3. Batch double booking
    batch_schedule = {}
    for slot in timetable_data:
        day = slot.get('day')
        time_slot = slot.get('time_slot')
        batch_id = slot.get('batch_id')
        
        key = f"{day}_{time_slot}_{batch_id}"
        if key in batch_schedule:
            batch = db.get_batch_by_id(batch_id)
            conflicts.append({
                'Type': 'Batch Double Booking',
                'Entity': batch['name'] if batch else 'Unknown',
                'Day': day,
                'Time Slot': time_slot,
                'Severity': 'High'
            })
        else:
            batch_schedule[key] = True
    
    # Display results
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Total Conflicts", len(conflicts), 
                 delta=f"{'✅ No conflicts!' if len(conflicts) == 0 else '⚠️ Issues found'}")
    
    if conflicts:
        st.markdown("---")
        st.error(f"⚠️ Found {len(conflicts)} constraint violations!")
        
        df_conflicts = pd.DataFrame(conflicts)
        st.dataframe(df_conflicts, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No constraint violations detected! The timetable is valid.")
        st.balloons()

# Navigation
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Dashboard", use_container_width=True):
        st.switch_page("pages/page_dashboard.py")
with col2:
    if st.button("📊 Views", use_container_width=True):
        st.switch_page("pages/page_timetable_views.py")
with col3:
    if st.button("💾 Saved Timetables", use_container_width=True):
        st.switch_page("pages/page_saved_timetables.py")
