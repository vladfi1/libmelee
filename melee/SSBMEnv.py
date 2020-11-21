import gym, melee, sys, signal, time
from ray.rllib.env import MultiAgentEnv
from gym import error, spaces, utils
from gym.utils import seeding
import numpy as np 
from melee import enums

"""
Gym compatible env for libmelee (an RL framework for SSBM)

Attr:
    - 
"""
SLIPPI_ADDRESS = "127.0.0.1"
SLIPPI_PORT=51441
PLAYER_PORT=1
OP_PORT=2
CONNECT_CODE=""

# TODO: allow increasable bot difficulty
# FIXME: getting error that gym has no env attr
# FIXME: configparser.NoSectionError: No section: 'Core' how did we fix this earlier?
"""
BUTTON_A = "A"
BUTTON_B = "B"
BUTTON_X = "X"
BUTTON_Y = "Y"
BUTTON_Z = "Z"
BUTTON_L = "L"
BUTTON_R = "R"
BUTTON_START = "START"
BUTTON_D_UP = "D_UP"
BUTTON_D_DOWN = "D_DOWN"
BUTTON_D_LEFT = "D_LEFT"
BUTTON_D_RIGHT = "D_RIGHT"
#Control sticks considered "buttons" here
BUTTON_MAIN = "MAIN"
BUTTON_C = "C"
Action space: [BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y, BUTTON_Z, BUTTON_L, BUTTON_R, BUTTON_D_UP, BUTTON_D_DOWN, BUTTON_D_LEFT, BUTTON_D_RIGHT,
                BUTTON_A_R, BUTTON_B_R, BUTTON_X_R, BUTTON_Y_R, BUTTON_Z_R, BUTTON_L_R, BUTTON_R_R, BUTTON_D_UP_R, BUTTON_D_DOWN_R, BUTTON_D_LEFT_R, BUTTON_D_RIGHT_R,
                BUTTON_MAIN (0, 0), BUTTON_MAIN (0.5, 0), BUTTON_MAIN (0, 0.5), BUTTON_MAIN (1, 0), BUTTON_MAIN (0, 1), BUTTON_MAIN (1, 0.5), BUTTON_MAIN (0.5, 1), BUTTON_MAIN (1, 1),
                BUTTON_C (0, 0), BUTTON_C (0.5, 0), BUTTON_C (0, 0.5), BUTTON_C (1, 0), BUTTON_C (0, 1), BUTTON_C (1, 0.5), BUTTON_C (0.5, 1), BUTTON_C (1, 1)]

Observation space: [p1_char, p1_x, p1_y, p1_percent, p1_shield, p1_facing, p1_action_enum_value, p1_action_frame, p1_invulnerable, p1_invulnerable_left, p1_hitlag, p1_hitstun_frames_left, p1_jumps_left, p1_on_ground, p1_speed_air_x_self,
                    p1_speed_y_self, p1_speed_x_attack, p1_speed_y_attack, p1_speed_ground_x_self, distance_btw_players, ...p2 same attr...]
"""

buttons = [enums.Button.BUTTON_A, enums.Button.BUTTON_B, enums.Button.BUTTON_X, enums.Button.BUTTON_Y, enums.Button.BUTTON_Z, 
               enums.Button.BUTTON_L, enums.Button.BUTTON_R, enums.Button.BUTTON_D_UP, enums.Button.BUTTON_D_DOWN, enums.Button.BUTTON_D_LEFT, 
               enums.Button.BUTTON_D_RIGHT]
intervals = [(0, 0), (0.5, 0), (0, 0.5), (1, 0), (0, 1), (1, 0.5), (0.5, 1), (1, 1)]


class SSBMEnv(MultiAgentEnv):
    DOLPHIN_SHUTDOWN_TIME = 5
    metadata = {'render.modes': ['human']}

    
    """
    SSBMEnv Constructor

    Attr:
        - self.logger: log useful data in csv
        - self.console: console to communicate with slippi dolphin
        - self.symmetric: False if one agent is bot
        - self.ctrlr: controller for char1
        - self.ctrlr_op: controller for char2 (could be cpu bot)
        - 

    Args:
        - dolphin_exe_path: path to dolphin exe
        - ssbm_iso_path: path to ssbm iso
        - char1, char2: melee.Character enum
        - stage: where we playin?
        - symmetric: True if we are training policies for both char1 and char2
                     else char2 is cpu bot
        - cpu_level: if symmetric=False this is the level of the cpu
        - log: are we logging stuff?
        - reward_func: custom reward function should take two gamestate objects as input and output a tuple
                       containing the reward for the player and opponent
    """
    def __init__(self, dolphin_exe_path, ssbm_iso_path, char1=melee.Character.FOX, char2=melee.Character.FALCO, 
                stage=melee.Stage.FINAL_DESTINATION, symmetric=False, cpu_level=1, log=False, reward_func=None, render=False):
        self.dolphin_exe_path = dolphin_exe_path
        self.ssbm_iso_path = ssbm_iso_path
        self.char1 = char1
        self.char2 = char2
        self.stage = stage
        self.symmetric = symmetric
        self.cpu_level = cpu_level
        self.reward_func = reward_func
        self.render = render
        self.logger = melee.Logger()
        self.log = log
        self.console = None
        self._is_dolphin_running = False

        self.get_reward = self._default_get_reward if not self.reward_func else self.reward_func
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(39,), dtype=np.float32)
        self.num_actions = (len(buttons) + len(intervals))*2 # num actions *2 for press/release and both joysticks
        self.action_space = spaces.Discrete(self.num_actions+1) # plus one for nop

    def _default_get_reward(self, prev_gamestate, gamestate): # define reward function
        # TODO: make sure that the correct damage goes to the correct player
        p1_reward = gamestate.player[self.ctrlr_op_port].percent-gamestate.player[self.ctrlr_port].percent
        p2_reward = gamestate.player[self.ctrlr_port].percent-gamestate.player[self.ctrlr_op_port].percent
        rewards = [p1_reward, p2_reward]

        joint_reward = {}
        for i, agent in enumerate(self.agents):
            joint_reward[agent] = rewards[i]
        
        return joint_reward


    def _get_state(self):
        """
        [p1_char, p1_x, p1_y, p1_percent, p1_shield, p1_facing, p1_action_enum_value, p1_action_frame, p1_invulnerable, 
         p1_invulnerable_left, p1_hitlag, p1_hitstun_frames_left, p1_jumps_left, p1_on_ground, p1_speed_air_x_self,
         p1_speed_y_self, p1_speed_x_attack, p1_speed_y_attack, p1_speed_ground_x_self, distance_btw_players, ...p2 same attr...]
        """
        # TODO: make sure the correct state goes to the correct player
        # I make the assumption that p1 is *always* a non-cpu and p2 is the cpu, if present
        p1 = self.gamestate.player[self.ctrlr_port]
        p2 = self.gamestate.player[self.ctrlr_op_port]
        p1_state = np.array([p1.character.value, p1.x, p1.y, p1.percent, p1.shield_strength, p1.facing, p1.action.value, p1.action_frame, 
                             float(p1.invulnerable), p1.invulnerability_left, float(p1.hitlag), p1.hitstun_frames_left, p1.jumps_left, 
                             float(p1.on_ground), p1.speed_air_x_self, p1.speed_y_self, p1.speed_x_attack, p1.speed_y_attack, p1.speed_ground_x_self, 
                             self.gamestate.distance, p2.character.value, p2.x, p2.y, p2.percent, p2.shield_strength, p2.facing, p2.action.value, p2.action_frame, 
                             float(p2.invulnerable), p2.invulnerability_left, float(p2.hitlag), p2.hitstun_frames_left, p2.jumps_left, 
                             float(p2.on_ground), p2.speed_air_x_self, p2.speed_y_self, p2.speed_x_attack, p2.speed_y_attack, p2.speed_ground_x_self])
        p1, p2 = p2, p1 
        p2_state = np.array([p1.character.value, p1.x, p1.y, p1.percent, p1.shield_strength, p1.facing, p1.action.value, p1.action_frame, 
                             float(p1.invulnerable), p1.invulnerability_left, float(p1.hitlag), p1.hitstun_frames_left, p1.jumps_left, 
                             float(p1.on_ground), p1.speed_air_x_self, p1.speed_y_self, p1.speed_x_attack, p1.speed_y_attack, p1.speed_ground_x_self, 
                             self.gamestate.distance, p2.character.value, p2.x, p2.y, p2.percent, p2.shield_strength, p2.facing, p2.action.value, p2.action_frame, 
                             float(p2.invulnerable), p2.invulnerability_left, float(p2.hitlag), p2.hitstun_frames_left, p2.jumps_left, 
                             float(p2.on_ground), p2.speed_air_x_self, p2.speed_y_self, p2.speed_x_attack, p2.speed_y_attack, p2.speed_ground_x_self])

        observations = [p1_state, p2_state]
        obs_dict = { agent_name : observations[i] for i, agent_name in enumerate(self.agents) }
        
        return obs_dict

    def _get_done(self):
        done =  self.gamestate.player[self.ctrlr_port].action.value <= 0xa or self.gamestate.player[self.ctrlr_op_port].action.value <= 0xa
        return {'__all__' : done }

    def _get_info(self):
        # TODO write frames skipped to info  (I think if we miss more than 6 frames between steps we might be in trouble)
        info = {}
        for agent in self.agents:
            info[agent] = {}
        return info
    
    def _perform_action(self, player, action_idx):
        if action_idx == 0:
            return
        ctrlr = self.ctrlr if player == 0 else self.ctrlr_op
        action_idx -= 1
        len_b = len(buttons)
        len_i = len(intervals)
        if action_idx < len_b: # button press
            ctrlr.press_button(buttons[action_idx])
        elif action_idx < len_b*2: # button release
            ctrlr.release_button(buttons[action_idx-len_b])
        elif action_idx < len_b*2 + len_i: # main joystick tilt
            tlt = intervals[action_idx-len_b*2]
            ctrlr.tilt_analog(enums.Button.BUTTON_MAIN, tlt[0], tlt[1])
        else: # c joystick tilt
            tlt = intervals[action_idx-(len_b*2+len_i)]
            ctrlr.tilt_analog(enums.Button.BUTTON_C, tlt[0], tlt[1])

    def _start_dolphin(self):
        self.console = melee.Console(path=self.dolphin_exe_path,
                                    slippi_address=SLIPPI_ADDRESS,
                                    slippi_port=SLIPPI_PORT,
                                    blocking_input=False,
                                    polling_mode=False,
                                    logger=self.logger)
        self.console.render = self.render
        self.symmetric = self.symmetric
        self.ctrlr = melee.Controller(console=self.console,
                                    port=PLAYER_PORT,
                                    type=melee.ControllerType.STANDARD)
        self.ctrlr_op = melee.Controller(console=self.console,
                                    port=OP_PORT,
                                    type=melee.ControllerType.STANDARD)
        self.console.run(iso_path=self.ssbm_iso_path)
        self._is_dolphin_running = True
        print("Connecting to console...")
        if not self.console.connect():
            print("ERROR: Failed to connect to the console.")
            raise RuntimeError("Failed to connect to console")

        # Plug our controller in
        print("Connecting controller to console...")
        if not self.ctrlr.connect():
            print("ERROR: Failed to connect the controller.")
            raise RuntimeError("Failed to connect to controller")
        if not self.ctrlr_op.connect():
            print("ERROR: Failed to connect the controller.")
            raise RuntimeError("Failed to connect to controller")
        print("Controllers connected")
    
    def _step_through_menu(self):
        # Step through main menu, player select, stage select scenes # TODO: include frame processing warning stuff
        self.gamestate = self.console.step()
        menu_helper = melee.MenuHelper(controller_1=self.ctrlr,
                                        controller_2=self.ctrlr_op,
                                        character_1_selected=self.char1,
                                        character_2_selected=self.char2,
                                        stage_selected=self.stage,
                                        connect_code=CONNECT_CODE,
                                        autostart=True,
                                        swag=False,
                                        make_cpu=not self.symmetric,
                                        level=self.cpu_level)
        
        while self.gamestate.menu_state not in [melee.Menu.IN_GAME, melee.Menu.SUDDEN_DEATH]:
            self.gamestate = self.console.step()
            menu_helper.step(self.gamestate)
            if self.log:
                self.logger.logframe(self.gamestate)
                self.logger.writeframe()
        
    def _stop_dolphin(self):
        print("STOPPING DOLPHIN")
        if self.console:
            self.console.stop()
            time.sleep(self.DOLPHIN_SHUTDOWN_TIME)
        self._is_dolphin_running = False
    
    def step(self, joint_action): # step should advance our state (in the form of the obs space)
        if set(joint_action.keys()).intersection(self.agents) != set(joint_action.keys()).union(self.agents):
            raise ValueError("Invalid agent in action dictionary!")

        # why do we need to do this?
        self.ctrlr_port = melee.gamestate.port_detector(self.gamestate, self.char1) 
        self.ctrlr_op_port = melee.gamestate.port_detector(self.gamestate, self.char2)

        if self.ctrlr_port != self.ctrlr.port or self.ctrlr_op_port != self.ctrlr_op.port:
            raise RuntimeError("Controller port inconsistency!")
        
        prev_gamestate = self.gamestate
        # perform actions
        for agent_idx, agent in enumerate(self.agents):
            action = joint_action[agent]
            self._perform_action(agent_idx, action)
        
        # step env
        self.gamestate = self.console.step()
        # collect reward
        reward = self.get_reward(prev_gamestate, self.gamestate)
        state = self._get_state()
        # determine if game is over and write extra info
        done = self._get_done()
        info = self._get_info()

        if done['__all__']:
            self._stop_dolphin()
        
        return state, reward, done, info
    

    def reset(self):    # TODO: should reset state to initial state, how to do this?
        if self._is_dolphin_running:
            self._stop_dolphin()

        # hashtag JustDolphinThings
        self._start_dolphin()
        self._step_through_menu()

        if self.symmetric:
            self.agents = ['ai_1', 'ai_2']
        else:
            self.agents = ['ai_1']

        self.ctrlr_port = melee.gamestate.port_detector(self.gamestate, self.char1) 
        self.ctrlr_op_port = melee.gamestate.port_detector(self.gamestate, self.char2)
        
        if self.ctrlr_port != self.ctrlr.port or self.ctrlr_op_port != self.ctrlr_op.port:
            raise RuntimeError("Controller port inconsistency!")
        
        # Return initial observation
        joint_obs = self._get_state()
        return joint_obs

    
    def render(self, mode='human', close=False):    # FIXME: changing this parameter does nothing rn??
        self.console.render = True
    

if __name__ == "__main__":
    import time
    import argparse
    parser = argparse.ArgumentParser(description='Example of Gym Wrapper in action')
    parser.add_argument('--dolphin_executable_path', '-e', default=None,
                        help='The directory where dolphin is')
    parser.add_argument('--iso_path', '-i', default="~/SSMB.iso",
                        help='Full path to Melee ISO file')
    parser.add_argument('--cpu', '-c', action='store_true',
                        help='Whether to set oponent as CPU')
    parser.add_argument('--cpu_level', '-l', type=int, default=3,
                        help='Level of CPU. Only valid if cpu is true')

    args = parser.parse_args()

    ssbm_env = SSBMEnv(args.dolphin_executable_path, args.iso_path, symmetric=not args.cpu, cpu_level=args.cpu_level, log=True, render=True)
    obs = ssbm_env.reset()

    start_time = time.time()
    done = False
    while not done:
        curr_time = time.time() - start_time
        print(">>>>>", curr_time)
        if curr_time > 18:
            start_time = time.time()
            ssbm_env.reset()
        
        # Perform first part of upsmash
        joint_action = {'ai_1' : 35}
        if not args.cpu:
            joint_action['ai_2'] = 0
        obs, reward, done, info = ssbm_env.step(joint_action)
        done = done['__all__']

        # Perform second part of upsmash
        if not done:
            joint_action = {'ai_1' : 31}
            if not args.cpu:
                joint_action['ai_2'] = 0
            obs, reward, done, info = ssbm_env.step(joint_action)
            done = done['__all__']
