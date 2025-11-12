import streamlit as st
import json
import time
import os
import pandas as pd
from database import Database
from constraint_solver import create_solver
import datetime
from theme import apply_light_mode_css
apply_light_mode_css()
#from auth import prevent_url_manipulation

# Try to import GA validation function
try:
    from genetic_algorithm import validate_timetable
except ImportError:
    def validate_timetable(timetable, db):
        """Fallback validation if GA module not available"""
        return {'conflicts': [], 'stats': {}}

# Security check
#prevent_url_manipulation()

#========HELPER FUNCTIONS=============
def load_timetables_from_json():
    """Load all saved timetables from JSON files"""
    import os
    import json
    
    timetables_dir = 'timetables'
    if not os.path.exists(timetables_dir):
        return []
    
    timetables = []
    for filename in os.listdir(timetables_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(timetables_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    timetables.append(data)
            except Exception as e:
                st.warning(f"Error loading {filename}: {e}")
    
    # Sort by creation time (newest first)
    timetables.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return timetables


def delete_timetable_json(version_name: str):
    """Delete a saved timetable JSON file"""
    filepath = f"timetables/{version_name}.json"
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


st.title("⚙️ Configure & Generate Timetable")
st.markdown("### Select batches and configure constraints for timetable generation")

db = st.session_state.db

# ===== PERSISTENCE: Load from database on startup =====
def load_persisted_data():
    """Load previously generated timetable from database"""
    if 'data_loaded_from_db' not in st.session_state:
        try:
            saved_timetable = db.get_generated_timetable()
            if saved_timetable and len(saved_timetable) > 0:
                st.session_state.generated_timetable = saved_timetable
                st.session_state.fitness_score = saved_timetable[0].get('fitness_score', 0) if saved_timetable else 0
                batch_ids = list(set(s['batch_id'] for s in saved_timetable))
                st.session_state.selected_batches = batch_ids
                st.info("📁 Loaded previously generated timetable from database")
        except Exception as e:
            st.warning(f"Could not load previous timetable: {e}")
        finally:
            st.session_state.data_loaded_from_db = True

load_persisted_data()

# ===== BATCH SELECTION =====
st.header("1️⃣ Select Batches")
batches = db.get_all('batches')

if not batches:
    st.error("❌ No batches found. Please add batches in Data Input first.")
    st.stop()

batch_options = {f"{b['batch_code']} - {b['batch_name']}": b['id'] for b in batches}
selected_batch_names = st.multiselect(
    "Select Batches for Timetable Generation*",
    options=list(batch_options.keys()),
    default=[k for k, v in batch_options.items() if v in st.session_state.get('selected_batches', [])],
    help="Select one or more batches to generate timetable for"
)

selected_batch_ids = [batch_options[name] for name in selected_batch_names]

if not selected_batch_ids:
    st.warning("⚠️ Please select at least one batch")
    st.stop()

st.session_state.selected_batches = selected_batch_ids

# ===== CONSTRAINT CONFIGURATION =====
st.markdown("---")
st.header("2️⃣ Configure Constraints")

with st.expander("🔧 Constraint Settings", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        avoid_consecutive = st.checkbox(
            "Avoid Consecutive Same-Type Classes",
            value=True,
            help="Prevent lab-lab or theory-theory patterns consecutively"
        )
        
        no_morning_gaps = st.checkbox(
            "No Morning Free Slots",
            value=True,
            help="Penalize empty slots in morning (first time period)"
        )
    
    with col2:
        enable_saturday_flex = st.checkbox(
            "Enable Saturday Flexibility",
            value=False,
            help="Allow Saturday morning to be used if other days overloaded"
        )
        
        lab_alternation = st.slider(
            "Lab Alternation Strictness (0-10)",
            min_value=0,
            max_value=10,
            value=5,
            help="How strictly to enforce lab rotation between batch groups (0=relaxed, 10=strict)"
        )

# Get constraints from database
constraints = db.get_constraints()
st.markdown("**Constraint Weights**")
constraint_adjustments = {}

cols = st.columns(3)
for idx, constraint in enumerate(constraints[:9]):  # Show first 9
    col = cols[idx % 3]
    with col:
        weight = st.slider(
            f"{constraint['constraint_name'].replace('_', ' ').title()}",
            min_value=0.0,
            max_value=10.0,
            value=float(constraint['weight']),
            step=0.1,
            key=f"constraint_{constraint['id']}"
        )
        constraint_adjustments[constraint['constraint_name']] = weight

# ===== ALGORITHM SELECTION =====
st.markdown("---")
st.header("3️⃣ Algorithm Selection")

algorithm_option = st.selectbox(
    "Select Solving Algorithm",
    [
        "🔍 CSP - Constraint Satisfaction (Recommended)",
        "🧬 Genetic Algorithm - CPU",
        "🎮 Genetic Algorithm - GPU"
    ],
    help="CSP algorithms are deterministic and faster for highly constrained problems. GA is better for soft constraint optimization."
)

# Map selection to algorithm type
algorithm_map = {
    "🔍 CSP - Constraint Satisfaction (Recommended)": "csp",
    "🧬 Genetic Algorithm - CPU": "genetic_cpu",
    "🎮 Genetic Algorithm - GPU": "genetic_gpu"
}
selected_algorithm = algorithm_map[algorithm_option]

# Algorithm-specific parameters
if selected_algorithm == 'csp':
    st.markdown("### CSP Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        max_iterations = st.number_input(
            "Max Iterations",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000,
            help="Maximum iterations (mainly affects timeout)"
        )
    
    with col2:
        st.info(
            "**CSP Algorithm Benefits:**\n"
            "✅ Deterministic results\n"
            "✅ Faster convergence\n"
            "✅ Guaranteed solution if one exists\n"
            "✅ Better constraint handling"
        )
    
    solver_params = {
        'max_iterations': max_iterations
    }

else:  # Genetic Algorithm
    st.markdown("### Genetic Algorithm Parameters")
    
    # Check GPU availability
    use_gpu = (selected_algorithm == 'genetic_gpu')
    if use_gpu:
        try:
            from genetic_algorithm_gpu import GPU_AVAILABLE
            if not GPU_AVAILABLE:
                st.error("❌ GPU not available. Please select CPU version or install CuPy.")
                st.stop()
        except ImportError:
            st.error("❌ GPU module not found. Please select CPU version.")
            st.stop()
    
    with st.expander("🧬 Genetic Algorithm Configuration", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            population_size = st.slider(
                "Population Size",
                min_value=20,
                max_value=500,
                value=100,
                step=10,
                help="Number of timetables in each generation"
            )
            
            mutation_rate = st.slider(
                "Mutation Rate",
                min_value=0.001,
                max_value=0.1,
                value=0.01,
                step=0.001,
                help="Probability of random mutations"
            )
        
        with col2:
            max_generations = st.slider(
                "Max Generations",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                help="Maximum iterations"
            )
            
            crossover_rate = st.slider(
                "Crossover Rate",
                min_value=0.1,
                max_value=1.0,
                value=0.8,
                step=0.05,
                help="Probability of crossover between parents"
            )
        
        with col3:
            elite_size = st.slider(
                "Elite Size",
                min_value=1,
                max_value=20,
                value=5,
                help="Number of best timetables preserved"
            )
            
            tournament_size = st.slider(
                "Tournament Size",
                min_value=2,
                max_value=20,
                value=5,
                help="Number of candidates in tournament selection"
            )
    
    solver_params = {
        'population_size': population_size,
        'max_generations': max_generations,
        'crossover_rate': crossover_rate,
        'mutation_rate': mutation_rate,
        'elite_size': elite_size,
        'tournament_size': tournament_size
    }
    
    if selected_algorithm == 'genetic_cpu':
        import multiprocessing
        max_cores = multiprocessing.cpu_count()
        n_workers = st.slider(
            "CPU Cores",
            min_value=1,
            max_value=max_cores,
            value=max(1, max_cores - 1),
            help="Number of CPU cores to use"
        )
        solver_params['n_workers'] = n_workers
        solver_params['use_multiprocessing'] = True

# ===== GENERATION =====
st.markdown("---")
st.header("4️⃣ Generate Timetable")

col1, col2 = st.columns(2)

with col1:
    generate_btn = st.button("🚀 Generate Timetable", use_container_width=True, type="primary")

with col2:
    regenerate_btn = st.button("🔄 Regenerate", use_container_width=True)

if generate_btn or regenerate_btn:
    try:
        with st.spinner(f"⏳ Initializing {algorithm_option}..."):
            # Create constraints config
            constraints_config = {
                'avoid_consecutive_same_type': avoid_consecutive,
                'no_morning_gaps': no_morning_gaps,
                'enable_saturday_flexibility': enable_saturday_flex,
                'lab_alternation_strictness': lab_alternation
            }
            
            # Create solver using factory
            solver = create_solver(
                algorithm=selected_algorithm,
                db=db,
                selected_batches=selected_batch_ids,
                use_fixed_slots=True,
                **solver_params
            )
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            fitness_metrics = st.empty()
            
            # Initialize best_fitness
            best_fitness = 0
            
            
            # Progress callback
            def progress_callback(*args):
                global best_fitness
                
                if selected_algorithm == 'csp':
                    # CSP progress: (progress_pct, assigned, total)
                    progress, assigned, total = args
                    progress_bar.progress(min(progress / 100, 1.0))
                    status_text.write(f"Assigned: {assigned}/{total} variables | Progress: {progress}%")
                else:
                    # GA progress: (generation, best_fitness, avg_fitness)
                    gen, best, avg = args
                    best_fitness = best
                    progress = min(gen / solver_params['max_generations'], 1.0)
                    progress_bar.progress(progress)
                    status_text.write(f"Generation: {gen}/{solver_params['max_generations']} | Best: {best:.2f} | Avg: {avg:.2f}")
            
            # Run solver
            with st.spinner(f"🧬 Running {algorithm_option}..."):
                timetable, fitness_history = solver.run(progress_callback)
                
                if timetable:
                    # Set best fitness for CSP (always perfect)
                    if selected_algorithm == 'csp':
                        best_fitness = 1000.0
                    
                    st.session_state.generated_timetable = timetable
                    st.session_state.fitness_score = best_fitness
                    st.session_state.fitness_history = fitness_history
                    st.session_state.generation_config = {
                        'algorithm': selected_algorithm,
                        'constraints_config': constraints_config,
                        **solver_params
                    }
                    
                    # Save to database with version
                    version_name = f"{selected_algorithm.upper()}_{int(time.time())}"
                    
                    

                    try:
                        # Create timetable data structure
                        timetable_data = {
                            "version_name": version_name,
                            "algorithm": selected_algorithm.upper(),
                            "created_by": st.session_state.get('username', 'admin'),
                            "created_at": datetime.time().isoformat(),
                            "fitness_score": best_fitness,
                            "generation_config": st.session_state.generation_config,
                            "timetable": timetable,
                            "metadata": {
                                "total_slots": len(timetable),
                                "selected_batches": st.session_state.generation_config.get('selected_batches', []),
                                "constraints_used": list(st.session_state.generation_config.get('constraints', {}).keys())
                            }
                        }
                        
                        # Create 'timetables' directory if it doesn't exist
                        os.makedirs('timetables', exist_ok=True)
                        
                        # Save to JSON file
                        filename = f"timetables/{version_name}.json"
                        with open(filename, 'w') as f:
                            json.dump(timetable_data, f, indent=2)
                        
                        st.success(f"✅ Timetable saved as '{filename}'")
                        
                    except Exception as e:
                        st.warning(f"⚠️ Generated but not saved: {e}")

                    st.success("✅ Timetable Generated Successfully!")
                    
                    
                    # Display fitness metrics
                    with fitness_metrics.container():
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Best Fitness", f"{best_fitness:.2f}")
                        
                        if fitness_history and selected_algorithm != 'csp':
                            avg_final = fitness_history[-1].get('average', 0)
                            col2.metric("Final Average Fitness", f"{avg_final:.2f}")
                            
                            if fitness_history[0].get('best', 0) > 0:
                                improvement = ((best_fitness - fitness_history[0]['best']) / fitness_history[0]['best'] * 100)
                                col3.metric("Improvement %", f"{improvement:.1f}%")
                        else:
                            col2.metric("Algorithm", selected_algorithm.upper())
                            elapsed = fitness_history[0].get('time', 0) if fitness_history else 0
                            col3.metric("Time", f"{elapsed:.2f}s")
                    
                    # Validate timetable
                    validation_results = validate_timetable(timetable, db)
                    
                    if validation_results.get('conflicts'):
                        st.warning(f"⚠️ {len(validation_results['conflicts'])} conflicts found")
                        with st.expander("View Conflicts"):
                            for conflict in validation_results['conflicts']:
                                st.write(f"- {conflict}")
                    else:
                        st.success("✅ No conflicts detected!")
                else:
                    st.error("❌ Failed to generate timetable")
                    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# Display fitness history chart
if st.session_state.get('fitness_history') and st.session_state.get('generation_config', {}).get('algorithm') != 'csp':
    st.markdown("---")
    st.header("📈 Fitness Progression")
    
    history_df = pd.DataFrame(st.session_state.fitness_history)
    
    try:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history_df['generation'] if 'generation' in history_df.columns else history_df.index,
            y=history_df['best'] if 'best' in history_df.columns else history_df.get('fitness', []),
            mode='lines',
            name='Best Fitness'
        ))
        
        if 'average' in history_df.columns:
            fig.add_trace(go.Scatter(
                x=history_df['generation'],
                y=history_df['average'],
                mode='lines',
                name='Average Fitness'
            ))
        
        fig.update_layout(
            title="Algorithm Convergence",
            xaxis_title="Iteration",
            yaxis_title="Fitness Score",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info("Install plotly for better visualization: pip install plotly")
        if 'generation' in history_df.columns:
            st.line_chart(history_df.set_index('generation')[['best', 'average']])
        else:
            st.line_chart(history_df)

# ===== CURRENT TIMETABLE PREVIEW =====
if st.session_state.get('generated_timetable'):
    st.markdown("---")
    st.header("📋 Current Generated Timetable Preview")
    
    timetable = st.session_state.generated_timetable
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Slots", len(timetable))
    
    with col2:
        unique_batches = len(set(s['batch_id'] for s in timetable))
        st.metric("Batches", unique_batches)
    
    with col3:
        unique_subjects = len(set(s.get('subject_id') for s in timetable if s.get('subject_id')))
        st.metric("Subjects", unique_subjects)
    
    with col4:
        st.metric("Fitness Score", f"{st.session_state.get('fitness_score', 0):.2f}")
    
    # Display full timetable table
    st.subheader("Detailed Timetable")
    display_data = []
    
    for slot in timetable:
        batch = db.get_by_id('batches', slot['batch_id'])
        subject = db.get_by_id('subjects', slot['subject_id']) if slot.get('subject_id') else None
        faculty = db.get_by_id('faculty', slot['faculty_id']) if slot.get('faculty_id') else None
        
        display_data.append({
            'Batch': batch['batch_name'] if batch else 'N/A',
            'Day': slot['day'],
            'Time Slot': slot['time_slot'],
            'Subject': subject['subject_name'] if subject else 'N/A',
            'Faculty': faculty['faculty_name'] if faculty else 'N/A',
            'Type': slot.get('room_type', 'classroom'),
            'Room': slot.get('room_id', 'N/A'),
            'Fixed': '✓' if slot.get('is_fixed', False) else '✗'
        })
    
    df_display = pd.DataFrame(display_data)
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Export preview
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Go to View & Export", use_container_width=True):
            st.switch_page("pages/page_view_export.py")
    
    with col2:
        if st.button("🗑️ Clear Timetable", use_container_width=True):
            st.session_state.generated_timetable = None
            st.session_state.fitness_score = 0.0
            st.rerun()
