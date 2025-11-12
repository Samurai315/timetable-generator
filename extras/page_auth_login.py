"""
Login Page - Bcrypt-based authentication
Separate authentication system
"""

import streamlit as st
from auth_database import AuthDatabase
from auth_manager import login_user, check_authentication, get_client_ip

# Check if already authenticated
if check_authentication():
    st.switch_page("pages/page_dashboard.py")

st.set_page_config(
    page_title="Login - Timetable Generator",
    page_icon="🔐",
    layout="centered"
)

# Initialize auth database
if 'auth_db' not in st.session_state:
    st.session_state.auth_db = AuthDatabase()
    st.session_state.auth_db.connect()
    st.session_state.auth_db.create_tables()
    st.session_state.auth_db.create_default_admin()

auth_db = st.session_state.auth_db

# Custom CSS for login page
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 5px;
        font-weight: 600;
        margin-top: 1rem;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    .info-box {
        background: #f0f7ff;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #667eea;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🔐 Timetable Generator</h1>
    <p>Secure Authentication System</p>
</div>
""", unsafe_allow_html=True)

# Login Form
with st.container():
    st.markdown("### 👤 Login to Your Account")
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            remember_me = st.checkbox("Remember", value=False)
        
        if login_button:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                with st.spinner("Authenticating..."):
                    success, message = login_user(auth_db, username, password)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

# Default credentials info box
st.markdown("""
<div class="info-box">
    <strong>ℹ️ Default Admin Credentials</strong><br>
    <strong>Username:</strong> admin<br>
    <strong>Password:</strong> admin123<br>
    <small>⚠️ Please change the default password after first login</small>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    © 2025 Timetable Generator System | Secure Access with Bcrypt Encryption
</div>
""", unsafe_allow_html=True)
