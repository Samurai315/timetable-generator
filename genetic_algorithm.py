import random
import json
import copy
from typing import List, Dict, Tuple, Callable, Optional
from database import Database
from multiprocessing import Pool, cpu_count
import functools
from concurrent.futures import ProcessPoolExecutor
import os

# Try to import GPU version
try:
    from genetic_algorithm_gpu import GeneticAlgorithmGPU, GPU_AVAILABLE
except ImportError:
    GPU_AVAILABLE = False
    GeneticAlgorithmGPU = None

def create_genetic_algorithm(db: Database, selected_batches: List[int], use_fixed_slots: bool = True,
                            population_size: int = 100, max_generations: int = 100,
                            crossover_rate: float = 0.8, mutation_rate: float = 0.01,
                            elite_size: int = 5, tournament_size: int = 5,
                            use_multiprocessing: bool = True, use_gpu: bool = False,
                            n_workers: Optional[int] = None):
    """Factory function to create appropriate algorithm version"""
    
    if use_gpu and GPU_AVAILABLE:
        return GeneticAlgorithmGPU(
            db=db,
            selected_batches=selected_batches,
            use_fixed_slots=use_fixed_slots,
            population_size=population_size,
            max_generations=max_generations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            elite_size=elite_size,
            tournament_size=tournament_size
        )
    else:
        return GeneticAlgorithmCPUOptimized(
            db=db,
            selected_batches=selected_batches,
            use_fixed_slots=use_fixed_slots,
            population_size=population_size,
            max_generations=max_generations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            elite_size=elite_size,
            tournament_size=tournament_size,
            use_multiprocessing=use_multiprocessing,
            n_workers=n_workers
        )

# Alias for backward compatibility
class GeneticAlgorithm:
    """Backward compatible wrapper - use create_genetic_algorithm() instead"""
    def __new__(cls, *args, **kwargs):
        return create_genetic_algorithm(*args, **kwargs)

class GeneticAlgorithmCPUOptimized:
    """Fully optimized Multi-Core CPU Genetic Algorithm"""
    
    def __init__(self, db: Database, selected_batches: List[int], use_fixed_slots: bool = True,
                 population_size: int = 100, max_generations: int = 100,
                 crossover_rate: float = 0.8, mutation_rate: float = 0.01,
                 elite_size: int = 5, tournament_size: int = 5,
                 use_multiprocessing: bool = True, use_gpu: bool = False,
                 n_workers: Optional[int] = None):
        """Initialize fully optimized multi-core genetic algorithm"""
        self.db = db
        self.selected_batches = selected_batches
        self.use_fixed_slots = use_fixed_slots
        self.population_size = population_size
        self.max_generations = max_generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
        
        # Optimized parallelization settings
        self.use_multiprocessing = use_multiprocessing
        self.n_workers = n_workers or max(1, cpu_count() - 1)
        
        # Chunk size for parallel processing optimization
        self.chunk_size = max(1, self.population_size // (self.n_workers * 4))
        
        # Load data
        self._load_data()
        self._load_constraints()
        
        # Pre-compute static data for faster operations
        self._precompute_static_data()
    
    def _precompute_static_data(self):
        """Pre-compute static data to avoid repeated lookups"""
        self.day_indices = {day: idx for idx, day in enumerate(self.working_days)}
        self.time_indices = {time: idx for idx, time in enumerate(self.time_slots)}
        
        # Create lookup dicts for batch/room sizes
        self.batch_sizes = {b['id']: b['number_of_students'] for b in self.batches.values()}
        self.classroom_capacities = {r['id']: r['capacity'] for r in self.classrooms}
        self.lab_capacities = {l['id']: l['computer_capacity'] for l in self.labs}
    
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
            raise ValueError(f"No batches found for selected batch IDs: {self.selected_batches}")
        
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
        
        self.slot_requirements = []
        for alloc in self.allocations:
            if alloc['subject_id'] not in self.subjects or alloc['batch_id'] not in self.batches:
                continue
            
            subject = self.subjects[alloc['subject_id']]
            theory_slots = subject.get('theory_hours', 0)
            lab_slots = subject.get('lab_hours', 0)
            
            for _ in range(theory_slots):
                self.slot_requirements.append({
                    'batch_id': alloc['batch_id'],
                    'subject_id': alloc['subject_id'],
                    'faculty_id': alloc['faculty_id'],
                    'type': 'theory'
                })
            
            if lab_slots > 0:
                self.slot_requirements.append({
                    'batch_id': alloc['batch_id'],
                    'subject_id': alloc['subject_id'],
                    'faculty_id': alloc['faculty_id'],
                    'type': 'practical',
                    'duration': lab_slots
                })
        
        if not self.slot_requirements:
            raise ValueError("No slot requirements generated.")
    
    def _load_constraints(self):
        """Load constraint configurations"""
        constraints = self.db.get_constraints()
        self.constraints = {c['constraint_name']: c for c in constraints if c['is_enabled']}
    
    def _create_random_timetable(self) -> List[Dict]:
        """Create a random timetable chromosome"""
        timetable = []
        
        for fixed in self.fixed_slots:
            timetable.append({
                'batch_id': fixed['batch_id'],
                'day': fixed['day'],
                'time_slot': fixed['time_slot'],
                'subject_id': fixed['subject_id'],
                'faculty_id': fixed['faculty_id'],
                'room_id': fixed['room_id'],
                'room_type': fixed['room_type'],
                'is_fixed': True
            })
        
        for req in self.slot_requirements:
            if req['type'] == 'theory':
                day = random.choice(self.working_days)
                time_slot = random.choice(self.time_slots)
                room = random.choice(self.classrooms)
                
                timetable.append({
                    'batch_id': req['batch_id'],
                    'day': day,
                    'time_slot': time_slot,
                    'subject_id': req['subject_id'],
                    'faculty_id': req['faculty_id'],
                    'room_id': room['id'],
                    'room_type': 'classroom',
                    'is_fixed': False
                })
            
            elif req['type'] == 'practical':
                day = random.choice(self.working_days)
                start_idx = random.randint(0, max(0, len(self.time_slots) - req['duration']))
                
                if self.labs:
                    lab = random.choice(self.labs)
                    room_id, room_type = lab['id'], 'lab'
                else:
                    room = random.choice(self.classrooms)
                    room_id, room_type = room['id'], 'classroom'
                
                for i in range(req['duration']):
                    if start_idx + i < len(self.time_slots):
                        timetable.append({
                            'batch_id': req['batch_id'],
                            'day': day,
                            'time_slot': self.time_slots[start_idx + i],
                            'subject_id': req['subject_id'],
                            'faculty_id': req['faculty_id'],
                            'room_id': room_id,
                            'room_type': room_type,
                            'is_fixed': False
                        })
        
        return timetable
    
    def _initialize_population_parallel(self) -> List[List[Dict]]:
        """Parallel population initialization"""
        if self.use_multiprocessing and self.population_size > 100:
            try:
                with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                    population = list(executor.map(
                        lambda _: self._create_random_timetable(),
                        range(self.population_size),
                        chunksize=self.chunk_size
                    ))
                return population
            except Exception as e:
                print(f"⚠️ Parallel initialization failed: {e}. Using sequential.")
                return [self._create_random_timetable() for _ in range(self.population_size)]
        else:
            return [self._create_random_timetable() for _ in range(self.population_size)]
    
    def _calculate_fitness(self, timetable: List[Dict]) -> float:
        """Calculate fitness with pre-computed indices for speed"""
        penalty = 0.0
        
        # Build lookup tables for this timetable
        slots_by_day_time = {}
        for slot in timetable:
            day = slot['day']
            time = slot['time_slot']
            key = (day, time)
            if key not in slots_by_day_time:
                slots_by_day_time[key] = []
            slots_by_day_time[key].append(slot)
        
        # Hard Constraints - Faculty conflicts
        if 'no_faculty_conflict' in self.constraints:
            weight = self.constraints['no_faculty_conflict']['weight']
            for slots in slots_by_day_time.values():
                faculty_counts = {}
                for slot in slots:
                    fid = slot['faculty_id']
                    faculty_counts[fid] = faculty_counts.get(fid, 0) + 1
                
                for count in faculty_counts.values():
                    if count > 1:
                        penalty += weight * (count - 1)
        
        # Hard Constraints - Batch conflicts
        if 'no_batch_conflict' in self.constraints:
            weight = self.constraints['no_batch_conflict']['weight']
            for slots in slots_by_day_time.values():
                batch_counts = {}
                for slot in slots:
                    bid = slot['batch_id']
                    batch_counts[bid] = batch_counts.get(bid, 0) + 1
                
                for count in batch_counts.values():
                    if count > 1:
                        penalty += weight * (count - 1)
        
        # Hard Constraints - Room conflicts
        if 'no_room_conflict' in self.constraints:
            weight = self.constraints['no_room_conflict']['weight']
            for slots in slots_by_day_time.values():
                room_counts = {}
                for slot in slots:
                    rid = slot['room_id']
                    room_counts[rid] = room_counts.get(rid, 0) + 1
                
                for count in room_counts.values():
                    if count > 1:
                        penalty += weight * (count - 1)
        
        # Soft Constraints - Minimize faculty gaps
        if 'minimize_faculty_gaps' in self.constraints:
            weight = self.constraints['minimize_faculty_gaps']['weight']
            faculty_by_day = {}
            
            for slot in timetable:
                fid = slot['faculty_id']
                day = slot['day']
                key = (fid, day)
                if key not in faculty_by_day:
                    faculty_by_day[key] = []
                faculty_by_day[key].append(slot)
            
            for slots in faculty_by_day.values():
                if len(slots) > 1:
                    sorted_slots = sorted(slots, key=lambda x: self.time_indices.get(x['time_slot'], 0))
                    for i in range(len(sorted_slots) - 1):
                        idx1 = self.time_indices.get(sorted_slots[i]['time_slot'], 0)
                        idx2 = self.time_indices.get(sorted_slots[i + 1]['time_slot'], 0)
                        gap = idx2 - idx1 - 1
                        if gap > 0:
                            penalty += weight * gap * 0.5
        
        # Soft Constraints - Minimize batch gaps
        if 'minimize_batch_gaps' in self.constraints:
            weight = self.constraints['minimize_batch_gaps']['weight']
            batch_by_day = {}
            
            for slot in timetable:
                bid = slot['batch_id']
                day = slot['day']
                key = (bid, day)
                if key not in batch_by_day:
                    batch_by_day[key] = []
                batch_by_day[key].append(slot)
            
            for slots in batch_by_day.values():
                if len(slots) > 1:
                    sorted_slots = sorted(slots, key=lambda x: self.time_indices.get(x['time_slot'], 0))
                    for i in range(len(sorted_slots) - 1):
                        idx1 = self.time_indices.get(sorted_slots[i]['time_slot'], 0)
                        idx2 = self.time_indices.get(sorted_slots[i + 1]['time_slot'], 0)
                        gap = idx2 - idx1 - 1
                        if gap > 0:
                            penalty += weight * gap * 0.5
        
        # Soft Constraints - Balanced faculty load
        if 'balanced_faculty_load' in self.constraints:
            weight = self.constraints['balanced_faculty_load']['weight']
            faculty_daily_load = {}
            
            for slot in timetable:
                fid = slot['faculty_id']
                day = slot['day']
                key = (fid, day)
                faculty_daily_load[key] = faculty_daily_load.get(key, 0) + 1
            
            for fid in set(s['faculty_id'] for s in timetable):
                daily_loads = [faculty_daily_load.get((fid, day), 0) for day in self.working_days]
                if daily_loads and max(daily_loads) > 0:
                    avg_load = sum(daily_loads) / len(daily_loads)
                    variance = sum((load - avg_load) ** 2 for load in daily_loads) / len(daily_loads)
                    penalty += weight * variance * 0.3
        
        return 1000.0 / (1.0 + penalty)
    
    def _calculate_fitness_batch_optimized(self, timetables: List[List[Dict]]) -> List[float]:
        """Optimized parallel batch fitness calculation"""
        if not self.use_multiprocessing or len(timetables) <= 1:
            return [self._calculate_fitness(tt) for tt in timetables]
        
        try:
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                fitnesses = list(executor.map(
                    self._calculate_fitness,
                    timetables,
                    chunksize=self.chunk_size
                ))
            return fitnesses
        except Exception as e:
            print(f"⚠️ Parallel fitness calculation failed: {e}. Using sequential.")
            return [self._calculate_fitness(tt) for tt in timetables]
    
    def _parallel_crossover_mutation(self, parents: List[Tuple[List[Dict], List[Dict]]]) -> List[List[Dict]]:
        """Parallel crossover and mutation"""
        if not self.use_multiprocessing or len(parents) <= 1:
            children = []
            for parent1, parent2 in parents:
                child1, child2 = self._crossover(parent1, parent2)
                children.append(self._mutate(child1))
                if len(children) < len(parents) * 2:
                    children.append(self._mutate(child2))
            return children
        
        try:
            def process_pair(pair):
                parent1, parent2 = pair
                child1, child2 = self._crossover(parent1, parent2)
                return [self._mutate(child1), self._mutate(child2)]
            
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                results = list(executor.map(process_pair, parents, chunksize=self.chunk_size))
            
            children = []
            for pair in results:
                children.extend(pair)
            return children
        except Exception as e:
            print(f"⚠️ Parallel crossover/mutation failed: {e}. Using sequential.")
            children = []
            for parent1, parent2 in parents:
                child1, child2 = self._crossover(parent1, parent2)
                children.append(self._mutate(child1))
                if len(children) < len(parents) * 2:
                    children.append(self._mutate(child2))
            return children
    
    def _tournament_selection(self, population: List[List[Dict]], fitnesses: List[float]) -> List[Dict]:
        """Tournament selection"""
        tournament_indices = random.sample(range(len(population)), self.tournament_size)
        tournament_fitnesses = [fitnesses[i] for i in tournament_indices]
        winner_idx = tournament_indices[tournament_fitnesses.index(max(tournament_fitnesses))]
        return copy.deepcopy(population[winner_idx])
    
    def _crossover(self, parent1: List[Dict], parent2: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Uniform crossover"""
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        child1, child2 = [], []
        fixed_slots = [s for s in parent1 if s.get('is_fixed', False)]
        parent1_nonfixed = [s for s in parent1 if not s.get('is_fixed', False)]
        parent2_nonfixed = [s for s in parent2 if not s.get('is_fixed', False)]
        
        child1.extend(copy.deepcopy(fixed_slots))
        child2.extend(copy.deepcopy(fixed_slots))
        
        min_len = min(len(parent1_nonfixed), len(parent2_nonfixed))
        for i in range(min_len):
            if random.random() < 0.5:
                child1.append(copy.deepcopy(parent1_nonfixed[i]))
                child2.append(copy.deepcopy(parent2_nonfixed[i]))
            else:
                child1.append(copy.deepcopy(parent2_nonfixed[i]))
                child2.append(copy.deepcopy(parent1_nonfixed[i]))
        
        child1.extend(copy.deepcopy(parent1_nonfixed[min_len:]))
        child2.extend(copy.deepcopy(parent2_nonfixed[min_len:]))
        
        return child1, child2
    
    def _mutate(self, timetable: List[Dict]) -> List[Dict]:
        """Swap mutation"""
        mutated = copy.deepcopy(timetable)
        non_fixed_indices = [i for i, s in enumerate(mutated) if not s.get('is_fixed', False)]
        
        if len(non_fixed_indices) < 2:
            return mutated
        
        for _ in range(int(len(non_fixed_indices) * self.mutation_rate) + 1):
            if random.random() < self.mutation_rate:
                idx1, idx2 = random.sample(non_fixed_indices, 2)
                mutated[idx1]['day'], mutated[idx2]['day'] = mutated[idx2]['day'], mutated[idx1]['day']
                mutated[idx1]['time_slot'], mutated[idx2]['time_slot'] = mutated[idx2]['time_slot'], mutated[idx1]['time_slot']
        
        return mutated
    
    def run(self, progress_callback: Optional[Callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """Run fully optimized multi-core genetic algorithm"""
        # Parallel population initialization
        population = self._initialize_population_parallel()
        fitness_history = []
        
        best_overall_fitness = 0
        best_overall_timetable = None
        
        for generation in range(self.max_generations):
            # Parallel fitness calculation
            fitnesses = self._calculate_fitness_batch_optimized(population)
            
            best_fitness = max(fitnesses)
            avg_fitness = sum(fitnesses) / len(fitnesses)
            best_idx = fitnesses.index(best_fitness)
            
            fitness_history.append({
                'generation': generation,
                'best': best_fitness,
                'average': avg_fitness
            })
            
            if best_fitness > best_overall_fitness:
                best_overall_fitness = best_fitness
                best_overall_timetable = copy.deepcopy(population[best_idx])
            
            if progress_callback:
                progress_callback(generation + 1, best_fitness, avg_fitness)
            
            if best_fitness >= 999.0:
                break
            
            # Create next generation
            new_population = []
            
            # Elitism - keep best individuals
            elite_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)[:self.elite_size]
            for idx in elite_indices:
                new_population.append(copy.deepcopy(population[idx]))
            
            # Generate rest of population with parallel crossover/mutation
            parent_pairs = []
            while len(new_population) + len(parent_pairs) * 2 < self.population_size:
                parent1 = self._tournament_selection(population, fitnesses)
                parent2 = self._tournament_selection(population, fitnesses)
                parent_pairs.append((parent1, parent2))
            
            # Parallel crossover and mutation
            children = self._parallel_crossover_mutation(parent_pairs)
            new_population.extend(children[:self.population_size - len(new_population)])
            
            population = new_population
        
        return best_overall_timetable, fitness_history
