from typing import List, Dict, Optional
from database import Database
from timetable_csp import TimetableCSP

# Import GA for backward compatibility
try:
    from genetic_algorithm import create_genetic_algorithm
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False

def create_solver(algorithm: str, db: Database, selected_batches: List[int], 
                 use_fixed_slots: bool = True, **kwargs):
    """
    Factory function to create appropriate timetable solver
    
    Args:
        algorithm: 'csp', 'csp_min_conflicts', 'genetic_cpu', or 'genetic_gpu'
        db: Database instance
        selected_batches: List of batch IDs
        use_fixed_slots: Whether to honor fixed slots
        **kwargs: Algorithm-specific parameters
    
    Returns:
        Solver instance with run() method
    """
    
    if algorithm == 'csp' or algorithm == 'csp_min_conflicts':
        return TimetableCSP(
            db=db,
            selected_batches=selected_batches,
            use_fixed_slots=use_fixed_slots,
            max_iterations=kwargs.get('max_iterations', 10000),
            use_min_conflicts=(algorithm == 'csp_min_conflicts')
        )
    
    elif algorithm in ['genetic_cpu', 'genetic_gpu']:
        if not GA_AVAILABLE:
            raise ImportError("Genetic algorithm module not available")
        
        return create_genetic_algorithm(
            db=db,
            selected_batches=selected_batches,
            use_fixed_slots=use_fixed_slots,
            use_gpu=(algorithm == 'genetic_gpu'),
            population_size=kwargs.get('population_size', 100),
            max_generations=kwargs.get('max_generations', 100),
            crossover_rate=kwargs.get('crossover_rate', 0.8),
            mutation_rate=kwargs.get('mutation_rate', 0.01),
            elite_size=kwargs.get('elite_size', 5),
            tournament_size=kwargs.get('tournament_size', 5),
            use_multiprocessing=kwargs.get('use_multiprocessing', True),
            n_workers=kwargs.get('n_workers', None)
        )
    
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose from: csp, csp_min_conflicts, genetic_cpu, genetic_gpu")
