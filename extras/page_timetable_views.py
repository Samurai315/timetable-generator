"""
Timetable Views Page - Multiple view modes for timetables
📅 Batch View | 👨‍🏫 Faculty View | 🏛️ Room View | 📚 Subject View
"""

import streamlit as st
from auth_manager import prevent_url_manipulation, get_current_user
import pandas as pd
from typing import Dict, List
import json

# Security check
prevent_url_manipulation()

st.set_page_config(
    page_title="Timetable Views",
    page_icon="📊",
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

# Helper function to create timetable grid
def create_batch_timetable_grid(batch_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    """Create timetable grid for a specific batch"""
    # Get batch slots
    batch_slots = [slot for slot in timetable_data if slot.get('batch_id') == batch_id]
    
    if not batch_slots:
        return pd.DataFrame()
    
    # Get time slots and days from database
    college_info = db.get_college_info()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    # Create grid
    grid_data = {}
    for day in working_days:
        grid_data[day] = {}
        for slot in time_slots:
            grid_data[day][slot] = "FREE"
    
    # Fill grid with timetable data
    for slot_data in batch_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        faculty_id = slot_data.get('faculty_id')
        room_id = slot_data.get('room_id')
        
        # Get subject, faculty, room names
        subject = db.get_subject_by_id(subject_id)
        faculty = db.get_faculty_by_id(faculty_id)
        room = db.get_room_by_id(room_id)
        
        subject_name = subject['name'] if subject else "N/A"
        faculty_name = faculty['name'] if faculty else "N/A"
        room_name = room['name'] if room else "N/A"
        
        cell_content = f"{subject_name}\n{faculty_name}\n{room_name}"
        grid_data[day][time_slot] = cell_content
    
    # Convert to DataFrame
    df = pd.DataFrame(grid_data).T
    return df

def create_faculty_timetable_grid(faculty_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    """Create timetable grid for a specific faculty"""
    faculty_slots = [slot for slot in timetable_data if slot.get('faculty_id') == faculty_id]
    
    if not faculty_slots:
        return pd.DataFrame()
    
    college_info = db.get_college_info()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    grid_data = {}
    for day in working_days:
        grid_data[day] = {}
        for slot in time_slots:
            grid_data[day][slot] = "FREE"
    
    for slot_data in faculty_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        batch_id = slot_data.get('batch_id')
        room_id = slot_data.get('room_id')
        
        batch = db.get_by_id('batches', selected_batch_id)
        faculty = db.get_by_id('faculty', selected_faculty_id)
        subject = db.get_by_id('subjects', selected_subject_id)
        
        subject_name = subject['name'] if subject else "N/A"
        batch_name = batch['name'] if batch else "N/A"
        room_name = room['name'] if room else "N/A"
        
        cell_content = f"{subject_name}\n{batch_name}\n{room_name}"
        grid_data[day][time_slot] = cell_content
    
    df = pd.DataFrame(grid_data).T
    return df

def create_room_timetable_grid(room_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    """Create timetable grid for a specific room"""
    room_slots = [slot for slot in timetable_data if slot.get('room_id') == room_id]
    
    if not room_slots:
        return pd.DataFrame()
    
    college_info = db.get_college_info()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    grid_data = {}
    for day in working_days:
        grid_data[day] = {}
        for slot in time_slots:
            grid_data[day][slot] = "VACANT"
    
    for slot_data in room_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        batch_id = slot_data.get('batch_id')
        faculty_id = slot_data.get('faculty_id')
        
        subject = db.get_subject_by_id(subject_id)
        batch = db.get_batch_by_id(batch_id)
        faculty = db.get_faculty_by_id(faculty_id)
        
        subject_name = subject['name'] if subject else "N/A"
        batch_name = batch['name'] if batch else "N/A"
        faculty_name = faculty['name'] if faculty else "N/A"
        
        cell_content = f"{batch_name}\n{subject_name}\n{faculty_name}"
        grid_data[day][time_slot] = cell_content
    
    df = pd.DataFrame(grid_data).T
    return df

# Header
st.title("📊 Timetable Views")
st.markdown("### Multiple perspectives of your timetable")
st.markdown("---")

# Check if timetable exists
timetable_data = get_timetable_data()

if not timetable_data:
    st.warning("⚠️ No timetable loaded!")
    st.info("Please generate a timetable or load a saved one first.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 Generate New Timetable", use_container_width=True, type="primary"):
            st.switch_page("page_configure_generate.py")
    with col2:
        if st.button("💾 Load Saved Timetable", use_container_width=True):
            st.switch_page("pages/page_saved_timetables.py")
    st.stop()

# View selector
view_tabs = st.tabs(["📅 Batch View", "👨‍🏫 Faculty View", "🏛️ Room View", "📚 Subject View"])

# ==================== BATCH VIEW ====================
with view_tabs[0]:
    st.markdown("### 📅 Batch Timetable View")
    st.markdown("View timetables organized by batch/class")
    
    # Get all batches
    batches = db.get_all_batches()
    
    if not batches:
        st.warning("No batches found in the database")
    else:
        # Batch selector
        batch_options = {f"{batch['name']} - {batch['semester']} Semester": batch['id'] for batch in batches}
        selected_batch_name = st.selectbox("Select Batch", options=list(batch_options.keys()))
        selected_batch_id = batch_options[selected_batch_name]
        
        st.markdown("---")
        
        # Get batch details
        batch = db.get_batch_by_id(selected_batch_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Batch", batch['name'])
        with col2:
            st.metric("Semester", batch['semester'])
        with col3:
            st.metric("Division", batch.get('division', 'N/A'))
        with col4:
            st.metric("Year", batch.get('year', 'N/A'))
        
        st.markdown("---")
        
        # Generate timetable grid
        df = create_batch_timetable_grid(selected_batch_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this batch")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            # Download button
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"timetable_{batch['name']}.csv",
                mime="text/csv"
            )

# ==================== FACULTY VIEW ====================
with view_tabs[1]:
    st.markdown("### 👨‍🏫 Faculty Timetable View")
    st.markdown("View timetables organized by faculty member")
    
    # Get all faculty
    faculty_list = db.get_all_faculty()
    
    if not faculty_list:
        st.warning("No faculty found in the database")
    else:
        # Faculty selector
        faculty_options = {f"{fac['name']} ({fac['department']})": fac['id'] for fac in faculty_list}
        selected_faculty_name = st.selectbox("Select Faculty", options=list(faculty_options.keys()))
        selected_faculty_id = faculty_options[selected_faculty_name]
        
        st.markdown("---")
        
        # Get faculty details
        faculty = db.get_faculty_by_id(selected_faculty_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Name", faculty['name'])
        with col2:
            st.metric("Department", faculty['department'])
        with col3:
            st.metric("Designation", faculty.get('designation', 'N/A'))
        with col4:
            # Calculate teaching load
            faculty_slots = [slot for slot in timetable_data if slot.get('faculty_id') == selected_faculty_id]
            st.metric("Classes/Week", len(faculty_slots))
        
        st.markdown("---")
        
        # Generate timetable grid
        df = create_faculty_timetable_grid(selected_faculty_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this faculty member")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            # Download button
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"timetable_{faculty['name'].replace(' ', '_')}.csv",
                mime="text/csv"
            )

# ==================== ROOM VIEW ====================
with view_tabs[2]:
    st.markdown("### 🏛️ Room Utilization View")
    st.markdown("View room occupancy and scheduling")
    
    # Get all rooms
    rooms = db.get_all_rooms()
    
    if not rooms:
        st.warning("No rooms found in the database")
    else:
        # Room selector
        room_options = {f"{room['name']} - {room.get('type', 'N/A')} (Capacity: {room.get('capacity', 'N/A')})": room['id'] for room in rooms}
        selected_room_name = st.selectbox("Select Room", options=list(room_options.keys()))
        selected_room_id = room_options[selected_room_name]
        
        st.markdown("---")
        
        # Get room details
        room = db.get_room_by_id(selected_room_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Room", room['name'])
        with col2:
            st.metric("Type", room.get('type', 'N/A'))
        with col3:
            st.metric("Capacity", room.get('capacity', 'N/A'))
        with col4:
            # Calculate utilization
            room_slots = [slot for slot in timetable_data if slot.get('room_id') == selected_room_id]
            college_info = db.get_college_info()
            if college_info:
                time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
                working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
                total_slots = len(time_slots) * len(working_days)
                utilization = (len(room_slots) / total_slots * 100) if total_slots > 0 else 0
                st.metric("Utilization", f"{utilization:.1f}%")
        
        st.markdown("---")
        
        # Generate timetable grid
        df = create_room_timetable_grid(selected_room_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this room")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            # Download button
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"room_schedule_{room['name']}.csv",
                mime="text/csv"
            )

# ==================== SUBJECT VIEW ====================
with view_tabs[3]:
    st.markdown("### 📚 Subject Distribution View")
    st.markdown("View how subjects are distributed across batches and faculty")
    
    # Get all subjects
    subjects = db.get_all_subjects()
    
    if not subjects:
        st.warning("No subjects found in the database")
    else:
        # Subject selector
        subject_options = {f"{sub['name']} ({sub['code']})": sub['id'] for sub in subjects}
        selected_subject_name = st.selectbox("Select Subject", options=list(subject_options.keys()))
        selected_subject_id = subject_options[selected_subject_name]
        
        st.markdown("---")
        
        # Get subject details
        subject = db.get_subject_by_id(selected_subject_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Subject", subject['name'])
        with col2:
            st.metric("Code", subject['code'])
        with col3:
            st.metric("Type", subject.get('subject_type', 'N/A'))
        with col4:
            # Calculate total classes
            subject_slots = [slot for slot in timetable_data if slot.get('subject_id') == selected_subject_id]
            st.metric("Total Classes/Week", len(subject_slots))
        
        st.markdown("---")
        
        # Subject distribution analysis
        st.markdown("#### 📊 Distribution Analysis")
        
        # Group by batch
        batch_distribution = {}
        faculty_distribution = {}
        
        for slot in [s for s in timetable_data if s.get('subject_id') == selected_subject_id]:
            batch_id = slot.get('batch_id')
            faculty_id = slot.get('faculty_id')
            
            batch = db.get_batch_by_id(batch_id)
            faculty = db.get_faculty_by_id(faculty_id)
            
            batch_name = batch['name'] if batch else 'Unknown'
            faculty_name = faculty['name'] if faculty else 'Unknown'
            
            batch_distribution[batch_name] = batch_distribution.get(batch_name, 0) + 1
            faculty_distribution[faculty_name] = faculty_distribution.get(faculty_name, 0) + 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Classes per Batch")
            if batch_distribution:
                df_batch = pd.DataFrame(list(batch_distribution.items()), columns=['Batch', 'Classes'])
                st.dataframe(df_batch, use_container_width=True, hide_index=True)
            else:
                st.info("No distribution data")
        
        with col2:
            st.markdown("##### Classes per Faculty")
            if faculty_distribution:
                df_faculty = pd.DataFrame(list(faculty_distribution.items()), columns=['Faculty', 'Classes'])
                st.dataframe(df_faculty, use_container_width=True, hide_index=True)
            else:
                st.info("No distribution data")

# Navigation
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Dashboard", use_container_width=True):
        st.switch_page("pages/page_dashboard.py")
with col2:
    if st.button("📊 Analytics", use_container_width=True):
        st.switch_page("pages/page_analytics.py")
with col3:
    if st.button("💾 Saved Timetables", use_container_width=True):
        st.switch_page("pages/page_saved_timetables.py")
