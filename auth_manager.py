"""
Authentication Manager - Session and user management utilities
Works with auth_database.py for authentication logic
"""

import streamlit as st
from typing import Optional, Dict
import socket


def get_client_ip() -> str:
    """Get client IP address (best effort)"""
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "Unknown"


def check_authentication() -> bool:
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)


def get_current_user() -> Optional[Dict]:
    """Get current logged-in user details"""
    if check_authentication():
        return {
            'user_id': st.session_state.get('user_id'),
            'username': st.session_state.get('username'),
            'full_name': st.session_state.get('full_name'),
            'email': st.session_state.get('email'),
            'role': st.session_state.get('role')
        }
    return None


def is_admin() -> bool:
    """Check if current user is admin"""
    return check_authentication() and st.session_state.get('role') == 'admin'


def is_faculty() -> bool:
    """Check if current user is faculty"""
    return check_authentication() and st.session_state.get('role') in ['admin', 'faculty']


def login_user(auth_db, username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate user and set session state
    Returns: (success: bool, message: str)
    """
    try:
        ip_address = get_client_ip()
        success, message, user_data = auth_db.authenticate_user(username, password, ip_address)
        
        if success and user_data:
            # Set session state
            st.session_state.authenticated = True
            st.session_state.user_id = user_data['user_id']
            st.session_state.username = user_data['username']
            st.session_state.full_name = user_data['full_name']
            st.session_state.email = user_data['email']
            st.session_state.role = user_data['role']
            st.session_state.login_time = st.session_state.get('login_time', None)
            
            return True, message
        else:
            return False, message
            
    except Exception as e:
        return False, f"Login error: {str(e)}"


def logout_user(auth_db):
    """Logout user and clear session"""
    try:
        # Clear authentication state
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.full_name = None
        st.session_state.email = None
        st.session_state.role = None
        st.session_state.login_time = None
        
        # Clear any other session data
        if 'selected_timetable_id' in st.session_state:
            del st.session_state.selected_timetable_id
            
    except Exception as e:
        st.error(f"Logout error: {e}")


def require_auth(redirect: bool = True):
    """
    Decorator/function to require authentication
    Use at the top of protected pages
    """
    if not check_authentication():
        if redirect:
            st.error("🔒 Please login to access this page")
            st.stop()
        return False
    return True


def require_role(allowed_roles: list, redirect: bool = True):
    """
    Require specific role(s) to access
    allowed_roles: list of allowed role strings like ['admin', 'faculty']
    """
    if not check_authentication():
        if redirect:
            st.error("🔒 Please login to access this page")
            st.stop()
        return False
    
    current_role = st.session_state.get('role')
    if current_role not in allowed_roles:
        if redirect:
            st.error(f"🚫 Access Denied: Required role - {', '.join(allowed_roles)}")
            st.stop()
        return False
    
    return True


def prevent_url_manipulation():
    """
    Prevent direct URL access without authentication
    Place at the top of every protected page
    """
    if not check_authentication():
        st.error("🔒 Unauthorized Access: Please login first")
        st.stop()
