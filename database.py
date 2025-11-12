import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_name: str = "timetable.db"):
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
        """Create all required tables with proper schema"""
        # College Information Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS college (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                max_periods_per_day INTEGER NOT NULL,
                current_semester TEXT CHECK(current_semester IN ('odd', 'even')),
                working_days TEXT NOT NULL,
                time_slots TEXT NOT NULL,
                number_of_periods INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Departments Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                hod_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Classrooms Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT UNIQUE NOT NULL,
                room_name TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                floor TEXT,
                building TEXT,
                facilities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Computer Labs Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS computer_labs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_code TEXT UNIQUE NOT NULL,
                lab_name TEXT NOT NULL,
                lab_type TEXT,
                computer_capacity INTEGER NOT NULL,
                floor TEXT,
                building TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Faculty Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_code TEXT UNIQUE NOT NULL,
                faculty_name TEXT NOT NULL,
                department_id INTEGER,
                designation TEXT,
                email TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            )
        ''')

        # Programs Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_code TEXT UNIQUE NOT NULL,
                program_name TEXT NOT NULL,
                duration INTEGER NOT NULL,
                department_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            )
        ''')

        # Batches/Classes Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_code TEXT UNIQUE NOT NULL,
                batch_name TEXT NOT NULL,
                program_id INTEGER,
                year INTEGER NOT NULL,
                section TEXT,
                number_of_students INTEGER NOT NULL,
                semester INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (program_id) REFERENCES programs(id)
            )
        ''')

        # Subjects Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_code TEXT UNIQUE NOT NULL,
                subject_name TEXT NOT NULL,
                subject_type TEXT CHECK(subject_type IN ('theory', 'practical')),
                credits INTEGER NOT NULL,
                theory_hours INTEGER DEFAULT 0,
                lab_hours INTEGER DEFAULT 0,
                department_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            )
        ''')

        # Subject Allocation Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subject_allocation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,
                subject_id INTEGER,
                faculty_id INTEGER,
                semester INTEGER NOT NULL,
                academic_year TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id),
                UNIQUE(batch_id, subject_id, semester, academic_year)
            )
        ''')

        # Fixed/Static Slots Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fixed_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,
                day TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                subject_id INTEGER,
                faculty_id INTEGER,
                room_id INTEGER,
                room_type TEXT CHECK(room_type IN ('classroom', 'lab')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id)
            )
        ''')

        # Generated Timetable Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,
                day TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                subject_id INTEGER,
                faculty_id INTEGER,
                room_id INTEGER,
                room_type TEXT CHECK(room_type IN ('classroom', 'lab')),
                is_fixed BOOLEAN DEFAULT 0,
                generation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fitness_score REAL,
                FOREIGN KEY (batch_id) REFERENCES batches(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                FOREIGN KEY (faculty_id) REFERENCES faculty(id)
            )
        ''')

        # Constraints Configuration Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS constraints_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                constraint_name TEXT UNIQUE NOT NULL,
                constraint_type TEXT CHECK(constraint_type IN ('hard', 'soft')),
                is_enabled BOOLEAN DEFAULT 1,
                weight REAL DEFAULT 1.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def initialize_default_constraints(self):
        """Initialize default constraint configurations with ALL constraints"""
        default_constraints = [
            # HARD CONSTRAINTS
            ('no_faculty_conflict', 'hard', 1, 10.0, 'Faculty cannot teach multiple classes simultaneously'),
            ('no_batch_conflict', 'hard', 1, 10.0, 'Batch cannot attend multiple classes simultaneously'),
            ('no_room_conflict', 'hard', 1, 10.0, 'Room cannot be used for multiple classes simultaneously'),
            ('respect_fixed_slots', 'hard', 1, 10.0, 'Honor manually defined fixed slots'),
            ('room_capacity', 'hard', 1, 8.0, 'Room capacity must accommodate batch size'),

            # SOFT CONSTRAINTS
            ('weekly_hours_met', 'soft', 1, 5.0, 'Meet required weekly hours for each subject'),
            ('balanced_faculty_load', 'soft', 1, 3.0, 'Distribute load evenly among faculty'),
            ('minimize_faculty_gaps', 'soft', 1, 2.0, 'Minimize idle periods between classes for faculty'),
            ('minimize_batch_gaps', 'soft', 1, 2.0, 'Minimize idle periods between classes for batches'),
            ('consecutive_lab_hours', 'soft', 1, 4.0, 'Schedule lab sessions in consecutive slots'),
            ('lab_alternation', 'soft', 1, 3.0, 'Alternate labs across different days'),
            ('no_morning_gaps', 'soft', 1, 3.5, 'Avoid gaps in morning schedule'),
            ('avoid_consecutive_same_type', 'soft', 1, 2.5, 'Avoid consecutive theory or lab sessions'),
            ('interest_based_scheduling', 'soft', 1, 2.0, 'Schedule based on student engagement patterns'),
            ('priority_bias_scheduling', 'soft', 1, 3.0, 'Prioritize important subjects in better time slots'),
            ('minimize_gaps', 'soft', 1, 2.5, 'General gap minimization across timetable'),
        ]

        for constraint in default_constraints:
            self.cursor.execute('''
                INSERT OR IGNORE INTO constraints_config 
                (constraint_name, constraint_type, is_enabled, weight, description)
                VALUES (?, ?, ?, ?, ?)
            ''', constraint)

        self.conn.commit()


    
    def insert_college(self, data: Dict[str, Any]) -> int:
        """Insert college information"""
        self.cursor.execute('''
            INSERT INTO college (name, academic_year, max_periods_per_day, 
                                current_semester, working_days, time_slots, number_of_periods)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'], data['academic_year'], data['max_periods_per_day'],
            data['current_semester'], json.dumps(data['working_days']),
            json.dumps(data['time_slots']), data['number_of_periods']
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_department(self, code: str, name: str, hod_name: str = None) -> int:
        """Insert department"""
        self.cursor.execute('''
            INSERT INTO departments (code, name, hod_name)
            VALUES (?, ?, ?)
        ''', (code, name, hod_name))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_classroom(self, data: Dict[str, Any]) -> int:
        """Insert classroom"""
        self.cursor.execute('''
            INSERT INTO classrooms (room_code, room_name, capacity, floor, building, facilities)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['room_code'], data['room_name'], data['capacity'],
            data.get('floor', ''), data.get('building', ''), data.get('facilities', '')
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_lab(self, data: Dict[str, Any]) -> int:
        """Insert computer lab"""
        self.cursor.execute('''
            INSERT INTO computer_labs (lab_code, lab_name, lab_type, computer_capacity, floor, building)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['lab_code'], data['lab_name'], data.get('lab_type', ''),
            data['computer_capacity'], data.get('floor', ''), data.get('building', '')
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_faculty(self, data: Dict[str, Any]) -> int:
        """Insert faculty member"""
        self.cursor.execute('''
            INSERT INTO faculty (faculty_code, faculty_name, department_id, designation, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['faculty_code'], data['faculty_name'], data.get('department_id'),
            data.get('designation', ''), data.get('email', ''), data.get('phone', '')
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_program(self, data: Dict[str, Any]) -> int:
        """Insert program"""
        self.cursor.execute('''
            INSERT INTO programs (program_code, program_name, duration, department_id)
            VALUES (?, ?, ?, ?)
        ''', (data['program_code'], data['program_name'], data['duration'], data.get('department_id')))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_batch(self, data: Dict[str, Any]) -> int:
        """Insert batch/class"""
        self.cursor.execute('''
            INSERT INTO batches (batch_code, batch_name, program_id, year, section, number_of_students, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['batch_code'], data['batch_name'], data.get('program_id'),
            data['year'], data.get('section', ''), data['number_of_students'], data['semester']
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_subject(self, data: Dict[str, Any]) -> int:
        """Insert subject"""
        self.cursor.execute('''
            INSERT INTO subjects (subject_code, subject_name, subject_type, credits, 
                                theory_hours, lab_hours, department_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['subject_code'], data['subject_name'], data['subject_type'],
            data['credits'], data.get('theory_hours', 0), data.get('lab_hours', 0),
            data.get('department_id')
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_subject_allocation(self, batch_id: int, subject_id: int, faculty_id: int, 
                                  semester: int, academic_year: str) -> int:
        """Insert subject allocation"""
        self.cursor.execute('''
            INSERT INTO subject_allocation (batch_id, subject_id, faculty_id, semester, academic_year)
            VALUES (?, ?, ?, ?, ?)
        ''', (batch_id, subject_id, faculty_id, semester, academic_year))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_fixed_slot(self, data: Dict[str, Any]) -> int:
        """Insert fixed/static slot"""
        self.cursor.execute('''
            INSERT INTO fixed_slots (batch_id, day, time_slot, subject_id, faculty_id, room_id, room_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['batch_id'], data['day'], data['time_slot'], data.get('subject_id'),
            data.get('faculty_id'), data.get('room_id'), data.get('room_type')
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_all(self, table_name: str) -> List[Dict]:
        """Get all records from a table"""
        self.cursor.execute(f'SELECT * FROM {table_name}')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_by_id(self, table_name: str, record_id: int) -> Optional[Dict]:
        """Get a record by ID"""
        self.cursor.execute(f'SELECT * FROM {table_name} WHERE id = ?', (record_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def delete_by_id(self, table_name: str, record_id: int):
        """Delete a record by ID"""
        self.cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (record_id,))
        self.conn.commit()
    
    def clear_generated_timetable(self):
        """Clear all generated timetable entries"""
        self.cursor.execute('DELETE FROM generated_timetable')
        self.conn.commit()
    
    def save_generated_timetable(self, timetable_data: List[Dict[str, Any]], fitness_score: float):
        """Save generated timetable to database"""
        self.clear_generated_timetable()
        
        for slot in timetable_data:
            self.cursor.execute('''
                INSERT INTO generated_timetable 
                (batch_id, day, time_slot, subject_id, faculty_id, room_id, room_type, is_fixed, fitness_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                slot['batch_id'], slot['day'], slot['time_slot'], slot['subject_id'],
                slot['faculty_id'], slot.get('room_id'), slot.get('room_type'),
                slot.get('is_fixed', 0), fitness_score
            ))
        
        self.conn.commit()
    
    def get_generated_timetable(self, batch_id: Optional[int] = None) -> List[Dict]:
        """Retrieve generated timetable"""
        if batch_id:
            self.cursor.execute('SELECT * FROM generated_timetable WHERE batch_id = ?', (batch_id,))
        else:
            self.cursor.execute('SELECT * FROM generated_timetable')
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_constraint(self, constraint_name: str, is_enabled: bool, weight: float):
        """Update constraint configuration"""
        self.cursor.execute('''
            UPDATE constraints_config 
            SET is_enabled = ?, weight = ?
            WHERE constraint_name = ?
        ''', (is_enabled, weight, constraint_name))
        self.conn.commit()
    
    def get_constraints(self) -> List[Dict]:
        """Get all constraint configurations"""
        self.cursor.execute('SELECT * FROM constraints_config')
        return [dict(row) for row in self.cursor.fetchall()]
