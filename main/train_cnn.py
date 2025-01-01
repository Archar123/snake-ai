import os
import random
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv
#from stable_baselines3.common.monitor import Monitor
from gymnasium.wrappers import RecordEpisodeStatistics
from snake_game_custom_wrapper_cnn import SnakeEnv, ActionMasker

if torch.backends.mps.is_available():
    NUM_ENV = 32 * 2
else:
    NUM_ENV = 32
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def linear_schedule(initial_value, final_value=0.0):
    if isinstance(initial_value, str):
        initial_value = float(initial_value)
        final_value = float(final_value)
        assert (initial_value > 0.0)

    def scheduler(progress):
        return final_value + progress * (initial_value - final_value)

    return scheduler

def make_env(seed=0):
    def _init():
        env = SnakeEnv(seed=seed)
        env = ActionMasker(env, SnakeEnv.get_action_mask)
        #env = Monitor(env)
        #env.seed(seed)
        env = RecordEpisodeStatistics(env)
        return env
    return _init

def main():
    # Generate a list of random seeds for each environment.
    seed_set = set()
    while len(seed_set) < NUM_ENV:
        seed_set.add(random.randint(0, 1e9))

    # Create the Snake environment.
    env = DummyVecEnv([make_env(seed=s) for s in seed_set])

    if torch.backends.mps.is_available():
        lr_schedule = linear_schedule(2.5e-4, 2.5e-6)
        clip_range_schedule = linear_schedule(0.150, 0.025)
        # Instantiate a PPO agent using MPS (Metal Performance Shaders).
        model = MaskablePPO(
            "CnnPolicy",
            env,
            device="mps",
            verbose=1,
            n_steps=2048,
            batch_size=512,
            n_epochs=4,
            gamma=0.94,
            learning_rate=lr_schedule,
            clip_range=clip_range_schedule,
            tensorboard_log=LOG_DIR
        )
    else:
        lr_schedule = linear_schedule(2.5e-4, 2.5e-6)
        clip_range_schedule = linear_schedule(0.150, 0.025)
        # Instantiate a PPO agent using CUDA.
        model = MaskablePPO(
            "CnnPolicy",
            env,
            device="cuda",
            verbose=1,
            n_steps=2048,
            batch_size=512,
            n_epochs=4,
            gamma=0.94,
            learning_rate=lr_schedule,
            clip_range=clip_range_schedule,
            tensorboard_log=LOG_DIR
        )

    # Set the save directory
    if torch.backends.mps.is_available():
        save_dir = "trained_models_cnn_mps"
    else:
        save_dir = "trained_models_cnn"
    os.makedirs(save_dir, exist_ok=True)

    # Train the model
    model.learn(total_timesteps=1e6, use_masking=False)
    # Save the final model
    model.save(os.path.join(save_dir, "ppo_snake_final.zip"))

if __name__ == "__main__":
    main()