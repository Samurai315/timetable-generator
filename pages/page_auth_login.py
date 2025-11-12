"""
Enhanced Login Page with Registration and Forgot Password
"""

import streamlit as st
from auth_database import AuthDatabase
from auth_manager import login_user, check_authentication, get_client_ip
import bcrypt
from datetime import datetime

# Check if already authenticated
if 'authenticated' in st.session_state and st.session_state.authenticated:
    st.switch_page("pages/page_dashboard.py")


st.title("🔐Login - Timetable Generator")
    

# Initialize auth database
if 'auth_db' not in st.session_state:
    st.session_state.auth_db = AuthDatabase()
    st.session_state.auth_db.connect()
    st.session_state.auth_db.create_tables()
    st.session_state.auth_db.create_default_admin()

auth_db = st.session_state.auth_db

# Custom CSS
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 30px;
        background-color: #f0f2f6;
        border-radius: 5px;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 5px;
        font-weight: 600;
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

# Tabs for Login, Register, Forgot Password
tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Register", "🔓 Forgot Password"])

# ==================== LOGIN TAB ====================
with tab1:
    st.markdown("### Login to Your Account")
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            login_button = st.form_submit_button("🔓 Login", use_container_width=True)
        with col2:
            remember_me = st.checkbox("Remember", value=False)
        
        if login_button:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                with st.spinner("Authenticating..."):
                    # Authenticate user
                    user = auth_db.get_user_by_username(username)
                    
                    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):

                        # Successful login
                        st.session_state.authenticated = True
                        st.session_state.current_user = dict(user)
                        
                        # Log activity
                        auth_db.log_activity(
                            user_id=user['id'],
                            action="login",
                            details=f"User logged in from {get_client_ip()}",
                            #ip_address=get_client_ip()
                        )
                        
                        # Update last login
                        auth_db.cursor.execute(
                            "UPDATE users SET last_login = ? WHERE id = ?",
                            (datetime.now().isoformat(), user['id'])
                        )
                        auth_db.conn.commit()
                        
                        st.success(f"✅ Welcome back, {user['full_name']}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
    
    # Default credentials info
    st.markdown("""
    <div class="info-box">
        <strong>📌 Default Admin Credentials</strong><br>
        <strong>Username:</strong> admin<br>
        <strong>Password:</strong> admin123<br>
        <small>⚠️ Please change the default password after first login</small>
    </div>
    """, unsafe_allow_html=True)

# ==================== REGISTER TAB ====================
with tab2:
    st.markdown("### Create New Account")
    
    with st.form("register_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            reg_username = st.text_input("Username*", placeholder="Choose a unique username")
            reg_fullname = st.text_input("Full Name*", placeholder="Enter your full name")
        
        with col2:
            reg_email = st.text_input("Email*", placeholder="your.email@example.com")
            reg_role = st.selectbox("Role*", ["faculty", "viewer"], index=0)
        
        reg_password = st.text_input("Password*", type="password", placeholder="Choose a strong password")
        reg_confirm = st.text_input("Confirm Password*", type="password", placeholder="Re-enter password")
        
        register_button = st.form_submit_button("✨ Create Account", use_container_width=True)
        
        if register_button:
            # Validation
            if not all([reg_username, reg_fullname, reg_email, reg_password, reg_confirm]):
                st.error("⚠️ Please fill in all required fields")
            elif reg_password != reg_confirm:
                st.error("⚠️ Passwords do not match")
            elif len(reg_password) < 6:
                st.error("⚠️ Password must be at least 6 characters long")
            elif auth_db.get_user_by_username(reg_username):
                st.error("⚠️ Username already exists. Please choose another.")
            elif auth_db.get_user_by_email(reg_email):
                st.error("⚠️ Email already registered. Please use another email.")
            else:
                # Create user
                try:
                    hashed_password = bcrypt.hashpw(reg_password.encode('utf-8'), bcrypt.gensalt())
                    success = auth_db.create_user(
                        username=reg_username,
                        full_name=reg_fullname,
                        email=reg_email,
                        password_hash=hashed_password,
                        role=reg_role
                    )
                    
                    if success:
                        st.success("✅ Registration successful! You can now log in.")
                        st.balloons()
                    else:
                        st.error("❌ Registration failed. Please try again.")
                except Exception as e:
                    st.error(f"❌ Error during registration: {str(e)}")
    
    st.info("💡 **Note:** New accounts are created with limited permissions. Contact admin for role changes.")

# ==================== FORGOT PASSWORD TAB ====================
with tab3:
    st.markdown("### Reset Your Password")
    
    # Step 1: Verify user
    if 'reset_user' not in st.session_state:
        st.session_state.reset_user = None
    
    if st.session_state.reset_user is None:
        with st.form("verify_user_form"):
            username_or_email = st.text_input("Username or Email", placeholder="Enter your username or email")
            verify_button = st.form_submit_button("🔍 Verify Account", use_container_width=True)
            
            if verify_button:
                if not username_or_email:
                    st.error("⚠️ Please enter your username or email")
                else:
                    # Check if user exists
                    user = auth_db.get_user_by_username(username_or_email)
                    if not user:
                        user = auth_db.get_user_by_email(username_or_email)
                    
                    if user:
                        st.session_state.reset_user = dict(user)
                        st.success(f"✅ Account found: {user['full_name']}")
                        st.rerun()
                    else:
                        st.error("❌ No account found with that username or email")
    
    else:
        # Step 2: Reset password
        user = st.session_state.reset_user
        st.info(f"🔄 Resetting password for: **{user['full_name']}** ({user['username']})")
        
        with st.form("reset_password_form"):
            new_password = st.text_input("New Password*", type="password", placeholder="Enter new password")
            confirm_new = st.text_input("Confirm New Password*", type="password", placeholder="Re-enter new password")
            
            col1, col2 = st.columns(2)
            with col1:
                reset_button = st.form_submit_button("🔄 Reset Password", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if reset_button:
                if not new_password or not confirm_new:
                    st.error("⚠️ Please fill in both password fields")
                elif new_password != confirm_new:
                    st.error("⚠️ Passwords do not match")
                elif len(new_password) < 6:
                    st.error("⚠️ Password must be at least 6 characters long")
                else:
                    try:
                        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                        auth_db.update_password(user['id'], hashed_password)
                        
                        # Log activity
                        auth_db.log_activity(
                            user_id=user['id'],
                            action="password_reset",
                            details="Password reset successful",
                            ip_address=get_client_ip()
                        )
                        
                        st.success("✅ Password updated successfully! You can now log in with your new password.")
                        st.session_state.reset_user = None
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Error resetting password: {str(e)}")
            
            if cancel_button:
                st.session_state.reset_user = None
                st.rerun()
        
        st.warning("⚠️ **Security Note:** In production, password reset should be done via email verification.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    © 2025 Timetable Generator System | Secure Access with Bcrypt Encryption
</div>
""", unsafe_allow_html=True)
