import streamlit as st
from database import Database
from theme import apply_light_mode_css  # Import the CSS injector function from theme.py


# Page configuration
st.set_page_config(
    page_title="Timetable Generator",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()
    st.session_state.db.create_tables()
    st.session_state.db.initialize_default_constraints()
# Apply the global light mode CSS once for all pages
apply_light_mode_css()

# Parse query params for routing
params = st.query_params

page = params.get("page", ["login"])[0]
if page == "login":
    import pages.page_auth_login as current_page
elif page == "dashboard":
    import pages.page_dashboard as current_page
elif page == "page_data_input":
    import pages.page_data_input as current_page
elif page == "page_configure_generate":
    import pages.page_configure_generate as current_page
elif page == "page_view_export":
    import pages.page_view_export as current_page
elif page == "page_saved_timetables":
    import pages.page_saved_timetables as current_page
elif page == "page_timetable_views":
    import pages.page_timetable_views as current_page
elif page == "page_analytics":
    import pages.page_analytics as current_page
elif page == "page_user_management":
    import pages.page_user_management as current_page
elif page == "page_system_stats":
    import pages.page_system_stats as current_page
elif page == "page_activity_logs":
    import pages.page_activity_logs as current_page
else:
    current_page = None
    st.error(f"Page '{page}' not found")

# Initialize main timetable database connection in session state
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()
    st.session_state.db.create_tables()
    st.session_state.db.initialize_default_constraints()

# Initialize session state variables for the app workflow
for key, default in {
    'current_page': 'Data Input',
    'generated_timetable': None,
    'fitness_score': 0.0,
    'selected_batches': [],
    'generation_config': {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Sidebar Info and Navigation ---
with st.sidebar:
    st.title("📅 Timetable Generator")
    st.markdown("---")
    
    # About section
    st.markdown("### About")
    st.info("""
    **Genetic Algorithm-based Timetable Generator**

    This system generates optimal timetables using genetic algorithms that:
    - Respect all hard constraints (no conflicts)
    - Optimize soft constraints (load balancing, gap minimization)
    - Support fixed/static slot definitions
    - Generate parallel timetables for multiple batches
    - Interest-based scheduling
    - Lab alternation for batches
    - Faculty-wise timetable views
    """)
    st.markdown("---")
    
    # Database stats
    st.markdown("### Database Stats")
    try:
        db = st.session_state.db
        stats = {
            "Departments": len(db.get_all('departments')),
            "Faculty": len(db.get_all('faculty')),
            "Programs": len(db.get_all('programs')),
            "Batches": len(db.get_all('batches')),
            "Subjects": len(db.get_all('subjects')),
            "Classrooms": len(db.get_all('classrooms')),
            "Labs": len(db.get_all('computer_labs')),
        }
        col1, col2 = st.columns(2)
        items = list(stats.items())
        for i, (key, value) in enumerate(items):
            with col1 if i % 2 == 0 else col2:
                st.metric(key, value)
    except Exception as e:
        st.error(f"Error loading stats: {e}")

    st.markdown("---")
    st.markdown("### Quick Actions")
    if st.button("🔄 Refresh Database", use_container_width=True):
        st.rerun()

    if st.button("🗑️ Clear Generated Timetable", use_container_width=True):
        try:
            st.session_state.db.clear_generated_timetable()
            st.session_state.generated_timetable = None
            st.session_state.fitness_score = 0.0
            st.success("Timetable cleared successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("### 📚 Saved Versions")
    try:
        versions = db.get_timetable_versions()
        if versions:
            st.metric("Total Versions", len(versions))
            version_options = {f"{v['version_name']} (ID: {v['id']})": v['id'] for v in versions[:10]}
            if version_options:
                selected_version = st.selectbox(
                    "Load Version",
                    options=list(version_options.keys()),
                    key="version_selector"
                )
                if st.button("📥 Load Selected", use_container_width=True):
                    version_id = version_options[selected_version]
                    loaded_tt = db.get_generated_timetable(version_id=version_id)
                    if loaded_tt:
                        st.session_state.generated_timetable = loaded_tt
                        st.session_state.fitness_score = loaded_tt[0].get('fitness_score', 0) if loaded_tt else 0
                        st.success(f"✅ Loaded: {selected_version}")
                        st.rerun()
        else:
            st.info("No saved versions yet")
    except Exception as e:
        st.error(f"Error: {e}")

    # Sidebar navigation radio
PAGE_MAP = {
    "🏠 Dashboard": "dashboard",
    "📝 Data Input": "page_data_input",
    "⚙️ Configure & Generate": "page_configure_generate",
    "📊 View & Export": "page_view_export",
    "💾 Saved Timetables": "page_saved_timetables",
    "📊 Timetable Views": "page_timetable_views",
    "📈 Analytics": "page_analytics",
    "👥 User Management": "page_user_management",
    "📊 System Stats": "page_system_stats",
    "📝 Activity Logs": "page_activity_logs",
    "🔑 Login": "login"
}

page_display_names = list(PAGE_MAP.keys())

# Get current page from query params
current_page_param = params.get("page", ["login"])[0]
try:
    current_index = list(PAGE_MAP.values()).index(current_page_param)
    default_index = current_index
except ValueError:
    default_index = 0

selected_page = st.radio(
    "🎯 Navigation", 
    page_display_names, 
    index=default_index,
    key="nav_radio"
)

# Handle navigation when selection changes
if PAGE_MAP[selected_page] != current_page_param:
    st.query_params.update({"page": PAGE_MAP[selected_page]})
    st.rerun()

# --- Page execution ---
if current_page is not None and hasattr(current_page, "main"):
    current_page.main()
else:
    st.error("Requested page is not available or does not have a `main()` function.")

# --- Footer ---
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.85rem;'>
        © 2025 Timetable Generator | Developed with Streamlit & Genetic Algorithms
    </div>
    """,
    unsafe_allow_html=True
)
