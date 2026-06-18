import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import random
import numpy as np
from collections import deque

class EpisodicReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, episode):
        # episode is a list of transitions: (state, action, reward, next_state, done)
        self.buffer.append(episode)
        
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

class DRQNetwork(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=64):
        super(DRQNetwork, self).__init__()
        self.hidden_dim = hidden_dim
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.fc2 = nn.Linear(hidden_dim, action_dim)
        
    def forward(self, x, hidden):
        # x is (batch, seq_len, state_dim)
        x = F.relu(self.fc1(x))
        out, hidden = self.lstm(x, hidden)
        out = self.fc2(out)
        return out, hidden
        
class DRQNAgent:
    def __init__(self, state_dim, action_dim, hidden_dim=64, lr=1e-3, gamma=0.99, batch_size=16, buffer_size=1000):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.gamma = gamma
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_network = DRQNetwork(state_dim, action_dim, hidden_dim).to(self.device)
        self.target_network = DRQNetwork(state_dim, action_dim, hidden_dim).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.memory = EpisodicReplayBuffer(buffer_size)
        
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.995

    def init_hidden(self, batch_size=1):
        return (torch.zeros(1, batch_size, self.hidden_dim).to(self.device),
                torch.zeros(1, batch_size, self.hidden_dim).to(self.device))

    def select_action(self, state, hidden):
        if random.random() < self.epsilon:
            action = random.randrange(self.action_dim)
            # Step LSTM to get next hidden even if action is random
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(self.device)
                _, next_hidden = self.q_network(state_tensor, hidden)
            return action, next_hidden
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(self.device)
            q_values, next_hidden = self.q_network(state_tensor, hidden)
            return q_values.argmax().item(), next_hidden

    def optimize_model(self):
        if len(self.memory) < self.batch_size:
            return
            
        episodes = self.memory.sample(self.batch_size)
        seq_len = len(episodes[0])
        
        states = np.zeros((self.batch_size, seq_len, self.state_dim))
        actions = np.zeros((self.batch_size, seq_len, 1))
        rewards = np.zeros((self.batch_size, seq_len, 1))
        next_states = np.zeros((self.batch_size, seq_len, self.state_dim))
        dones = np.zeros((self.batch_size, seq_len, 1))
        
        for i, ep in enumerate(episodes):
            for t, transition in enumerate(ep):
                states[i, t] = transition[0]
                actions[i, t] = transition[1]
                rewards[i, t] = transition[2]
                next_states[i, t] = transition[3]
                dones[i, t] = transition[4]
                
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        hidden = self.init_hidden(self.batch_size)
        q_values, _ = self.q_network(states, hidden)
        q_values = q_values.gather(2, actions)
        
        with torch.no_grad():
            next_hidden = self.init_hidden(self.batch_size)
            next_q_values, _ = self.target_network(next_states, next_hidden)
            next_q_values = next_q_values.max(2)[0].unsqueeze(2)
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
            
        loss = F.mse_loss(q_values, target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def update_target_network(self):
        self.target_network.load_state_dict(self.q_network.state_dict())
        
    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
