import random
import json
from typing import List, Dict, Tuple, Optional, Callable, Set
from database import Database
from collections import defaultdict
import time

class TimetableCSP:
    """
    Enhanced CSP solver with:
    1. Day divided into 3 slots (morning, noon, late-noon)
    2. Only one type (theory/practical) per slot per batch
    3. Strict fixed slot preservation
    4. Chronological slot assignment (morning to evening)
    5. No free periods between consecutive classes
    6. Soft preference: avoid theory subject repetition on same day
    """
    def __init__(self, db: Database, selected_batches: List[int],
                 use_fixed_slots: bool = True,
                 max_iterations: int = 10000,
                 use_min_conflicts: bool = False):
        """Initialize CSP solver"""
        self.db = db
        self.selected_batches = selected_batches
        self.use_fixed_slots = use_fixed_slots
        self.max_iterations = max_iterations
        self.use_min_conflicts = use_min_conflicts
        
        # Load data
        self._load_data()
        
        # Define day slots (morning, noon, late-noon)
        self._define_day_slots()
        
        # CSP components
        self.slots = []
        self.assignments = []
        self.solution = []
        
        # Tracking for constraints
        self.fixed_assignments_set = set()
        
        # Initialize
        self._prepare_slots()
        self._prepare_assignments()
    
    def _load_data(self):
        """Load all necessary data from database"""
        colleges = self.db.get_all('college')
        if not colleges:
            raise ValueError("No college information found.")
        
        self.college_info = colleges[0]
        self.working_days = json.loads(self.college_info['working_days'])
        self.time_slots = json.loads(self.college_info['time_slots'])
        
        all_batches = self.db.get_all('batches')
        self.batches = {b['id']: b for b in all_batches if b['id'] in self.selected_batches}
        if not self.batches:
            raise ValueError(f"No batches found for IDs: {self.selected_batches}")
        
        all_allocations = self.db.get_all('subject_allocation')
        self.allocations = [a for a in all_allocations if a['batch_id'] in self.selected_batches]
        if not self.allocations:
            raise ValueError("No subject allocations found for selected batches.")
        
        self.subjects = {s['id']: s for s in self.db.get_all('subjects')}
        self.faculty = {f['id']: f for f in self.db.get_all('faculty')}
        self.classrooms = self.db.get_all('classrooms')
        self.labs = self.db.get_all('computer_labs')
        
        if not self.classrooms:
            raise ValueError("No classrooms found.")
        
        if self.use_fixed_slots:
            all_fixed = self.db.get_all('fixed_slots')
            self.fixed_slots = [fs for fs in all_fixed if fs['batch_id'] in self.selected_batches]
        else:
            self.fixed_slots = []
        
        # Get constraints with weights
        constraints = self.db.get_constraints()
        self.constraint_config = {c['constraint_name']: {
            'enabled': c['is_enabled'],
            'weight': c['weight'],
            'type': c['constraint_type']
        } for c in constraints}
    
    def _define_day_slots(self):
        """Define day divisions: morning, noon, late-noon"""
        num_periods = len(self.time_slots)
        
        # Divide day into 3 equal slots
        morning_end = num_periods // 3
        noon_end = (num_periods * 2) // 3
        
        self.slot_divisions = {
            'morning': list(range(0, morning_end)),
            'noon': list(range(morning_end, noon_end)),
            'late_noon': list(range(noon_end, num_periods))
        }
    
    def _get_time_slot_division(self, time_slot: str) -> str:
        """Get which division (morning/noon/late_noon) a time slot belongs to"""
        try:
            time_idx = self.time_slots.index(time_slot)
            for division, indices in self.slot_divisions.items():
                if time_idx in indices:
                    return division
        except ValueError:
            pass
        return 'unknown'
    
    def _prepare_slots(self):
        """Prepare all available time slots in CHRONOLOGICAL order"""
        self.slots = []
        
        # Create day order mapping
        day_order = {day: idx for idx, day in enumerate(self.working_days)}
        
        # Generate all slots
        for day in self.working_days:
            for time in self.time_slots:
                self.slots.append((day, time))
        
        # Sort chronologically (day order, then time order)
        self.slots.sort(key=lambda x: (
            day_order.get(x[0], 999),
            self.time_slots.index(x[1]) if x[1] in self.time_slots else 999
        ))
    
    def _prepare_assignments(self):
        """Prepare list of all assignments with priority ordering"""
        temp_assignments = []
        
        for alloc in self.allocations:
            if alloc['subject_id'] not in self.subjects:
                continue
            if alloc['batch_id'] not in self.batches:
                continue
            
            subject = self.subjects[alloc['subject_id']]
            batch_id = alloc['batch_id']
            subject_id = alloc['subject_id']
            faculty_id = alloc['faculty_id']
            
            # Check if this is a fixed assignment
            is_fixed = any(
                fs['batch_id'] == batch_id and
                fs['subject_id'] == subject_id and
                fs['faculty_id'] == faculty_id
                for fs in self.fixed_slots
            )
            
            if is_fixed:
                # Mark as fixed, will be applied separately
                self.fixed_assignments_set.add((batch_id, subject_id, faculty_id))
                continue
            
            # Theory slots
            theory_hours = subject.get('theory_hours', 0)
            for i in range(theory_hours):
                temp_assignments.append({
                    'batch_id': batch_id,
                    'subject_id': subject_id,
                    'faculty_id': faculty_id,
                    'type': 'theory',
                    'duration': 1,
                    'index': i,
                    'priority': subject.get('credits', 3)
                })
            
            # Lab slots (consecutive)
            lab_hours = subject.get('lab_hours', 0)
            if lab_hours > 0:
                temp_assignments.append({
                    'batch_id': batch_id,
                    'subject_id': subject_id,
                    'faculty_id': faculty_id,
                    'type': 'lab',
                    'duration': lab_hours,
                    'index': 0,
                    'priority': subject.get('credits', 3) + 2
                })
        
        # Sort by priority (descending)
        self.assignments = sorted(temp_assignments, key=lambda x: (-x['priority'], -x['duration']))
    
    def _get_available_rooms(self, slot_type: str, batch_size: int = 0) -> List[Dict]:
        """Get available rooms for slot type with capacity check"""
        if slot_type == 'lab':
            rooms = self.labs if self.labs else self.classrooms
        else:
            rooms = self.classrooms
        
        # Filter by capacity
        if self.constraint_config.get('room_capacity', {}).get('enabled', True):
            rooms = [r for r in rooms if r.get('capacity', 999) >= batch_size or
                     r.get('computer_capacity', 999) >= batch_size]
        
        return rooms
    
    def _find_consecutive_slots(self, start_day: str, start_time: str, duration: int) -> List[Tuple[str, str]]:
        """Find consecutive time slots starting from given slot"""
        try:
            day_idx = self.working_days.index(start_day)
            time_idx = self.time_slots.index(start_time)
        except ValueError:
            return []
        
        consecutive = []
        for i in range(duration):
            if time_idx + i < len(self.time_slots):
                consecutive.append((start_day, self.time_slots[time_idx + i]))
            else:
                return []
        
        return consecutive
    
    def _check_slot_type_constraint(self, assignment: Dict, slot: Tuple[str, str],
                                     current_solution: List[Dict]) -> bool:
        """
        Check if slot division already has a different type assigned
        Returns True if constraint violated (conflict exists)
        """
        day, time = slot
        batch_id = assignment['batch_id']
        assignment_type = assignment['type']
        
        # Get the division this slot belongs to
        division = self._get_time_slot_division(time)
        
        # Check all existing assignments for this batch on this day
        for entry in current_solution:
            if entry['batch_id'] == batch_id and entry['day'] == day:
                entry_time = entry['time_slot']
                entry_division = self._get_time_slot_division(entry_time)
                
                # Same division?
                if entry_division == division:
                    # Check type
                    entry_subject = self.subjects.get(entry['subject_id'], {})
                    entry_type = entry_subject.get('subject_type', 'theory')
                    
                    # If types differ, constraint violated
                    if assignment_type == 'theory' and entry_type == 'practical':
                        return True
                    if assignment_type == 'lab' and entry_type == 'theory':
                        return True
        
        return False
    
    def _check_consecutive_free_period(self, assignment: Dict, slot: Tuple[str, str],
                                        current_solution: List[Dict]) -> bool:
        """
        Check if adding this creates a free period between classes
        Returns True if constraint violated
        """
        day, time = slot
        batch_id = assignment['batch_id']
        
        try:
            time_idx = self.time_slots.index(time)
        except ValueError:
            return False
        
        # Get all scheduled times for this batch on this day
        batch_day_times = []
        for entry in current_solution:
            if entry['batch_id'] == batch_id and entry['day'] == day:
                try:
                    t_idx = self.time_slots.index(entry['time_slot'])
                    batch_day_times.append(t_idx)
                except ValueError:
                    pass
        
        if not batch_day_times:
            return False
        
        batch_day_times.sort()
        
        # Check if adding current time creates gaps
        all_times = sorted(batch_day_times + [time_idx])
        for i in range(len(all_times) - 1):
            gap = all_times[i + 1] - all_times[i]
            if gap > 1:  # Gap detected
                return True
        
        return False
    
    def _check_hard_constraints(self, assignment: Dict, slot: Tuple[str, str],
                                 room_id: int, current_solution: List[Dict]) -> bool:
        """Check all HARD constraints - returns True if conflict exists"""
        day, time = slot
        batch_id = assignment['batch_id']
        faculty_id = assignment['faculty_id']
        duration = assignment['duration']
        batch_size = self.batches[batch_id]['number_of_students']
        
        # Get slots this assignment will occupy
        if duration == 1:
            occupied_slots = [slot]
        else:
            occupied_slots = self._find_consecutive_slots(day, time, duration)
            if not occupied_slots:
                return True
        
        # Check against existing solution (INCLUDING FIXED SLOTS)
        for entry in current_solution:
            entry_day = entry['day']
            entry_time = entry['time_slot']
            entry_batch = entry['batch_id']
            entry_faculty = entry['faculty_id']
            entry_room = entry['room_id']
            
            # Check if slots overlap
            if (entry_day, entry_time) in occupied_slots:
                # 1. Faculty conflict
                if self.constraint_config.get('no_faculty_conflict', {}).get('enabled', True):
                    if faculty_id == entry_faculty:
                        return True
                
                # 2. Batch conflict
                if self.constraint_config.get('no_batch_conflict', {}).get('enabled', True):
                    if batch_id == entry_batch:
                        return True
                
                # 3. Room conflict
                if self.constraint_config.get('no_room_conflict', {}).get('enabled', True):
                    if room_id == entry_room:
                        return True
        
        # 4. Room capacity check
        if self.constraint_config.get('room_capacity', {}).get('enabled', True):
            room = next((r for r in self.classrooms + self.labs if r['id'] == room_id), None)
            if room:
                capacity = room.get('capacity', room.get('computer_capacity', 0))
                if capacity < batch_size:
                    return True
        
        # 5. Slot type constraint (one type per division)
        if self._check_slot_type_constraint(assignment, slot, current_solution):
            return True
        
        # 6. No free periods between consecutive classes
        if self._check_consecutive_free_period(assignment, slot, current_solution):
            return True
        
        # NOTE: Subject repetition moved to SOFT constraint (penalty-based)
        
        return False
    
    def _calculate_soft_constraint_penalty(self, assignment: Dict, slot: Tuple[str, str],
                                            current_solution: List[Dict]) -> float:
        """Calculate penalty score for soft constraints (lower is better)"""
        penalty = 0.0
        day, time = slot
        batch_id = assignment['batch_id']
        faculty_id = assignment['faculty_id']
        subject_id = assignment['subject_id']
        
        try:
            time_idx = self.time_slots.index(time)
        except ValueError:
            time_idx = 0
        
        # 1. Priority bias scheduling (better slots for important subjects)
        if self.constraint_config.get('priority_bias_scheduling', {}).get('enabled', True):
            credits = self.subjects.get(subject_id, {}).get('credits', 3)
            
            # Morning slots preferred for high-credit courses
            division = self._get_time_slot_division(time)
            if credits >= 4 and division == 'late_noon':
                penalty += self.constraint_config.get('priority_bias_scheduling', {}).get('weight', 3.0)
        
        # 2. Lab alternation
        if self.constraint_config.get('lab_alternation', {}).get('enabled', True):
            if assignment['type'] == 'lab':
                lab_count_today = sum(1 for e in current_solution
                                       if e['day'] == day and e['batch_id'] == batch_id
                                       and self.subjects.get(e['subject_id'], {}).get('subject_type') == 'practical')
                if lab_count_today > 0:
                    penalty += lab_count_today * self.constraint_config.get('lab_alternation', {}).get('weight', 3.0)
        
        # 3. Minimize faculty gaps
        if self.constraint_config.get('minimize_faculty_gaps', {}).get('enabled', True):
            faculty_day_schedule = [e for e in current_solution
                                     if e['day'] == day and e['faculty_id'] == faculty_id]
            if faculty_day_schedule:
                time_indices = [self.time_slots.index(e['time_slot']) for e in faculty_day_schedule]
                for t_idx in time_indices:
                    gap = abs(time_idx - t_idx)
                    if gap > 1:
                        penalty += (gap - 1) * self.constraint_config.get('minimize_faculty_gaps', {}).get('weight', 2.0) * 0.5
        
        # 4. SOFT CONSTRAINT: Heavy penalty for same-day theory repetition
        if assignment['type'] == 'theory':
            same_day_theory_count = sum(1 for e in current_solution
                                        if e['batch_id'] == batch_id and
                                           e['day'] == day and
                                           e['subject_id'] == subject_id and
                                           e.get('room_type') == 'classroom')
            if same_day_theory_count > 0:
                # Heavy penalty (50 points per repetition) but NOT blocking
                penalty += 50.0 * same_day_theory_count
        
        # 5. Prefer earlier slots (chronological progression)
        penalty += time_idx * 0.1
        
        return penalty
    
    def _select_best_slot_lcv(self, assignment: Dict, valid_slots: List[Tuple[Tuple[str, str], Dict]],
                               current_solution: List[Dict]) -> Tuple[Tuple[str, str], Dict]:
        """Least Constraining Value heuristic with chronological preference"""
        if not valid_slots:
            return None, None
        
        slot_scores = []
        for slot, room in valid_slots:
            penalty = self._calculate_soft_constraint_penalty(assignment, slot, current_solution)
            slot_scores.append((penalty, slot, room))
        
        # Sort by penalty (lower is better)
        slot_scores.sort(key=lambda x: x[0])
        return slot_scores[0][1], slot_scores[0][2]
    
    def _assign_slot(self, assignment: Dict, slot: Tuple[str, str], room: Dict) -> List[Dict]:
        """Create timetable entries for an assignment"""
        day, time = slot
        duration = assignment['duration']
        entries = []
        
        if duration == 1:
            entries.append({
                'batch_id': assignment['batch_id'],
                'day': day,
                'time_slot': time,
                'subject_id': assignment['subject_id'],
                'faculty_id': assignment['faculty_id'],
                'room_id': room['id'],
                'room_type': 'lab' if assignment['type'] == 'lab' else 'classroom',
                'is_fixed': False
            })
        else:
            consecutive_slots = self._find_consecutive_slots(day, time, duration)
            for slot_day, slot_time in consecutive_slots:
                entries.append({
                    'batch_id': assignment['batch_id'],
                    'day': slot_day,
                    'time_slot': slot_time,
                    'subject_id': assignment['subject_id'],
                    'faculty_id': assignment['faculty_id'],
                    'room_id': room['id'],
                    'room_type': 'lab' if assignment['type'] == 'lab' else 'classroom',
                    'is_fixed': False
                })
        
        return entries
    
    def _apply_fixed_slots(self):
        """Apply fixed slots to solution EXACTLY as defined"""
        fixed_solution = []
        
        for fixed in self.fixed_slots:
            room_id = fixed['room_id']
            room_type = fixed['room_type']
            
            fixed_solution.append({
                'batch_id': fixed['batch_id'],
                'day': fixed['day'],
                'time_slot': fixed['time_slot'],
                'subject_id': fixed['subject_id'],
                'faculty_id': fixed['faculty_id'],
                'room_id': room_id,
                'room_type': room_type,
                'is_fixed': True
            })
        
        return fixed_solution
    
    def _smart_solve(self, progress_callback=None) -> Optional[List[Dict]]:
        """Enhanced greedy algorithm with all constraints"""
        # START WITH FIXED SLOTS as base solution
        solution = self._apply_fixed_slots()
        
        for idx, assignment in enumerate(self.assignments):
            if progress_callback and idx % 5 == 0:
                progress = int((idx / len(self.assignments)) * 100)
                progress_callback(progress, idx, len(self.assignments))
            
            batch_size = self.batches[assignment['batch_id']]['number_of_students']
            rooms = self._get_available_rooms(assignment['type'], batch_size)
            
            # Find all valid (slot, room) combinations
            valid_combinations = []
            for slot in self.slots:  # Already sorted chronologically
                for room in rooms:
                    if not self._check_hard_constraints(assignment, slot, room['id'], solution):
                        valid_combinations.append((slot, room))
            
            if not valid_combinations:
                return None  # Failed to assign
            
            # Use LCV heuristic (now includes same-day repetition penalty)
            best_slot, best_room = self._select_best_slot_lcv(assignment, valid_combinations, solution)
            
            if best_slot and best_room:
                new_entries = self._assign_slot(assignment, best_slot, best_room)
                solution.extend(new_entries)
            else:
                return None
        
        return solution
    
    def run(self, progress_callback: Optional[Callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """Solve CSP and return timetable"""
        start_time = time.time()
        
        if progress_callback:
            progress_callback(0, 0, len(self.assignments))
        
        solution = self._smart_solve(progress_callback)
        
        if solution is None:
            raise ValueError("Failed to find valid timetable. Try relaxing constraints.")
        
        elapsed = time.time() - start_time
        history = [{
            'iteration': 0,
            'conflicts': 0,
            'time': elapsed,
            'method': 'Enhanced CSP with Soft Subject Distribution'
        }]
        
        return solution, history
