"""
Timetable Views Page - Multiple view modes for timetables
📅 Batch View | 👨‍🏫 Faculty View | 🏛️ Room View | 📚 Subject View
"""
from theme import apply_light_mode_css
apply_light_mode_css()
import streamlit as st
from auth_manager import prevent_url_manipulation, get_current_user
import pandas as pd
from typing import Dict, List
import json


# Security check
prevent_url_manipulation()



st.title("📊Timetable Views")

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


# Helper function to get single college info safely
def get_college_info_safe():
    colleges = db.get_all('college')
    return colleges[0] if colleges else None


# Helper function to create timetable grid
def create_batch_timetable_grid(batch_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    batch_slots = [slot for slot in timetable_data if slot.get('batch_id') == batch_id]
    
    if not batch_slots:
        return pd.DataFrame()
    
    college_info = get_college_info_safe()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    grid_data = {day: {slot: "FREE" for slot in time_slots} for day in working_days}
    
    for slot_data in batch_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        faculty_id = slot_data.get('faculty_id')
        room_id = slot_data.get('room_id')
        
        subject = db.get_by_id('subjects', subject_id)
        faculty = db.get_by_id('faculty', faculty_id)
        room = db.get_by_id('classrooms', room_id)
        
        subject_name = subject['subject_name'] if subject else "N/A"
        faculty_name = faculty['faculty_name'] if faculty else "N/A"
        room_name = room['room_name'] if room else "N/A"
        
        cell_content = f"{subject_name}\n{faculty_name}\n{room_name}"
        grid_data[day][time_slot] = cell_content
    
    df = pd.DataFrame(grid_data).T
    return df


def create_faculty_timetable_grid(faculty_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    faculty_slots = [slot for slot in timetable_data if slot.get('faculty_id') == faculty_id]
    
    if not faculty_slots:
        return pd.DataFrame()
    
    college_info = get_college_info_safe()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    grid_data = {day: {slot: "FREE" for slot in time_slots} for day in working_days}
    
    for slot_data in faculty_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        batch_id = slot_data.get('batch_id')
        room_id = slot_data.get('room_id')
        
        subject = db.get_by_id('subjects', subject_id)
        batch = db.get_by_id('batches', batch_id)
        room = db.get_by_id('classrooms', room_id)
        
        subject_name = subject['subject_name'] if subject else "N/A"
        batch_name = batch['batch_name'] if batch else "N/A"
        room_name = room['room_name'] if room else "N/A"
        
        cell_content = f"{subject_name}\n{batch_name}\n{room_name}"
        grid_data[day][time_slot] = cell_content
    
    df = pd.DataFrame(grid_data).T
    return df


def create_room_timetable_grid(room_id: int, timetable_data: List[Dict]) -> pd.DataFrame:
    room_slots = [slot for slot in timetable_data if slot.get('room_id') == room_id]
    
    if not room_slots:
        return pd.DataFrame()
    
    college_info = get_college_info_safe()
    if not college_info:
        return pd.DataFrame()
    
    time_slots = json.loads(college_info['time_slots']) if isinstance(college_info['time_slots'], str) else college_info['time_slots']
    working_days = json.loads(college_info['working_days']) if isinstance(college_info['working_days'], str) else college_info['working_days']
    
    grid_data = {day: {slot: "VACANT" for slot in time_slots} for day in working_days}
    
    for slot_data in room_slots:
        day = slot_data.get('day')
        time_slot = slot_data.get('time_slot')
        subject_id = slot_data.get('subject_id')
        batch_id = slot_data.get('batch_id')
        faculty_id = slot_data.get('faculty_id')
        
        subject = db.get_by_id('subjects', subject_id)
        batch = db.get_by_id('batches', batch_id)
        faculty = db.get_by_id('faculty', faculty_id)
        
        subject_name = subject['subject_name'] if subject else "N/A"
        batch_name = batch['batch_name'] if batch else "N/A"
        faculty_name = faculty['faculty_name'] if faculty else "N/A"
        
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
    
    batches = db.get_all('batches')
    
    if not batches:
        st.warning("No batches found in the database")
    else:
        batch_options = {f"{batch['batch_name']} - {batch['semester']} Semester": batch['id'] for batch in batches}
        selected_batch_name = st.selectbox("Select Batch", options=list(batch_options.keys()))
        selected_batch_id = batch_options[selected_batch_name]
        
        st.markdown("---")
        
        batch = db.get_by_id('batches', selected_batch_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Batch", batch['batch_name'])
        with col2:
            st.metric("Semester", batch['semester'])
        with col3:
            st.metric("Division", batch.get('section', 'N/A'))
        with col4:
            st.metric("Year", batch.get('year', 'N/A'))
        
        st.markdown("---")
        
        df = create_batch_timetable_grid(selected_batch_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this batch")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"timetable_{batch['batch_name']}.csv",
                mime="text/csv"
            )


# ==================== FACULTY VIEW ====================
with view_tabs[1]:
    st.markdown("### 👨‍🏫 Faculty Timetable View")
    st.markdown("View timetables organized by faculty member")
    
    faculty_list = db.get_all('faculty')
    
    if not faculty_list:
        st.warning("No faculty found in the database")
    else:
        faculty_options = {f"{fac['faculty_name']} ({fac.get('department_id', 'N/A')})": fac['id'] for fac in faculty_list}
        selected_faculty_name = st.selectbox("Select Faculty", options=list(faculty_options.keys()))
        selected_faculty_id = faculty_options[selected_faculty_name]
        
        st.markdown("---")
        
        faculty = db.get_by_id('faculty', selected_faculty_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Name", faculty['faculty_name'])
        with col2:
            st.metric("Department", str(faculty.get('department_id', 'N/A')))
        with col3:
            st.metric("Designation", faculty.get('designation', 'N/A'))
        with col4:
            faculty_slots = [slot for slot in timetable_data if slot.get('faculty_id') == selected_faculty_id]
            st.metric("Classes/Week", len(faculty_slots))
        
        st.markdown("---")
        
        df = create_faculty_timetable_grid(selected_faculty_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this faculty member")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"timetable_{faculty['faculty_name'].replace(' ', '_')}.csv",
                mime="text/csv"
            )


# ==================== ROOM VIEW ====================
with view_tabs[2]:
    st.markdown("### 🏛️ Room Utilization View")
    st.markdown("View room occupancy and scheduling")
    
    rooms = db.get_all('classrooms')
    
    if not rooms:
        st.warning("No rooms found in the database")
    else:
        room_options = {f"{room['room_name']} - {room.get('floor', 'N/A')} (Capacity: {room.get('capacity', 'N/A')})": room['id'] for room in rooms}
        selected_room_name = st.selectbox("Select Room", options=list(room_options.keys()))
        selected_room_id = room_options[selected_room_name]
        
        st.markdown("---")
        
        room = db.get_by_id('classrooms', selected_room_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Room", room['room_name'])
        with col2:
            st.metric("Floor", room.get('floor', 'N/A'))
        with col3:
            st.metric("Capacity", room.get('capacity', 'N/A'))
        
        colleges = db.get_all('college')
        college_info = colleges[0] if colleges else None
        
        if college_info:
            if isinstance(college_info.get('time_slots'), str):
                time_slots = json.loads(college_info['time_slots'])
            else:
                time_slots = college_info.get('time_slots', [])
            
            if isinstance(college_info.get('working_days'), str):
                working_days = json.loads(college_info['working_days'])
            else:
                working_days = college_info.get('working_days', [])
            
            total_slots = len(time_slots) * len(working_days)
        else:
            total_slots = 0
        
        room_slots = [slot for slot in timetable_data if slot.get('room_id') == selected_room_id]
        utilization = (len(room_slots) / total_slots * 100) if total_slots > 0 else 0
        with col4:
            st.metric("Utilization", f"{utilization:.1f}%")
        
        st.markdown("---")
        
        df = create_room_timetable_grid(selected_room_id, timetable_data)
        
        if df.empty:
            st.info("No timetable data available for this room")
        else:
            st.dataframe(df, use_container_width=True, height=500)
            
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"room_schedule_{room['room_name']}.csv",
                mime="text/csv"
            )


# ==================== SUBJECT VIEW ====================
with view_tabs[3]:
    st.markdown("### 📚 Subject Distribution View")
    st.markdown("View how subjects are distributed across batches and faculty")
    
    subjects = db.get_all('subjects')
    
    if not subjects:
        st.warning("No subjects found in the database")
    else:
        subject_options = {f"{sub['subject_name']} ({sub['subject_code']})": sub['id'] for sub in subjects}
        selected_subject_name = st.selectbox("Select Subject", options=list(subject_options.keys()))
        selected_subject_id = subject_options[selected_subject_name]
        
        st.markdown("---")
        
        subject = db.get_by_id('subjects', selected_subject_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Subject", subject['subject_name'])
        with col2:
            st.metric("Code", subject['subject_code'])
        with col3:
            st.metric("Type", subject.get('subject_type', 'N/A'))
        with col4:
            subject_slots = [slot for slot in timetable_data if slot.get('subject_id') == selected_subject_id]
            st.metric("Total Classes/Week", len(subject_slots))
        
        st.markdown("---")
        
        batch_distribution = {}
        faculty_distribution = {}
        
        for slot in [s for s in timetable_data if s.get('subject_id') == selected_subject_id]:
            batch_id = slot.get('batch_id')
            faculty_id = slot.get('faculty_id')
            
            batch = db.get_by_id('batches', batch_id)
            faculty = db.get_by_id('faculty', faculty_id)
            
            batch_name = batch['batch_name'] if batch else 'Unknown'
            faculty_name = faculty['faculty_name'] if faculty else 'Unknown'
            
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
