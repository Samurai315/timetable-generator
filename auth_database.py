"""
Authentication Database Module - Separate from main timetable database
Handles user management, sessions, and saved timetable versions
"""

import sqlite3
import bcrypt
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class AuthDatabase:
    """Independent database for authentication and saved timetables"""
    
    def __init__(self, db_name: str = "auth_timetable.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create authentication and timetable management tables"""
        
        # Users Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT,
                role TEXT CHECK(role IN ('admin', 'faculty', 'viewer')) DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        # Login Sessions Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_time TIMESTAMP,
                ip_address TEXT,
                session_token TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Saved Timetable Versions Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_timetables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_name TEXT UNIQUE NOT NULL,
                version_description TEXT,
                algorithm_used TEXT NOT NULL,
                fitness_score REAL NOT NULL,
                timetable_data TEXT NOT NULL,
                generation_config TEXT,
                metadata TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                tags TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        # Timetable Access Log Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timetable_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timetable_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                access_type TEXT CHECK(access_type IN ('view', 'export', 'delete', 'edit')),
                access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (timetable_id) REFERENCES saved_timetables(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # System Activity Log Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.conn.commit()
    
    def create_default_admin(self):
        """Create default admin user if not exists"""
        try:
            # Check if admin exists
            self.cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not self.cursor.fetchone():
                # Create admin with password 'admin123'
                password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt(rounds=12))
                self.cursor.execute('''
                    INSERT INTO users (username, password_hash, full_name, email, role, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('admin', password_hash.decode('utf-8'), 'System Administrator', 
                      'admin@timetable.edu', 'admin', 1))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error creating default admin: {e}")
            return False
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username: str, password: str, full_name: str, 
                   email: str = None, role: str = 'viewer', created_by: int = None) -> tuple[bool, str, int]:
        """
        Create new user with bcrypt password hashing
        Returns: (success, message, user_id)
        """
        try:
            # Hash password with bcrypt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
            
            self.cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash.decode('utf-8'), full_name, email, role, created_by))
            
            self.conn.commit()
            user_id = self.cursor.lastrowid
            
            # Log activity
            self.log_activity(created_by, 'create_user', 'user', user_id, 
                            f"Created user: {username} with role: {role}")
            
            return True, "User created successfully", user_id
        except sqlite3.IntegrityError:
            return False, "Username already exists", 0
        except Exception as e:
            return False, f"Error: {str(e)}", 0
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None) -> tuple[bool, str, Optional[Dict]]:
        """
        Authenticate user with bcrypt password verification
        Returns: (success, message, user_data)
        """
        try:
            self.cursor.execute('''
                SELECT id, username, password_hash, full_name, email, role, is_active
                FROM users WHERE username = ?
            ''', (username,))
            
            user = self.cursor.fetchone()
            
            if not user:
                return False, "Invalid username or password", None
            
            if not user['is_active']:
                return False, "Account is inactive. Contact administrator.", None
            
            # Verify password with bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # Update last login
                self.cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                ''', (user['id'],))
                
                # Create login session
                self.cursor.execute('''
                    INSERT INTO login_sessions (user_id, ip_address, is_active)
                    VALUES (?, ?, 1)
                ''', (user['id'], ip_address))
                
                self.conn.commit()
                
                user_data = {
                    'user_id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'role': user['role']
                }
                
                return True, "Login successful", user_data
            else:
                return False, "Invalid username or password", None
                
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        self.cursor.execute('''
            SELECT id, username, full_name, email, role, is_active, 
                   created_at, last_login
            FROM users
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        self.cursor.execute('''
            SELECT id, username, full_name, email, role, is_active, 
                   created_at, last_login
            FROM users WHERE id = ?
        ''', (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id: int, **kwargs) -> tuple[bool, str]:
        """Update user details"""
        try:
            allowed_fields = ['full_name', 'email', 'role', 'is_active']
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                return False, "No valid fields to update"
            
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]
            
            self.cursor.execute(f'''
                UPDATE users SET {set_clause} WHERE id = ?
            ''', values)
            
            self.conn.commit()
            return True, "User updated successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def update_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        """Update user password with bcrypt"""
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12))
            
            self.cursor.execute('''
                UPDATE users SET password_hash = ? WHERE id = ?
            ''', (password_hash.decode('utf-8'), user_id))
            
            self.conn.commit()
            return True, "Password updated successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def delete_user(self, user_id: int, deleted_by: int) -> tuple[bool, str]:
        """Soft delete user (deactivate)"""
        try:
            self.cursor.execute('''
                UPDATE users SET is_active = 0 WHERE id = ?
            ''', (user_id,))
            
            self.log_activity(deleted_by, 'delete_user', 'user', user_id, 
                            f"Deactivated user ID: {user_id}")
            
            self.conn.commit()
            return True, "User deactivated successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # ==================== SAVED TIMETABLES ====================
    
    def save_timetable(self, version_name: str, algorithm_used: str, fitness_score: float,
                      timetable_data: List[Dict], generation_config: Dict,
                      created_by: int, version_description: str = None,
                      metadata: Dict = None, tags: List[str] = None) -> tuple[bool, str, int]:
        """Save a timetable version"""
        try:
            timetable_json = json.dumps(timetable_data)
            config_json = json.dumps(generation_config)
            metadata_json = json.dumps(metadata) if metadata else None
            tags_json = json.dumps(tags) if tags else None
            
            self.cursor.execute('''
                INSERT INTO saved_timetables 
                (version_name, version_description, algorithm_used, fitness_score,
                 timetable_data, generation_config, metadata, created_by, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (version_name, version_description, algorithm_used, fitness_score,
                  timetable_json, config_json, metadata_json, created_by, tags_json))
            
            self.conn.commit()
            timetable_id = self.cursor.lastrowid
            
            # Log activity
            self.log_activity(created_by, 'save_timetable', 'timetable', timetable_id,
                            f"Saved timetable: {version_name}")
            
            return True, "Timetable saved successfully", timetable_id
        except sqlite3.IntegrityError:
            return False, "Version name already exists", 0
        except Exception as e:
            return False, f"Error: {str(e)}", 0
    
    def get_all_saved_timetables(self, include_inactive: bool = False) -> List[Dict]:
        """Get all saved timetables"""
        query = '''
            SELECT st.*, u.username as created_by_username, u.full_name as created_by_name
            FROM saved_timetables st
            LEFT JOIN users u ON st.created_by = u.id
        '''
        if not include_inactive:
            query += ' WHERE st.is_active = 1'
        query += ' ORDER BY st.created_at DESC'
        
        self.cursor.execute(query)
        results = []
        for row in self.cursor.fetchall():
            data = dict(row)
            # Parse JSON fields
            data['timetable_data'] = json.loads(data['timetable_data'])
            data['generation_config'] = json.loads(data['generation_config']) if data['generation_config'] else {}
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
            data['tags'] = json.loads(data['tags']) if data['tags'] else []
            results.append(data)
        return results
    
    def get_timetable_by_id(self, timetable_id: int) -> Optional[Dict]:
        """Get timetable by ID"""
        self.cursor.execute('''
            SELECT st.*, u.username as created_by_username, u.full_name as created_by_name
            FROM saved_timetables st
            LEFT JOIN users u ON st.created_by = u.id
            WHERE st.id = ?
        ''', (timetable_id,))
        
        row = self.cursor.fetchone()
        if row:
            data = dict(row)
            data['timetable_data'] = json.loads(data['timetable_data'])
            data['generation_config'] = json.loads(data['generation_config']) if data['generation_config'] else {}
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
            data['tags'] = json.loads(data['tags']) if data['tags'] else []
            return data
        return None
    
    def delete_timetable(self, timetable_id: int, deleted_by: int) -> tuple[bool, str]:
        """Soft delete timetable"""
        try:
            self.cursor.execute('''
                UPDATE saved_timetables SET is_active = 0 WHERE id = ?
            ''', (timetable_id,))
            
            self.log_activity(deleted_by, 'delete_timetable', 'timetable', timetable_id,
                            f"Deleted timetable ID: {timetable_id}")
            
            self.conn.commit()
            return True, "Timetable deleted successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def log_timetable_access(self, timetable_id: int, user_id: int, access_type: str):
        """Log timetable access"""
        try:
            self.cursor.execute('''
                INSERT INTO timetable_access_log (timetable_id, user_id, access_type)
                VALUES (?, ?, ?)
            ''', (timetable_id, user_id, access_type))
            self.conn.commit()
        except Exception as e:
            print(f"Error logging access: {e}")
    
    # ==================== ACTIVITY LOGGING ====================
    
    def log_activity(self, user_id: Optional[int], action: str, entity_type: str = None, entity_id: int = None, details: str = None):
        """Log system activity"""
        try:
            self.cursor.execute('''
                INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, entity_type, entity_id, details))
            self.conn.commit()
        except Exception as e:
            print(f"Error logging activity: {e}")

    
    def get_recent_activities(self, limit: int = 50) -> List[Dict]:
        """Get recent system activities"""
        self.cursor.execute('''
            SELECT al.*, u.username, u.full_name
            FROM activity_log al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.timestamp DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ==================== STATISTICS ====================
    
    def get_user_statistics(self) -> Dict:
        """Get user statistics"""
        self.cursor.execute('SELECT COUNT(*) as total FROM users WHERE is_active = 1')
        total_users = self.cursor.fetchone()['total']
        
        self.cursor.execute('SELECT role, COUNT(*) as count FROM users WHERE is_active = 1 GROUP BY role')
        by_role = {row['role']: row['count'] for row in self.cursor.fetchall()}
        
        return {
            'total_users': total_users,
            'by_role': by_role
        }
    
    def get_timetable_statistics(self) -> Dict:
        """Get timetable statistics"""
        self.cursor.execute('SELECT COUNT(*) as total FROM saved_timetables WHERE is_active = 1')
        total = self.cursor.fetchone()['total']
        
        self.cursor.execute('''
            SELECT algorithm_used, COUNT(*) as count 
            FROM saved_timetables WHERE is_active = 1 
            GROUP BY algorithm_used
        ''')
        by_algorithm = {row['algorithm_used']: row['count'] for row in self.cursor.fetchall()}
        
        self.cursor.execute('''
            SELECT AVG(fitness_score) as avg_fitness 
            FROM saved_timetables WHERE is_active = 1
        ''')
        avg_fitness = self.cursor.fetchone()['avg_fitness'] or 0
        
        return {
            'total_saved': total,
            'by_algorithm': by_algorithm,
            'average_fitness': avg_fitness
        }

    def create_user(self, username: str, full_name: str, email: str, password_hash: bytes, role: str = 'faculty') -> bool:
        """Create a new user account"""
        try:
            self.cursor.execute("""
                INSERT INTO users (username, full_name, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (username, full_name, email, password_hash, role, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        try:
            self.cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    def update_password(self, user_id: int, new_password_hash: bytes) -> bool:
        """Update user password"""
        try:
            self.cursor.execute("""
                UPDATE users 
                SET password_hash = ?, updated_at = ?
                WHERE id = ?
            """, (new_password_hash, datetime.now().isoformat(), user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    def get_user_by_username(self, username: str):
        """Fetch a user by username"""
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
