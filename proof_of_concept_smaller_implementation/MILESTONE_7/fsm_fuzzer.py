import os
import sys
import time
import numpy as np

from agent_rnn import DRQNAgent
from env_fsm import FSMFuzzerEnv

def main():
    print("="*60)
    print("  MILESTONE 7: RNN Agent fuzzing an FSM Control Unit")
    print("="*60)
    
    env = FSMFuzzerEnv()
    agent = DRQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    
    num_episodes = 2000
    max_steps_per_episode = 15
    
    start_time = time.time()
    total_bugs = 0
    
    for episode in range(num_episodes):
        state = env.reset()
        hidden = agent.init_hidden()
        
        episode_transitions = []
        
        for step in range(max_steps_per_episode):
            action, next_hidden = agent.select_action(state, hidden)
            next_state, reward, done, _ = env.step(action)
            
            episode_transitions.append((state, action, reward, next_state, done))
            
            state = next_state
            hidden = next_hidden
            
            if done:
                break
                
        # Pad episode to max length so we can safely stack them in Numpy for the LSTM batches
        while len(episode_transitions) < max_steps_per_episode:
            episode_transitions.append((state, 0, 0.0, state, True))
            
        agent.memory.push(episode_transitions)
        agent.optimize_model()
        agent.decay_epsilon()
        
        if episode % 20 == 0:
            agent.update_target_network()
            
        if len(env.bugs_found) > total_bugs:
            total_bugs = len(env.bugs_found)
            
        if episode % 100 == 0 and episode > 0:
            elapsed = time.time() - start_time
            print(f"Episode {episode:4d} | Eps: {agent.epsilon:.2f} | Cov: {int(np.sum(env.coverage))}/{env.num_states} | Bugs: {total_bugs} | Time: {elapsed:.1f}s")

    elapsed = time.time() - start_time
    print("="*60)
    print("  FSM FUZZING COMPLETE")
    print(f"  Time taken: {elapsed:.1f}s")
    print(f"  Total Bugs Found: {total_bugs}")
    if total_bugs > 0:
        print("\n  Sample Bug Report:")
        print(env.bugs_found[0])
    print("="*60)

if __name__ == "__main__":
    main()
