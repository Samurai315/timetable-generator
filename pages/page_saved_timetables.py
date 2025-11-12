"""
Saved Timetables Page - Browse, view, and manage saved timetables
Access control and version management
"""
from theme import apply_light_mode_css
apply_light_mode_css()
import streamlit as st
from auth_manager import prevent_url_manipulation, get_current_user, is_admin
from auth_database import AuthDatabase
import pandas as pd
import json
from datetime import datetime

# Security check
prevent_url_manipulation()

st.title("💾Saved Timetables")
# Get databases
auth_db = st.session_state.auth_db
db = st.session_state.db
user = get_current_user()

# Header
st.title("💾 Saved Timetables")
st.markdown("### Browse and manage saved timetable versions")
st.markdown("---")

# Sidebar filters
with st.sidebar:
    st.markdown("### 🔍 Filters")
    
    # Algorithm filter
    saved_timetables = auth_db.get_all_saved_timetables()
    algorithms = list(set([tt['algorithm_used'] for tt in saved_timetables]))
    
    selected_algorithm = st.multiselect(
        "Filter by Algorithm",
        options=algorithms,
        default=algorithms
    )
    
    # Fitness score filter
    min_fitness = st.slider(
        "Minimum Fitness Score",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0
    )
    
    # Sort by
    sort_by = st.selectbox(
        "Sort By",
        options=["Newest First", "Oldest First", "Highest Fitness", "Lowest Fitness"]
    )
    
    st.markdown("---")
    
    # Save new timetable button
    if st.button("➕ Save Current Timetable", use_container_width=True, type="primary"):
        if st.session_state.get('generated_timetable') is not None:
            st.session_state.show_save_dialog = True
        else:
            st.error("No timetable generated to save!")

# Filter timetables
filtered_timetables = [
    tt for tt in saved_timetables
    if tt['algorithm_used'] in selected_algorithm
    and tt['fitness_score'] >= min_fitness
]

# Sort timetables
if sort_by == "Newest First":
    filtered_timetables.sort(key=lambda x: x['created_at'], reverse=True)
elif sort_by == "Oldest First":
    filtered_timetables.sort(key=lambda x: x['created_at'])
elif sort_by == "Highest Fitness":
    filtered_timetables.sort(key=lambda x: x['fitness_score'], reverse=True)
else:  # Lowest Fitness
    filtered_timetables.sort(key=lambda x: x['fitness_score'])

# Statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Saved", len(saved_timetables))
with col2:
    st.metric("Filtered Results", len(filtered_timetables))
with col3:
    avg_fitness = sum([tt['fitness_score'] for tt in filtered_timetables]) / len(filtered_timetables) if filtered_timetables else 0
    st.metric("Avg Fitness", f"{avg_fitness:.2f}")
with col4:
    st.metric("Algorithms", len(algorithms))

st.markdown("---")

# Save Dialog (if triggered)
if st.session_state.get('show_save_dialog', False):
    with st.form("save_timetable_form"):
        st.markdown("### 💾 Save Current Timetable")
        
        col1, col2 = st.columns(2)
        with col1:
            version_name = st.text_input("Version Name*", placeholder="e.g., Semester1_Fall2025_v1")
            algorithm_used = st.selectbox("Algorithm Used*", options=["Genetic Algorithm", "CSP", "Hybrid", "Other"])
        
        with col2:
            fitness_score = st.number_input("Fitness Score*", min_value=0.0, max_value=100.0, value=85.0, step=0.1)
            tags_input = st.text_input("Tags (comma-separated)", placeholder="e.g., fall2025, final, approved")
        
        version_description = st.text_area("Description", placeholder="Optional description of this timetable version")
        
        col1, col2 = st.columns(2)
        with col1:
            save_button = st.form_submit_button("💾 Save Timetable", use_container_width=True, type="primary")
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if save_button:
            if not version_name or not algorithm_used:
                st.error("Please fill in all required fields!")
            else:
                # Get current timetable data
                timetable_data = st.session_state.generated_timetable
                generation_config = st.session_state.get('generation_config', {})
                
                # Parse tags
                tags = [tag.strip() for tag in tags_input.split(',')] if tags_input else []
                
                # Metadata
                metadata = {
                    'batches_count': len(st.session_state.get('selected_batches', [])),
                    'generated_at': datetime.now().isoformat(),
                    'app_version': '2.0'
                }
                
                # Save to database
                success, message, timetable_id = auth_db.save_timetable(
                    version_name=version_name,
                    algorithm_used=algorithm_used,
                    fitness_score=fitness_score,
                    timetable_data=timetable_data,
                    generation_config=generation_config,
                    created_by=user['user_id'],
                    version_description=version_description,
                    metadata=metadata,
                    tags=tags
                )
                
                if success:
                    st.success(f"✅ {message}")
                    st.session_state.show_save_dialog = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        if cancel_button:
            st.session_state.show_save_dialog = False
            st.rerun()
    
    st.markdown("---")

# Display timetables
if not filtered_timetables:
    st.info("No saved timetables found matching the filters.")
else:
    # Table view
    st.markdown("### 📋 Saved Timetables List")
    
    for idx, tt in enumerate(filtered_timetables):
        with st.expander(
            f"{'⭐' if tt['fitness_score'] >= 90 else '📅'} **{tt['version_name']}** - "
            f"{tt['algorithm_used']} (Score: {tt['fitness_score']:.2f}) - "
            f"by {tt['created_by_name']}"
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Description:** {tt['version_description'] or 'No description provided'}")
                st.markdown(f"**Created by:** {tt['created_by_name']} ({tt['created_by_username']})")
                st.markdown(f"**Created at:** {tt['created_at']}")
                st.markdown(f"**Fitness Score:** {tt['fitness_score']:.2f}%")
                st.markdown(f"**Algorithm:** {tt['algorithm_used']}")
                if tt['tags']:
                    tags_display = ' '.join([f"`{tag}`" for tag in tt['tags']])
                    st.markdown(f"**Tags:** {tags_display}")
                
                # Metadata (avoid nested expanders inside this expander—use st.json directly)
                if tt['metadata']:
                    st.markdown("📊 Metadata")
                    st.json(tt['metadata'])
                
                # Generation Configuration
                if tt['generation_config']:
                    st.markdown("⚙️ Generation Configuration")
                    st.json(tt['generation_config'])
            
            with col2:
                st.markdown("#### Actions")
                
                # Load button
                if st.button("📖 Load Timetable", key=f"load_{tt['id']}", use_container_width=True):
                    st.session_state.generated_timetable = tt['timetable_data']
                    st.session_state.fitness_score = tt['fitness_score']
                    st.session_state.selected_timetable_id = tt['id']
                    
                    # Log access
                    auth_db.log_timetable_access(tt['id'], user['user_id'], 'view')
                    
                    st.success("✅ Timetable loaded successfully!")
                    st.info("Go to 'View & Export' page to see details")
                
                # View button
                if st.button("👁️ View Details", key=f"view_{tt['id']}", use_container_width=True):
                    st.session_state.selected_timetable_id = tt['id']
                    auth_db.log_timetable_access(tt['id'], user['user_id'], 'view')
                
                # Export button
                if st.button("📥 Export JSON", key=f"export_{tt['id']}", use_container_width=True):
                    export_data = {
                        'version_name': tt['version_name'],
                        'algorithm_used': tt['algorithm_used'],
                        'fitness_score': tt['fitness_score'],
                        'timetable_data': tt['timetable_data'],
                        'generation_config': tt['generation_config'],
                        'metadata': tt['metadata'],
                        'created_at': tt['created_at']
                    }
                    
                    json_str = json.dumps(export_data, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"{tt['version_name']}.json",
                        mime="application/json",
                        key=f"download_{tt['id']}"
                    )
                    
                    # Log access
                    auth_db.log_timetable_access(tt['id'], user['user_id'], 'export')
                
                # Delete button (admin only or creator)
                if is_admin() or user['user_id'] == tt['created_by']:
                    if st.button("🗑️ Delete", key=f"delete_{tt['id']}", use_container_width=True, type="secondary"):
                        success, message = auth_db.delete_timetable(tt['id'], user['user_id'])
                        if success:
                            st.success(message)
                            st.experimental_rerun()
                        else:
                            st.error(message)


# Back to dashboard
st.markdown("---")
if st.button("🏠 Back to Dashboard"):
    st.switch_page("pages/page_dashboard.py")
