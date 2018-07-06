import numpy as np
import argparse
from sim4step import sim
import pickle
import os
import csv

class BayesGap(object):

	def __init__(self, args):

		self.policy_file = os.path.join(args.data_dir, args.policy_file)
		self.prev_arm_bounds_file = os.path.join(args.data_dir, args.arm_bounds_dir, str(args.round_idx-1) + '.pkl') # note this is for previous round
		self.prev_early_pred_file = os.path.join(args.data_dir, args.early_pred_dir, str(args.round_idx-1) + '.csv') # note this is for previous round
		self.arm_bounds_file = os.path.join(args.data_dir, args.arm_bounds_dir, str(args.round_idx) + '.pkl')
		self.next_batch_file = os.path.join(args.data_dir, args.next_batch_dir, str(args.round_idx) + '.csv')

		self.param_space = self.get_parameter_space()
		self.num_arms = self.param_space.shape[0]

		self.X = self.get_design_matrix(args.gamma)

		self.num_dims = self.X.shape[1]
		self.batch_size = args.bsize
		self.budget = args.budget # T in Alg. 1
		self.round_idx = args.round_idx

		self.eta = args.eta
		self.sigma = args.likelihood_std
		self.beta = args.beta
		self.epsilon = args.epsilon

		pass

	def get_design_matrix(self, gamma):

		from sklearn.kernel_approximation import (RBFSampler, Nystroem)
		param_space = self.param_space
		num_arms = self.num_arms

		feature_map_nystroem = Nystroem(gamma=gamma, n_components=num_arms, random_state=1)
		X = feature_map_nystroem.fit_transform(param_space)
		return X

	def run(self):
		"""
		Algorithm 1 of paper
		"""

		prev_arm_bounds_file = self.prev_arm_bounds_file
		prev_early_pred_file = self.prev_early_pred_file
		arm_bounds_file = self.arm_bounds_file
		next_batch_file = self.next_batch_file

		num_arms = self.num_arms
		batch_size = self.batch_size
		epsilon = self.epsilon
		X = self.X
		round_idx = self.round_idx
		param_space = self.param_space

		def find_J_t(carms):

			B_k_ts = []
			for k in range(num_arms):
				if k in carms:
					temp_upper_bounds = np.delete(upper_bounds, k)
					B_k_t = np.amax(temp_upper_bounds) 
					B_k_ts.append(B_k_t)
				else:
					B_k_ts.append(np.inf)

			B_k_ts = np.array(B_k_ts) - np.array(lower_bounds)
			J_t = np.argmin(B_k_ts)
			min_B_k_t = np.amin(B_k_ts)
			return J_t, min_B_k_t


		def find_j_t(carms, preselected_arm):

			U_k_ts = []
			for k in range(num_arms):
				if k in carms and k != preselected_arm:
					U_k_ts.append(upper_bounds[k])
				else:
					U_k_ts.append(-np.inf)

			j_t = np.argmax(np.array(U_k_ts))

			return j_t


		def get_confidence_diameter(k):

			return upper_bounds[k] - lower_bounds[k]

	
		if round_idx == 0:
			X_t = []
			Y_t = []
			proposal_arms = [] # useful for Eq (8) later
			proposal_gaps = []
			beta = self.beta
			upper_bounds, lower_bounds = self.get_posterior_bounds(beta)
			best_arm_params = None
		else:

			# load proposal_arms, proposal_gaps, X_t, Y_t, beta for previous round in bounds/<round_idx-1>.pkl
			with open(prev_arm_bounds_file, 'rb') as infile:
				proposal_arms, proposal_gaps, X_t, Y_t, beta = pickle.load(infile)
			
			# update beta for this round
			beta = beta * epsilon

			# get armidx of batch policies and early predictions for previous round in pred/<round_idx-1>.csv

			with open(prev_early_pred_file, 'r', encoding='utf-8-sig') as infile:
				reader = csv.reader(infile, delimiter=',')
				early_pred = np.asarray([list(map(float, row)) for row in reader])
			print(early_pred)

			batch_policies = early_pred[:, :3]
			batch_arms = [param_space.tolist().index(policy) for policy in batch_policies.tolist()]
			X_t.append(X[batch_arms])

			batch_rewards = early_pred[:, 4].reshape(-1, 1) # this corresponds to 5th column coz we are supposed to ignore the 4th column
			Y_t.append(batch_rewards)

			np_X_t = np.vstack(X_t)
			np_Y_t = np.vstack(Y_t)
			print(np_X_t.shape, np_Y_t.shape)
			upper_bounds, lower_bounds = self.get_posterior_bounds(beta, np_X_t, np_Y_t)

			J_prev_round = proposal_arms[round_idx-1]
			temp_upper_bounds = np.delete(upper_bounds, J_prev_round)
			B_k_t = np.amax(temp_upper_bounds) - lower_bounds[J_prev_round]
			proposal_gaps.append(B_k_t)
			best_arm = proposal_arms[np.argmin(np.array(proposal_gaps))]
			best_arm_params = param_space[best_arm]

		print('Round', round_idx)
		batch_arms = []
		candidate_arms = list(range(num_arms)) # an extension of Alg 1 to batch setting, don't select the arm again in same batch
		for batch_elem in range(batch_size):
			J_t, _ = find_J_t(candidate_arms)
			j_t = find_j_t(candidate_arms, J_t)
			s_J_t = get_confidence_diameter(J_t)
			s_j_t = get_confidence_diameter(j_t)
			a_t = J_t if s_J_t >= s_j_t else j_t

			if batch_elem == 0:
				proposal_arms.append(J_t)
			batch_arms.append(a_t)
			candidate_arms.remove(a_t)

		print('Policy indices selected for this round:', batch_arms)

		# save proposal_arms, proposal_gaps, X_t, Y_t, beta for current round in bounds/<round_idx>.pkl
		with open(arm_bounds_file, 'wb') as outfile:
			pickle.dump([proposal_arms, proposal_gaps, X_t, Y_t, beta], outfile)

		# save policies corresponding to batch_arms in batch/<round_idx>.csv
		batch_policies = [param_space[arm] for arm in batch_arms]
		with open(next_batch_file, 'w') as outfile:
			writer = csv.writer(outfile)
			writer.writerows(batch_policies)

		return best_arm_params

	def posterior_theta(self, X_t, Y_t):

		"""
		Eq. (4, 5)
		"""

		num_dims = self.num_dims
		sigma = self.sigma
		eta = self.eta
		prior_mean = np.zeros(num_dims)

		prior_theta_params = (prior_mean, eta * eta * np.identity(num_dims))

		if X_t is None:
			return prior_theta_params

		posterior_covar = np.linalg.inv(np.dot(X_t.T, X_t) / (sigma * sigma) + np.identity(num_dims) / (eta * eta))
		posterior_mean = np.linalg.multi_dot((posterior_covar, X_t.T, Y_t))/ (sigma * sigma) 

		posterior_theta_params = (np.squeeze(posterior_mean), posterior_covar)
		return posterior_theta_params


	def marginal_mu(self, posterior_theta_params):

		# marginal_mu denoted by rho_t

		# Note expected reward for each arm, mu_k = E[Y|theta] is another random variable

		X = self.X
		posterior_mean, posterior_covar = posterior_theta_params

		marginal_mean = np.dot(X, posterior_mean) # dimensions num_arms x num_dims
		marginal_var = np.sum(np.multiply(np.dot(X, posterior_covar), X), 1)

		marginal_mu_params = (marginal_mean, marginal_var)

		return marginal_mu_params

	def get_posterior_bounds(self, beta, X=None, Y=None):
		"""
		Returns upper and lower bounds for all arms at every time step.
		"""

		posterior_theta_params = self.posterior_theta(X, Y)
		marginal_mu_params = self.marginal_mu(posterior_theta_params)
		marginal_mean, marginal_var = marginal_mu_params

		upper_bounds = marginal_mean + beta * marginal_var
		lower_bounds = marginal_mean - beta * marginal_var

		return (upper_bounds, lower_bounds)


	def get_parameter_space(self):

		policies = np.genfromtxt(self.policy_file,
				delimiter=',', skip_header=0)

		return policies[:, :3]

def parse_args():
	"""
	Specifies command line arguments for the program.
	"""

	parser = argparse.ArgumentParser(description='Best arm identification using Bayes Gap.')

	parser.add_argument('--policy_file', nargs='?', default='policies_all.csv')
	parser.add_argument('--data_dir', nargs='?', default='data/')
	parser.add_argument('--arm_bounds_dir', nargs='?', default='bounds/')
	parser.add_argument('--early_pred_dir', nargs='?', default='pred/')
	parser.add_argument('--next_batch_dir', nargs='?', default='batch/')
	parser.add_argument('--round_idx', default=0, type=int)

	parser.add_argument('--seed', default=0, type=int,
						help='Seed for random number generators')
	parser.add_argument('--budget', default=10, type=int,
						help='Time budget')
	parser.add_argument('--bsize', default=48, type=int,
						help='batch size')
	parser.add_argument('--eta', default=100, type=float,
						help='standard deviation for the prior')
	parser.add_argument('--gamma', default=0.2, type=float,
						help='kernel bandwidth for Gaussian kernel')
	parser.add_argument('--likelihood_std', default=98, type=float,
						help='standard deviation for the likelihood std')
	parser.add_argument('--beta', default=1, type=float,
						help='initial exploration constant in Thm 1')
	parser.add_argument('--epsilon', default=1, type=float,
						help='decay constant for exploration')

	parser.add_argument('--sim_mode', nargs='?', default='lo')

	return parser.parse_args()


def main():

	args = parse_args()

	np.random.seed(args.seed)
	np.set_printoptions(threshold=np.inf)

	assert (os.path.exists(os.path.join(args.data_dir, args.arm_bounds_dir)))
	assert (os.path.exists(os.path.join(args.data_dir, args.early_pred_dir)))
	assert (os.path.exists(os.path.join(args.data_dir, args.next_batch_dir)))

	agent = BayesGap(args)
	best_arm_params = agent.run()

	if args.round_idx != 0:
		print('Best arm until round', args.round_idx-1, 'is', best_arm_params)
		lifetime_best_arm = sim(best_arm_params[0], best_arm_params[1], best_arm_params[2], mode=args.sim_mode, variance=False)
		print('Lifetime of current best arm as per thermal simulator:', lifetime_best_arm)
        
	# Log the best arm at the end of the experiment
	if args.round_idx == args.budget:
		log_path = os.path.join(args.data_dir, 'log.csv')
		with open(log_path, "a") as log_file:
         		log_file.write(',\n' + args.sim_mode + ',' +
                          str(args.gamma) + ',' + 
                          str(args.epsilon) + ',' +
                          str(args.beta) + ',' + 
                          str(args.likelihood_std) + ',' + 
                          str(args.seed) + ',' + 
                          str(lifetime_best_arm))


if __name__ == '__main__':

	main()
