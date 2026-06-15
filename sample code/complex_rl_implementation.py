import gymnasium as gym
import math
import random
import numpy as np
from collections import namedtuple, deque

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# Define the Neural Network Architecture
class QNetwork(nn.Module):
    """
    Instead of a table, we use a Neural Network to predict Q-values.
    Input: State (e.g., cart position, velocity, pole angle, pole velocity)
    Output: Q-values for each possible action (e.g., push left, push right)
    """
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()
        # A simple Multi-Layer Perceptron (MLP)
        self.fc1 = nn.Linear(state_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x) # Returns raw Q-values for all actions

# Define a Replay Buffer
class ReplayBuffer:
    """
    Neural networks forget past experiences if trained purely sequentially. 
    A replay buffer stores past experiences and samples them randomly during training 
    to break the correlation between consecutive steps and stabilize learning.
    """
    def __init__(self, capacity):
        self.memory = deque(maxlen=capacity)
        self.experience = namedtuple("Experience", field_names=["state", "action", "reward", "next_state", "done"])

    def add(self, state, action, reward, next_state, done):
        e = self.experience(state, action, reward, next_state, done)
        self.memory.append(e)

    def sample(self, batch_size):
        experiences = random.sample(self.memory, k=batch_size)
        
        # Convert to PyTorch tensors
        states = torch.from_numpy(np.vstack([e.state for e in experiences])).float()
        actions = torch.from_numpy(np.vstack([e.action for e in experiences])).long()
        rewards = torch.from_numpy(np.vstack([e.reward for e in experiences])).float()
        next_states = torch.from_numpy(np.vstack([e.next_state for e in experiences])).float()
        dones = torch.from_numpy(np.vstack([e.done for e in experiences]).astype(np.uint8)).float()
        
        return (states, actions, rewards, next_states, dones)

    def __len__(self):
        return len(self.memory)

# Define the Deep Q-Learning Agent
class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        
        # Hyperparameters
        self.lr = 1e-3
        self.gamma = 0.99           # Discount factor
        self.batch_size = 64
        self.epsilon = 1.0          # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.target_update = 10     # How often to update target network

        # The "Brain" (Policy Network) and the "Target" (Target Network)
        # Using two networks stabilizes training
        self.policy_net = QNetwork(state_size, action_size)
        self.target_net = QNetwork(state_size, action_size)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval() # Target net is only used for inference

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.lr)
        self.memory = ReplayBuffer(capacity=10000)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net.to(self.device)
        self.target_net.to(self.device)

    def step(self, state, action, reward, next_state, done):
        # Save experience in replay memory
        self.memory.add(state, action, reward, next_state, done)
        
        # If enough samples are available in memory, learn from a batch
        if len(self.memory) > self.batch_size:
            self.learn()

    def act(self, state):
        """Epsilon-greedy action selection using the Neural Network."""
        if random.random() < self.epsilon:
            return random.choice(np.arange(self.action_size))
            
        state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        self.policy_net.eval()
        with torch.no_grad():
            action_values = self.policy_net(state_tensor)
        self.policy_net.train()
        
        # Return the action with the highest Q-value
        return np.argmax(action_values.cpu().data.numpy())

    def learn(self):
        """Update value parameters using given batch of experience tuples."""
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # Get expected Q values from policy network
        Q_expected = self.policy_net(states).gather(1, actions)

        # Get max predicted Q values (for next states) from target network
        Q_targets_next = self.target_net(next_states).detach().max(1)[0].unsqueeze(1)
        
        # Compute Q targets for current states (Bellman Equation via Neural Networks)
        Q_targets = rewards + (self.gamma * Q_targets_next * (1 - dones))

        # Compute loss (Mean Squared Error)
        loss = F.mse_loss(Q_expected, Q_targets)

        # Minimize the loss via Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

def train_dqn():
    env = gym.make('CartPole-v1')
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n
    
    agent = DQNAgent(state_size, action_size)
    episodes = 500
    
    print(f"Training on device: {agent.device}")
    
    for i_episode in range(1, episodes + 1):
        state, _ = env.reset()
        score = 0
        done = False
        truncated = False
        
        while not (done or truncated):
            action = agent.act(state)
            next_state, reward, done, truncated, _ = env.step(action)
            agent.step(state, action, reward, next_state, done or truncated)
            state = next_state
            score += reward
            
        # Decay exploration
        agent.epsilon = max(agent.epsilon_min, agent.epsilon * agent.epsilon_decay)
        
        # Update target network occasionally
        if i_episode % agent.target_update == 0:
            agent.target_net.load_state_dict(agent.policy_net.state_dict())
            
        if i_episode % 50 == 0:
            print(f"Episode {i_episode}\tScore: {score:.2f}\tEpsilon: {agent.epsilon:.2f}")
            
        # CartPole is considered "solved" if score is 475 or higher
        if score >= 475:
            print(f"\nEnvironment solved in {i_episode} episodes! \tFinal Score: {score:.2f}")
            break
            
    env.close()
    return agent

if __name__ == "__main__":
    print("Starting Deep Q-Learning (DQN) Training on CartPole-v1...")
    trained_agent = train_dqn()
    print("\nTraining Complete! You can now uncomment code to render the agent if desired.")