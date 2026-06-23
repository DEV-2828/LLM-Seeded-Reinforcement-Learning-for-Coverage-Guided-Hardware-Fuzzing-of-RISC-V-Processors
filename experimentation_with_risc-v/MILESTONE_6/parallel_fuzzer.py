import os
import sys
import time
import torch
import torch.multiprocessing as mp
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import DQNAgent

def worker_loop(worker_id, num_episodes, max_steps, experience_queue, weight_dict):
    """
    Worker process loop. It instantiates its own isolated environment and actor agent.
    """
    # Import locally to avoid cross-process ctypes issues
    verilator_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'verilator_env'))
    if verilator_env_path not in sys.path:
        sys.path.append(verilator_env_path)
    from verilator_env.differential_fuzzer import DifferentialFuzzerEnv
    
    print(f"[Worker {worker_id}] Starting...")
    env = DifferentialFuzzerEnv()
    
    # Local agent just for action selection (inference)
    agent = DQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    
    total_bugs = 0
    unique_sigs = set()
    
    for episode in range(num_episodes):
        state = env.reset()
        
        # Sync weights at the start of each episode if available
        if 'q_network' in weight_dict:
            agent.q_network.load_state_dict(weight_dict['q_network'])
        
        for step in range(max_steps):
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            
            # Push transition to central experience queue
            experience_queue.put((state, action, reward, next_state, done))
            
            state = next_state
            if done:
                break
                
        agent.decay_epsilon()
        
        if len(env.bugs_found) > total_bugs:
            new_bugs = len(env.bugs_found) - total_bugs
            total_bugs = len(env.bugs_found)
            for b in env.bugs_found[-new_bugs:]:
                unique_sigs.add(b['operation'])
            print(f"[Worker {worker_id}] Ep {episode}: Found {new_bugs} new bugs! Total worker bugs: {total_bugs} | Unique classes: {len(unique_sigs)}")

    print(f"[Worker {worker_id}] Finished {num_episodes} episodes. Found {total_bugs} bugs total.")


def main():
    # Use spawn method for safety with ctypes and CUDA
    mp.set_start_method('spawn', force=True)
    
    num_workers = 4
    num_episodes_per_worker = 100  # Total 400 episodes across workers
    max_steps = 100
    
    print("="*60)
    print("  MILESTONE 6: Parallel Fuzzer (Multi-Worker)")
    print("="*60)
    print(f"  Spawning {num_workers} workers...")
    
    # State and action space dimensions for our ALU environment
    state_dim = 16  # 6 instruction fields + 10 coverage bits
    action_dim = 38 # 38 possible mutations
    
    # Global central agent for training
    global_agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
    
    experience_queue = mp.Queue(maxsize=20000)
    manager = mp.Manager()
    weight_dict = manager.dict()
    
    # Store initial weights
    weight_dict['q_network'] = {k: v.cpu() for k, v in global_agent.q_network.state_dict().items()}
    
    workers = []
    for i in range(num_workers):
        p = mp.Process(target=worker_loop, args=(
            i, num_episodes_per_worker, max_steps, experience_queue, weight_dict
        ))
        p.start()
        workers.append(p)
        
    start_time = time.time()
    
    steps_processed = 0
    target_update_freq = 500
    last_print_time = time.time()
    
    # Training Loop
    while any(p.is_alive() for p in workers) or not experience_queue.empty():
        while not experience_queue.empty():
            try:
                state, action, reward, next_state, done = experience_queue.get_nowait()
            except queue.Empty:
                break
                
            # Step the global agent (adds to memory and triggers train if batch full)
            global_agent.step(state, action, reward, next_state, done)
            steps_processed += 1
            
            # Sync target network and broadcast weights periodically
            if steps_processed % target_update_freq == 0:
                global_agent.update_target_network()
                weight_dict['q_network'] = {k: v.cpu() for k, v in global_agent.q_network.state_dict().items()}
                
            if steps_processed % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"[Main] Processed {steps_processed} transitions. Queue size: {experience_queue.qsize()}. Time: {elapsed:.1f}s")
                
        # Sleep briefly to avoid 100% CPU lock in the polling loop
        time.sleep(0.01)
        
    for p in workers:
        p.join()
        
    elapsed = time.time() - start_time
    print("="*60)
    print("  PARALLEL FUZZING COMPLETE")
    print(f"  Time taken: {elapsed:.1f}s")
    print(f"  Total steps processed: {steps_processed}")
    print(f"  Throughput: {steps_processed/elapsed:.1f} steps/second")
    print("="*60)

if __name__ == "__main__":
    import queue  # Ensure queue is imported for the try/except block
    main()
