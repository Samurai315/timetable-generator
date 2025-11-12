import streamlit as st
import json
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from database import Database
import plotly.express as px
import plotly.graph_objects as go
from theme import apply_light_mode_css
apply_light_mode_css()
st.title("📊 View & Export Timetable")
st.markdown("### View generated timetables and export in multiple formats")

# Get database from session state
db = st.session_state.db

# Check if timetable has been generated
if st.session_state.generated_timetable is None:
    st.warning("⚠️ No timetable has been generated yet!")
    st.info("👉 Go to the 'Configure & Generate' page to create a timetable first.")
    
    # Check if there's a saved timetable in database
    saved_timetable = db.get_generated_timetable()
    if saved_timetable:
        st.info("📁 Found a previously saved timetable in the database.")
        if st.button("Load Saved Timetable"):
            st.session_state.generated_timetable = saved_timetable
            if saved_timetable:
                st.session_state.fitness_score = saved_timetable[0].get('fitness_score', 0)
            st.rerun()
    st.stop()

# Get generated timetable
timetable = st.session_state.generated_timetable
fitness_score = st.session_state.fitness_score

# Display summary metrics
st.header("📈 Generation Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Fitness Score", f"{fitness_score:.2f}")
with col2:
    st.metric("Total Slots", len(timetable))
with col3:
    unique_batches = len(set(s['batch_id'] for s in timetable))
    st.metric("Batches", unique_batches)
with col4:
    unique_faculty = len(set(s['faculty_id'] for s in timetable))
    st.metric("Faculty", unique_faculty)

st.markdown("---")

# Section 1: Batch Selection for Display
st.header("1️⃣ Select Batch to View")

# Get unique batches in timetable
batch_ids = list(set(s['batch_id'] for s in timetable))
batches = {b['id']: b for b in db.get_all('batches') if b['id'] in batch_ids}

batch_options = {f"{b['batch_code']} - {b['batch_name']}": b['id'] for b in batches.values()}

if not batch_options:
    st.error("No batches found in generated timetable!")
    st.stop()

selected_batch_display = st.selectbox("Select Batch", options=list(batch_options.keys()))
selected_batch_id = batch_options[selected_batch_display]

st.markdown("---")

# Section 2: Display Timetable
st.header("2️⃣ Timetable View")

# Filter timetable for selected batch
batch_timetable = [s for s in timetable if s['batch_id'] == selected_batch_id]

if not batch_timetable:
    st.warning("No slots found for this batch.")
else:
    # Get college info for days and slots
    colleges = db.get_all('college')
    if colleges:
        college_info = colleges[0]
        working_days = json.loads(college_info['working_days'])
        time_slots = json.loads(college_info['time_slots'])
    else:
        working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        time_slots = ["10:00-11:00", "11:00-12:00", "12:45-13:45", "13:45-14:45", "15:00-16:00", "16:00-17:00"]
    
    # Create timetable grid
    timetable_grid = {day: {slot: None for slot in time_slots} for day in working_days}
    
    # Populate grid
    subjects = {s['id']: s for s in db.get_all('subjects')}
    faculty = {f['id']: f for f in db.get_all('faculty')}
    classrooms = {r['id']: r for r in db.get_all('classrooms')}
    labs = {l['id']: l for l in db.get_all('computer_labs')}
    
    for slot in batch_timetable:
        day = slot['day']
        time = slot['time_slot']
        
        subject = subjects.get(slot['subject_id'], {})
        fac = faculty.get(slot['faculty_id'], {})
        
        if slot['room_type'] == 'classroom':
            room = classrooms.get(slot['room_id'], {})
            room_info = room.get('room_code', 'N/A')
        else:
            lab = labs.get(slot['room_id'], {})
            room_info = lab.get('lab_code', 'N/A')
        
        slot_info = {
            'subject_code': subject.get('subject_code', 'N/A'),
            'subject_name': subject.get('subject_name', 'N/A'),
            'faculty_name': fac.get('faculty_name', 'N/A'),
            'room': room_info,
            'type': subject.get('subject_type', 'N/A'),
            'is_fixed': slot.get('is_fixed', False)
        }
        
        if day in timetable_grid and time in timetable_grid[day]:
            timetable_grid[day][time] = slot_info
    
    # Display as table
    st.subheader(f"Timetable for {selected_batch_display}")
    
    # Create DataFrame for display
    df_data = []
    for time in time_slots:
        row = {'Time': time}
        for day in working_days:
            slot_info = timetable_grid[day][time]
            if slot_info:
                fixed_marker = "🔒 " if slot_info['is_fixed'] else ""
                cell_content = f"{fixed_marker}{slot_info['subject_code']}\n{slot_info['faculty_name']}\n📍 {slot_info['room']}"
                row[day] = cell_content
            else:
                row[day] = "-"
        df_data.append(row)
    
    df_timetable = pd.DataFrame(df_data)
    
    # Display with custom styling
    st.dataframe(df_timetable, use_container_width=True, height=400)
    
    # Legend
    st.caption("🔒 = Fixed/Static Slot")

st.markdown("---")

# Section 3: Analytics
st.header("3️⃣ Analytics & Statistics")

tab1, tab2, tab3 = st.tabs(["Faculty Workload", "Room Utilization", "Daily Distribution"])

with tab1:
    st.subheader("Faculty Workload Analysis")
    
    # Calculate faculty workload
    faculty_workload = {}
    for slot in timetable:
        fid = slot['faculty_id']
        if fid not in faculty_workload:
            faculty_workload[fid] = {'total': 0, 'by_day': {}}
        
        faculty_workload[fid]['total'] += 1
        day = slot['day']
        faculty_workload[fid]['by_day'][day] = faculty_workload[fid]['by_day'].get(day, 0) + 1
    
    # Create workload dataframe
    faculty_data = []
    faculty_dict = {f['id']: f for f in db.get_all('faculty')}
    
    for fid, workload in faculty_workload.items():
        fac = faculty_dict.get(fid, {})
        faculty_data.append({
            'Faculty Code': fac.get('faculty_code', 'N/A'),
            'Faculty Name': fac.get('faculty_name', 'N/A'),
            'Total Hours': workload['total'],
            'Avg Hours/Day': round(workload['total'] / len(working_days), 2)
        })
    
    df_faculty = pd.DataFrame(faculty_data).sort_values('Total Hours', ascending=False)
    st.dataframe(df_faculty, use_container_width=True)
    
    # Bar chart
    if not df_faculty.empty:
        fig = px.bar(df_faculty, x='Faculty Name', y='Total Hours', 
                     title='Faculty Workload Distribution',
                     color='Total Hours',
                     color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Room Utilization")
    
    # Calculate room utilization
    room_usage = {}
    for slot in timetable:
        rid = slot['room_id']
        rtype = slot['room_type']
        if rid not in room_usage:
            room_usage[rid] = {'total': 0, 'type': rtype}
        room_usage[rid]['total'] += 1
    
    # Create room dataframe
    room_data = []
    for rid, usage in room_usage.items():
        if usage['type'] == 'classroom':
            room = next((r for r in classrooms.values() if r['id'] == rid), {})
            room_code = room.get('room_code', 'N/A')
        else:
            lab = next((l for l in labs.values() if l['id'] == rid), {})
            room_code = lab.get('lab_code', 'N/A')
        
        max_slots = len(working_days) * len(time_slots)
        utilization = round((usage['total'] / max_slots) * 100, 2)
        
        room_data.append({
            'Room Code': room_code,
            'Type': usage['type'].capitalize(),
            'Hours Used': usage['total'],
            'Utilization %': utilization
        })
    
    df_rooms = pd.DataFrame(room_data).sort_values('Utilization %', ascending=False)
    st.dataframe(df_rooms, use_container_width=True)
    
    # Pie chart
    if not df_rooms.empty:
        fig = px.pie(df_rooms, values='Hours Used', names='Room Code',
                     title='Room Usage Distribution')
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Daily Class Distribution")
    
    # Calculate daily distribution
    daily_dist = {day: 0 for day in working_days}
    for slot in timetable:
        daily_dist[slot['day']] += 1
    
    df_daily = pd.DataFrame(list(daily_dist.items()), columns=['Day', 'Classes'])
    
    # Line chart
    fig = px.line(df_daily, x='Day', y='Classes', 
                  title='Classes per Day',
                  markers=True)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Section 4: Export Options
st.header("4️⃣ Export Timetable")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📄 JSON Export")
    
    # Prepare JSON data
    json_data = []
    for slot in timetable:
        batch = batches.get(slot['batch_id'], {})
        subject = subjects.get(slot['subject_id'], {})
        fac = faculty.get(slot['faculty_id'], {})
        
        json_data.append({
            'batch_code': batch.get('batch_code', 'N/A'),
            'batch_name': batch.get('batch_name', 'N/A'),
            'day': slot['day'],
            'time_slot': slot['time_slot'],
            'subject_code': subject.get('subject_code', 'N/A'),
            'subject_name': subject.get('subject_name', 'N/A'),
            'faculty_code': fac.get('faculty_code', 'N/A'),
            'faculty_name': fac.get('faculty_name', 'N/A'),
            'room_id': slot['room_id'],
            'room_type': slot['room_type'],
            'is_fixed': slot.get('is_fixed', False)
        })
    
    json_str = json.dumps(json_data, indent=2)
    
    st.download_button(
        label="📥 Download JSON",
        data=json_str,
        file_name="timetable.json",
        mime="application/json",
        use_container_width=True
    )

with col2:
    st.subheader("📊 Excel Export")
    
    # Create Excel file with multiple sheets (one per batch)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for batch_id, batch in batches.items():
            batch_slots = [s for s in timetable if s['batch_id'] == batch_id]
            
            # Create dataframe for this batch
            excel_data = []
            for slot in batch_slots:
                subject = subjects.get(slot['subject_id'], {})
                fac = faculty.get(slot['faculty_id'], {})
                
                if slot['room_type'] == 'classroom':
                    room = classrooms.get(slot['room_id'], {})
                    room_code = room.get('room_code', 'N/A')
                else:
                    lab = labs.get(slot['room_id'], {})
                    room_code = lab.get('lab_code', 'N/A')
                
                excel_data.append({
                    'Day': slot['day'],
                    'Time': slot['time_slot'],
                    'Subject Code': subject.get('subject_code', 'N/A'),
                    'Subject Name': subject.get('subject_name', 'N/A'),
                    'Faculty': fac.get('faculty_name', 'N/A'),
                    'Room': room_code,
                    'Type': subject.get('subject_type', 'N/A'),
                    'Fixed': 'Yes' if slot.get('is_fixed', False) else 'No'
                })
            
            df_batch = pd.DataFrame(excel_data)
            sheet_name = batch['batch_code'][:31]  # Excel sheet name limit
            df_batch.to_excel(writer, sheet_name=sheet_name, index=False)
    
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name="timetable.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col3:
    st.subheader("📑 PDF Export")
    
    def create_pdf():
        """Create formatted PDF timetable"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=18)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        for batch_id, batch in batches.items():
            # Add title
            title = Paragraph(f"Timetable - {batch['batch_code']}", title_style)
            elements.append(title)
            elements.append(Spacer(1, 12))
            
            # Add batch info
            info_style = styles['Normal']
            info_text = f"<b>Batch:</b> {batch['batch_name']} | <b>Year:</b> {batch['year']} | <b>Semester:</b> {batch['semester']}"
            elements.append(Paragraph(info_text, info_style))
            elements.append(Spacer(1, 20))
            
            # Create timetable table
            batch_slots = [s for s in timetable if s['batch_id'] == batch_id]
            
            # Build grid
            batch_grid = {day: {slot: None for slot in time_slots} for day in working_days}
            
            for slot in batch_slots:
                day = slot['day']
                time = slot['time_slot']
                subject = subjects.get(slot['subject_id'], {})
                fac = faculty.get(slot['faculty_id'], {})
                
                if slot['room_type'] == 'classroom':
                    room = classrooms.get(slot['room_id'], {})
                    room_code = room.get('room_code', 'N/A')
                else:
                    lab = labs.get(slot['room_id'], {})
                    room_code = lab.get('lab_code', 'N/A')
                
                cell_text = f"{subject.get('subject_code', 'N/A')}\n{fac.get('faculty_name', 'N/A')}\n{room_code}"
                batch_grid[day][time] = cell_text
            
            # Build table data
            table_data = [['Time'] + working_days]
            
            for time in time_slots:
                row = [time]
                for day in working_days:
                    cell = batch_grid[day][time]
                    row.append(cell if cell else '-')
                table_data.append(row)
            
            # Create table
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            elements.append(PageBreak())
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    if st.button("🔄 Generate PDF", use_container_width=True):
        with st.spinner("Generating PDF..."):
            pdf_buffer = create_pdf()
            
            st.download_button(
                label="📥 Download PDF",
                data=pdf_buffer,
                file_name="timetable.pdf",
                mime="application/pdf",
                use_container_width=True
            )

st.markdown("---")

# Section 5: Fitness History Chart
if st.session_state.get('generation_config', {}).get('algorithm', '').startswith('genetic'):
    if 'fitness_history' in st.session_state and st.session_state.fitness_history:
        st.header("5️⃣ Evolution Progress")
        
        history = st.session_state.fitness_history
        df_history = pd.DataFrame(history)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_history['generation'], y=df_history['best'],
                                 mode='lines', name='Best Fitness',
                                 line=dict(color='green', width=2)))
        fig.add_trace(go.Scatter(x=df_history['generation'], y=df_history['average'],
                                 mode='lines', name='Average Fitness',
                                 line=dict(color='blue', width=2, dash='dash')))
        
        fig.update_layout(title='Fitness Evolution Over Generations',
                         xaxis_title='Generation',
                         yaxis_title='Fitness Score',
                         hovermode='x unified')
        
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.success("✅ All timetables generated successfully! Export in your preferred format above.")