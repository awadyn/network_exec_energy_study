import gym
import math
import random
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
#from collections import namedtuple, deque
#from itertools import count
#from PIL import Image

import torch 
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.distributions as distributions
#import torchvision.transforms as T

train_env = gym.make('CartPole-v1', new_step_api=True).unwrapped
test_env = gym.make('CartPole-v1', new_step_api=True).unwrapped


# #setup matplotlib
# is_ipython = 'inline' in matplotlib.get_backend()
# if is_ipython:
# 	from IPython import display

plt.ion()


#check if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

##
print("READY..")
##


SEED = 1234
train_env.reset(seed = SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


class MLP(nn.Module):
	def __init__(self, input_dim, hidden_dim, output_dim, dropout = 0.5):
		super().__init__()

		self.fc_1 = nn.Linear(input_dim, hidden_dim)
		self.fc_2 = nn.Linear(hidden_dim, output_dim)
		self.dropout = nn.Dropout(dropout)

	def forward(self, x):
		x = self.fc_1(x)
		x = self.dropout(x)
		x = F.relu(x)
		x = self.fc_2(x)
		return x

INPUT_DIM = train_env.observation_space.shape[0]
print("input dim: ", INPUT_DIM)
HIDDEN_DIM = 128
OUTPUT_DIM = train_env.action_space.n
print("output dim: ", OUTPUT_DIM)

policy = MLP(INPUT_DIM, HIDDEN_DIM, OUTPUT_DIM)
#print("policy parameters: ", list(policy.parameters()))

##

def init_weights(m):
	if type(m) == nn.Linear:
		torch.nn.init.xavier_normal_(m.weight)
		m.bias.data.fill_(0)

my_mlp = policy.apply(init_weights)
print(my_mlp)
##

LEARNING_RATE = 0.01
optimizer = optim.Adam(policy.parameters(), lr = LEARNING_RATE)

##

def train(env, policy, optimizer, discount_factor):
	policy.train()
	
	log_prob_actions = []
	rewards = []
	done = False
	episode_reward = 0

	state = env.reset()

	while not done:
		state = torch.FloatTensor(state).unsqueeze(0)
#		print("state: ", state)
		action_pred = policy(state)
#		print("action pred: ", action_pred)
		action_prob = F.softmax(action_pred, dim=-1)
#		print("action prob: ", action_prob)
		dist = distributions.Categorical(action_prob)
#		print("dist: ", dist)
		action = dist.sample()
#		print("action: ", action)
		log_prob_action = dist.log_prob(action)
#		print("log_prob_action: ", log_prob_action)
		state, reward, done, _, _ = env.step(action.item())
#		print("state after step: ", state)
#		print("reward after step: ", reward)
#		print()
#		print()
#		done = True

		log_prob_actions.append(log_prob_action)
		rewards.append(reward)
		episode_reward += reward

	log_prob_actions = torch.cat(log_prob_actions)
#	print("log_prob_actions: ", log_prob_actions)
	returns = calculate_returns(rewards, discount_factor)
#	print("returns: ", returns)
	loss = update_policy(returns, log_prob_actions, optimizer)	
#	print("loss: ", loss)

	return loss, episode_reward

##

def calculate_returns(rewards, discount_factor, normalize=True):
	returns = []
	R = 0

	for r in reversed(rewards):
		R = r + R * discount_factor
		returns.insert(0, R)

	returns = torch.tensor(returns)

	if normalize:
		returns = (returns - returns.mean()) / returns.std()

	return returns

##

def update_policy(returns, log_prob_actions, optimizer):
	returns = returns.detach()
	loss = - (returns * log_prob_actions).sum()

	optimizer.zero_grad()
	loss.backward()
	optimizer.step()
	return loss.item()
	
##

def evaluate(env, policy):
	policy.eval()
	done = False
	episode_reward = 0

	state = env.reset()
	while not done:
		state = torch.FloatTensor(state).unsqueeze(0)
		with torch.no_grad():
			action_pred = policy(state)
			action_prob = F.softmax(action_pred, dim=-1)
		action = torch.argmax(action_prob, dim = -1)
		state, reward, done, _, _ = env.step(action.item())
		episode_reward += reward

	return episode_reward

##

MAX_EPISODES = 500
DISCOUNT_FACTOR = 0.99
N_TRIALS = 25
REWARD_THRESHOLD = 475
PRINT_EVERY  = 1

train_rewards = []
test_rewards = []

for episode in range(1, MAX_EPISODES + 1):
	loss, train_reward = train(train_env, policy, optimizer, DISCOUNT_FACTOR)
#	print("episode: ", episode, "loss: ", loss, "train_reward: ", train_reward)

	test_reward = evaluate(test_env, policy)

	train_rewards.append(train_reward)
	test_rewards.append(test_reward)

	mean_train_rewards = np.mean(train_rewards[-N_TRIALS:])
	mean_test_rewards = np.mean(test_rewards[-N_TRIALS:])

	if episode % PRINT_EVERY == 0:
		print(f'| Episode: {episode:3} | Mean Train Rewards: {mean_train_rewards:5.1f} | Mean Test Rewards: {mean_test_rewards:5.1f} |')

	if mean_test_rewards >= REWARD_THRESHOLD:
		print(f'REACHED REWARD THRESHOLD IN {episode} episodes')
		break

##



# #tuple describing a transition between 2 states
# Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))
# 
# #ring buffer of recent transitions
# class ReplayMemory(object):
# 	def __init__(self, capacity):
# 		self.memory = dequeue([], maxlen=capacity)
# 
# 	#save a transition
# 	def push(self, *args):
# 		self.memory.append(Transition(*args))
# 
# 	def sample(self, batch_size):
# 		return random.sample(self.memory, batch_size)
# 
# 	def __len__(self):
# 		return len(self.memory)
# 


