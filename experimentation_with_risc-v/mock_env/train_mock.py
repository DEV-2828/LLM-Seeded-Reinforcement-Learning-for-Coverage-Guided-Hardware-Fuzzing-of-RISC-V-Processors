import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env_mock import MockALUEnv
from agent import DQNAgent

def train():
    env = MockALUEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    
    num_episodes = 500
    max_steps_per_episode = 100
    target_update_freq = 10
    
    # Tracking metrics
    coverage_history = []
    
    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0
        
        for step in range(max_steps_per_episode):
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            
            agent.step(state, action, reward, next_state, done)
            
            state = next_state
            total_reward += reward
            
            if done:
                break
                
        agent.decay_epsilon()
        
        if episode % target_update_freq == 0:
            agent.update_target_network()
            
        current_coverage = np.sum(env.coverage)
        coverage_history.append(current_coverage)
        
        if episode % 50 == 0:
            print(f"Episode {episode}, Epsilon: {agent.epsilon:.2f}, Coverage: {current_coverage}/{env.num_branches}, Total Reward: {total_reward}")

    print("Training finished!")
    print(f"Final Coverage: {np.sum(env.coverage)}/{env.num_branches}")

    # Plot results
    plt.plot(coverage_history)
    plt.title('RL Agent Coverage Over Time')
    plt.xlabel('Episode')
    plt.ylabel('Unique Branches Hit')
    plt.savefig('coverage_plot.png')
    print("Saved coverage plot to coverage_plot.png")

if __name__ == "__main__":
    train()
