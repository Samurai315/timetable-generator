import streamlit as st
import json
from database import Database
import theme
from theme import apply_light_mode_css
apply_light_mode_css()
st.title("📝 Data Input")
st.markdown("### Enter all required data for timetable generation")

# Get database from session state
db = st.session_state.db

# Create tabs for different data input sections
tabs = st.tabs([
    "College Info", "Departments", "Classrooms", "Computer Labs", 
    "Faculty", "Programs", "Batches", "Subjects", "Subject Allocation", "Fixed Slots"
])

# Tab 0: College Information
with tabs[0]:
    st.header("College Information")
    
    with st.form("college_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            college_name = st.text_input("College Name*", placeholder="e.g., MGM University")
            academic_year = st.text_input("Academic Year*", placeholder="e.g., 2024-2025")
            max_periods = st.number_input("Max Periods Per Day*", min_value=1, max_value=10, value=6)
            current_semester = st.selectbox("Current Semester*", ["odd", "even"])
        
        with col2:
            working_days = st.multiselect(
                "Working Days*",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            )
            
            st.markdown("**Time Slots (10 AM to 5 PM)**")
            time_slots = ["10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"]
            
            recess_slot = st.selectbox("Recess/Break Slot", ["None"] + time_slots, index=4)
            
            if recess_slot != "None":
                time_slots_filtered = [slot for slot in time_slots if slot != recess_slot]
            else:
                time_slots_filtered = time_slots
            
            number_of_periods = st.number_input("Number of Periods*", min_value=1, max_value=10, value=6)
        
        submit_college = st.form_submit_button("💾 Save College Information")
        
        if submit_college:
            try:
                college_data = {
                    'name': college_name,
                    'academic_year': academic_year,
                    'max_periods_per_day': max_periods,
                    'current_semester': current_semester,
                    'working_days': working_days,
                    'time_slots': time_slots_filtered,
                    'number_of_periods': number_of_periods
                }
                db.insert_college(college_data)
                st.success("✅ College information saved successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing college info
    st.markdown("---")
    st.subheader("Existing College Information")
    colleges = db.get_all('college')
    if colleges:
        for college in colleges:
            with st.expander(f"{college['name']} - {college['academic_year']}"):
                st.json({
                    'name': college['name'],
                    'academic_year': college['academic_year'],
                    'max_periods_per_day': college['max_periods_per_day'],
                    'current_semester': college['current_semester'],
                    'working_days': json.loads(college['working_days']),
                    'number_of_periods': college['number_of_periods']
                })
                if st.button(f"Delete", key=f"del_college_{college['id']}"):
                    db.delete_by_id('college', college['id'])
                    st.rerun()

# Tab 1: Departments
with tabs[1]:
    st.header("Departments")
    
    with st.form("department_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            dept_code = st.text_input("Department Code*", placeholder="e.g., CSE")
            dept_name = st.text_input("Department Name*", placeholder="e.g., Computer Science Engineering")
        
        with col2:
            hod_name = st.text_input("HOD Name", placeholder="e.g., Dr. John Doe")
        
        submit_dept = st.form_submit_button("💾 Add Department")
        
        if submit_dept:
            try:
                db.insert_department(dept_code, dept_name, hod_name)
                st.success(f"✅ Department '{dept_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing departments
    st.markdown("---")
    st.subheader("Existing Departments")
    departments = db.get_all('departments')
    if departments:
        for dept in departments:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{dept['code']}** - {dept['name']}")
            col2.write(f"HOD: {dept['hod_name'] or 'N/A'}")
            if col3.button("Delete", key=f"del_dept_{dept['id']}"):
                db.delete_by_id('departments', dept['id'])
                st.rerun()
    else:
        st.info("No departments added yet.")

# Tab 2: Classrooms
with tabs[2]:
    st.header("Classrooms")
    
    with st.form("classroom_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            room_code = st.text_input("Room Code*", placeholder="e.g., R101")
            room_name = st.text_input("Room Name*", placeholder="e.g., Lecture Hall 1")
            capacity = st.number_input("Capacity*", min_value=1, value=60)
        
        with col2:
            floor = st.text_input("Floor", placeholder="e.g., Ground Floor")
            building = st.text_input("Building", placeholder="e.g., Main Building")
            facilities = st.text_input("Facilities", placeholder="e.g., Projector, AC, Whiteboard")
        
        submit_classroom = st.form_submit_button("💾 Add Classroom")
        
        if submit_classroom:
            try:
                classroom_data = {
                    'room_code': room_code,
                    'room_name': room_name,
                    'capacity': capacity,
                    'floor': floor,
                    'building': building,
                    'facilities': facilities
                }
                db.insert_classroom(classroom_data)
                st.success(f"✅ Classroom '{room_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing classrooms
    st.markdown("---")
    st.subheader("Existing Classrooms")
    classrooms = db.get_all('classrooms')
    if classrooms:
        for room in classrooms:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{room['room_code']}** - {room['room_name']}")
            col2.write(f"Capacity: {room['capacity']} | {room['building']}")
            if col3.button("Delete", key=f"del_room_{room['id']}"):
                db.delete_by_id('classrooms', room['id'])
                st.rerun()
    else:
        st.info("No classrooms added yet.")

# Tab 3: Computer Labs
with tabs[3]:
    st.header("Computer Labs")
    
    with st.form("lab_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            lab_code = st.text_input("Lab Code*", placeholder="e.g., LAB101")
            lab_name = st.text_input("Lab Name*", placeholder="e.g., Computer Lab 1")
            lab_type = st.text_input("Lab Type", placeholder="e.g., Programming Lab")
        
        with col2:
            computer_capacity = st.number_input("Computer Capacity*", min_value=1, value=30)
            lab_floor = st.text_input("Floor", placeholder="e.g., First Floor")
            lab_building = st.text_input("Building", placeholder="e.g., IT Block")
        
        submit_lab = st.form_submit_button("💾 Add Computer Lab")
        
        if submit_lab:
            try:
                lab_data = {
                    'lab_code': lab_code,
                    'lab_name': lab_name,
                    'lab_type': lab_type,
                    'computer_capacity': computer_capacity,
                    'floor': lab_floor,
                    'building': lab_building
                }
                db.insert_lab(lab_data)
                st.success(f"✅ Lab '{lab_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing labs
    st.markdown("---")
    st.subheader("Existing Computer Labs")
    labs = db.get_all('computer_labs')
    if labs:
        for lab in labs:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{lab['lab_code']}** - {lab['lab_name']}")
            col2.write(f"Capacity: {lab['computer_capacity']} | {lab['lab_type']}")
            if col3.button("Delete", key=f"del_lab_{lab['id']}"):
                db.delete_by_id('computer_labs', lab['id'])
                st.rerun()
    else:
        st.info("No labs added yet.")

# Tab 4: Faculty
with tabs[4]:
    st.header("Faculty Members")
    
    departments = db.get_all('departments')
    dept_options = {f"{d['code']} - {d['name']}": d['id'] for d in departments}
    
    with st.form("faculty_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            faculty_code = st.text_input("Faculty Code*", placeholder="e.g., FAC001")
            faculty_name = st.text_input("Faculty Name*", placeholder="e.g., Dr. Jane Smith")
            faculty_dept = st.selectbox("Department*", options=list(dept_options.keys()) if dept_options else ["No departments available"])
        
        with col2:
            designation = st.text_input("Designation", placeholder="e.g., Associate Professor")
            email = st.text_input("Email", placeholder="e.g., jane.smith@college.edu")
            phone = st.text_input("Phone", placeholder="e.g., +91 9876543210")
        
        submit_faculty = st.form_submit_button("💾 Add Faculty")
        
        if submit_faculty:
            try:
                faculty_data = {
                    'faculty_code': faculty_code,
                    'faculty_name': faculty_name,
                    'department_id': dept_options.get(faculty_dept),
                    'designation': designation,
                    'email': email,
                    'phone': phone
                }
                db.insert_faculty(faculty_data)
                st.success(f"✅ Faculty '{faculty_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing faculty
    st.markdown("---")
    st.subheader("Existing Faculty Members")
    faculty_list = db.get_all('faculty')
    if faculty_list:
        for fac in faculty_list:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{fac['faculty_code']}** - {fac['faculty_name']}")
            col2.write(f"{fac['designation']} | {fac['email']}")
            if col3.button("Delete", key=f"del_fac_{fac['id']}"):
                db.delete_by_id('faculty', fac['id'])
                st.rerun()
    else:
        st.info("No faculty members added yet.")

# Tab 5: Programs
with tabs[5]:
    st.header("Academic Programs")
    
    departments = db.get_all('departments')
    dept_options = {f"{d['code']} - {d['name']}": d['id'] for d in departments}
    
    with st.form("program_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            program_code = st.text_input("Program Code*", placeholder="e.g., BTECH_CSE")
            program_name = st.text_input("Program Name*", placeholder="e.g., B.Tech Computer Science")
        
        with col2:
            duration = st.number_input("Duration (Years)*", min_value=1, max_value=6, value=4)
            program_dept = st.selectbox("Department*", options=list(dept_options.keys()) if dept_options else ["No departments available"])
        
        submit_program = st.form_submit_button("💾 Add Program")
        
        if submit_program:
            try:
                program_data = {
                    'program_code': program_code,
                    'program_name': program_name,
                    'duration': duration,
                    'department_id': dept_options.get(program_dept)
                }
                db.insert_program(program_data)
                st.success(f"✅ Program '{program_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing programs
    st.markdown("---")
    st.subheader("Existing Programs")
    programs = db.get_all('programs')
    if programs:
        for prog in programs:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{prog['program_code']}** - {prog['program_name']}")
            col2.write(f"Duration: {prog['duration']} years")
            if col3.button("Delete", key=f"del_prog_{prog['id']}"):
                db.delete_by_id('programs', prog['id'])
                st.rerun()
    else:
        st.info("No programs added yet.")

# Tab 6: Batches
with tabs[6]:
    st.header("Batches / Classes")
    
    programs = db.get_all('programs')
    prog_options = {f"{p['program_code']} - {p['program_name']}": p['id'] for p in programs}
    
    with st.form("batch_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            batch_code = st.text_input("Batch Code*", placeholder="e.g., CSE_2024_A")
            batch_name = st.text_input("Batch Name*", placeholder="e.g., CSE Batch 2024 Section A")
            batch_program = st.selectbox("Program*", options=list(prog_options.keys()) if prog_options else ["No programs available"])
        
        with col2:
            year = st.number_input("Year*", min_value=1, max_value=6, value=1)
            section = st.text_input("Section", placeholder="e.g., A")
            num_students = st.number_input("Number of Students*", min_value=1, value=60)
            semester = st.number_input("Semester*", min_value=1, max_value=12, value=1)
        
        submit_batch = st.form_submit_button("💾 Add Batch")
        
        if submit_batch:
            try:
                batch_data = {
                    'batch_code': batch_code,
                    'batch_name': batch_name,
                    'program_id': prog_options.get(batch_program),
                    'year': year,
                    'section': section,
                    'number_of_students': num_students,
                    'semester': semester
                }
                db.insert_batch(batch_data)
                st.success(f"✅ Batch '{batch_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing batches
    st.markdown("---")
    st.subheader("Existing Batches")
    batches = db.get_all('batches')
    if batches:
        for batch in batches:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{batch['batch_code']}** - {batch['batch_name']}")
            col2.write(f"Year {batch['year']} | Semester {batch['semester']} | Students: {batch['number_of_students']}")
            if col3.button("Delete", key=f"del_batch_{batch['id']}"):
                db.delete_by_id('batches', batch['id'])
                st.rerun()
    else:
        st.info("No batches added yet.")

# Tab 7: Subjects
with tabs[7]:
    st.header("Subjects")
    
    departments = db.get_all('departments')
    dept_options = {f"{d['code']} - {d['name']}": d['id'] for d in departments}
    
    with st.form("subject_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subject_code = st.text_input("Subject Code*", placeholder="e.g., CS101")
            subject_name = st.text_input("Subject Name*", placeholder="e.g., Data Structures")
            subject_type = st.selectbox("Subject Type*", ["theory", "practical"])
            credits = st.number_input("Credits*", min_value=1, max_value=10, value=3)
        
        with col2:
            theory_hours = st.number_input("Theory Hours per Week", min_value=0, max_value=10, value=3)
            lab_hours = st.number_input("Lab Hours per Week", min_value=0, max_value=10, value=0)
            subject_dept = st.selectbox("Department*", options=list(dept_options.keys()) if dept_options else ["No departments available"])
        
        submit_subject = st.form_submit_button("💾 Add Subject")
        
        if submit_subject:
            try:
                subject_data = {
                    'subject_code': subject_code,
                    'subject_name': subject_name,
                    'subject_type': subject_type,
                    'credits': credits,
                    'theory_hours': theory_hours,
                    'lab_hours': lab_hours,
                    'department_id': dept_options.get(subject_dept)
                }
                db.insert_subject(subject_data)
                st.success(f"✅ Subject '{subject_name}' added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing subjects
    st.markdown("---")
    st.subheader("Existing Subjects")
    subjects = db.get_all('subjects')
    if subjects:
        for subj in subjects:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{subj['subject_code']}** - {subj['subject_name']}")
            col2.write(f"{subj['subject_type'].capitalize()} | Credits: {subj['credits']} | Hours: T{subj['theory_hours']} + L{subj['lab_hours']}")
            if col3.button("Delete", key=f"del_subj_{subj['id']}"):
                db.delete_by_id('subjects', subj['id'])
                st.rerun()
    else:
        st.info("No subjects added yet.")

# Tab 8: Subject Allocation
with tabs[8]:
    st.header("Subject Allocation")
    st.markdown("Assign subjects to batches with faculty")
    
    batches = db.get_all('batches')
    subjects = db.get_all('subjects')
    faculty_list = db.get_all('faculty')
    
    batch_options = {f"{b['batch_code']} - {b['batch_name']}": b['id'] for b in batches}
    subject_options = {f"{s['subject_code']} - {s['subject_name']}": s['id'] for s in subjects}
    faculty_options = {f"{f['faculty_code']} - {f['faculty_name']}": f['id'] for f in faculty_list}
    
    with st.form("allocation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            alloc_batch = st.selectbox("Select Batch*", options=list(batch_options.keys()) if batch_options else ["No batches available"])
            alloc_subject = st.selectbox("Select Subject*", options=list(subject_options.keys()) if subject_options else ["No subjects available"])
        
        with col2:
            alloc_faculty = st.selectbox("Select Faculty*", options=list(faculty_options.keys()) if faculty_options else ["No faculty available"])
            alloc_semester = st.number_input("Semester*", min_value=1, max_value=12, value=1)
            alloc_year = st.text_input("Academic Year*", placeholder="e.g., 2024-2025")
        
        submit_allocation = st.form_submit_button("💾 Allocate Subject")
        
        if submit_allocation:
            try:
                batch_id = batch_options.get(alloc_batch)
                subject_id = subject_options.get(alloc_subject)
                faculty_id = faculty_options.get(alloc_faculty)
                
                db.insert_subject_allocation(batch_id, subject_id, faculty_id, alloc_semester, alloc_year)
                st.success("✅ Subject allocated successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing allocations
    st.markdown("---")
    st.subheader("Existing Allocations")
    allocations = db.get_all('subject_allocation')
    if allocations:
        for alloc in allocations:
            batch = db.get_by_id('batches', alloc['batch_id'])
            subject = db.get_by_id('subjects', alloc['subject_id'])
            faculty = db.get_by_id('faculty', alloc['faculty_id'])
            
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{batch['batch_code']}** → {subject['subject_code']}")
            col2.write(f"Faculty: {faculty['faculty_name']} | Sem: {alloc['semester']}")
            if col3.button("Delete", key=f"del_alloc_{alloc['id']}"):
                db.delete_by_id('subject_allocation', alloc['id'])
                st.rerun()
    else:
        st.info("No subject allocations yet.")

# Tab 9: Fixed Slots
with tabs[9]:
    st.header("Fixed / Static Slots")
    st.markdown("Define manually fixed time slots that will be respected during generation")
    
    batches = db.get_all('batches')
    subjects = db.get_all('subjects')
    faculty_list = db.get_all('faculty')
    classrooms = db.get_all('classrooms')
    labs = db.get_all('computer_labs')
    
    batch_options = {f"{b['batch_code']} - {b['batch_name']}": b['id'] for b in batches}
    subject_options = {f"{s['subject_code']} - {s['subject_name']}": s['id'] for s in subjects}
    faculty_options = {f"{f['faculty_code']} - {f['faculty_name']}": f['id'] for f in faculty_list}
    
    # Get time slots from college info
    colleges = db.get_all('college')
    if colleges:
        college_info = colleges[0]
        working_days = json.loads(college_info['working_days'])
        time_slots = json.loads(college_info['time_slots'])
    else:
        working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        time_slots = ["10:00-11:00", "11:00-12:00", "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"]
    
    with st.form("fixed_slot_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fixed_batch = st.selectbox("Batch*", options=list(batch_options.keys()) if batch_options else ["No batches available"])
            fixed_day = st.selectbox("Day*", options=working_days)
            fixed_time = st.selectbox("Time Slot*", options=time_slots)
        
        with col2:
            fixed_subject = st.selectbox("Subject*", options=list(subject_options.keys()) if subject_options else ["No subjects available"])
            fixed_faculty = st.selectbox("Faculty*", options=list(faculty_options.keys()) if faculty_options else ["No faculty available"])
        
        with col3:
            room_type = st.selectbox("Room Type*", ["classroom", "lab"])
            
            if room_type == "classroom":
                room_options = {f"{r['room_code']} - {r['room_name']}": r['id'] for r in classrooms}
            else:
                room_options = {f"{l['lab_code']} - {l['lab_name']}": l['id'] for l in labs}
            
            fixed_room = st.selectbox("Room*", options=list(room_options.keys()) if room_options else ["No rooms available"])
        
        submit_fixed = st.form_submit_button("💾 Add Fixed Slot")
        
        if submit_fixed:
            try:
                fixed_data = {
                    'batch_id': batch_options.get(fixed_batch),
                    'day': fixed_day,
                    'time_slot': fixed_time,
                    'subject_id': subject_options.get(fixed_subject),
                    'faculty_id': faculty_options.get(fixed_faculty),
                    'room_id': room_options.get(fixed_room),
                    'room_type': room_type
                }
                db.insert_fixed_slot(fixed_data)
                st.success("✅ Fixed slot added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Display existing fixed slots
    st.markdown("---")
    st.subheader("Existing Fixed Slots")
    fixed_slots = db.get_all('fixed_slots')
    if fixed_slots:
        for slot in fixed_slots:
            batch = db.get_by_id('batches', slot['batch_id'])
            subject = db.get_by_id('subjects', slot['subject_id'])
            faculty = db.get_by_id('faculty', slot['faculty_id'])
            
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{batch['batch_code']}** | {slot['day']} {slot['time_slot']}")
            col2.write(f"{subject['subject_code']} - {faculty['faculty_name']}")
            if col3.button("Delete", key=f"del_fixed_{slot['id']}"):
                db.delete_by_id('fixed_slots', slot['id'])
                st.rerun()
    else:
        st.info("No fixed slots defined yet.")

st.markdown("---")
st.success("💡 **Tip:** Complete all data entry before moving to the 'Configure & Generate' page.")
