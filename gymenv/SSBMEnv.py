import gym, melee, sys, signal
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
PLAYER_PORT=2
OP_PORT=1
CONNECT_CODE=""

# TODO: allow increasable bot difficulty
# TODO: figure out size of action/obs space based on descretization
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


class SSBMEnv(gym.env):
    metadata = {'render.modes': ['human']}

    buttons = [enums.Button.BUTTON_A, enums.Button.BUTTON_B, enums.Button.BUTTON_X, enums.Button.BUTTON_Y, enums.Button.BUTTON_Z, 
               enums.Button.BUTTON_L, enums.Button.BUTTON_R, enums.Button.BUTTON_D_UP, enums.Button.BUTTON_D_DOWN, enums.Button.BUTTON_D_LEFT, 
               enums.Button.BUTTON_D_RIGHT]
    intervals = [(0, 0), (0.5, 0), (0, 0.5), (1, 0), (0, 1), (1, 0.5), (0.5, 1), (1, 1)]

    def _default_get_reward(prev_gamestate, gamestate): # define reward function
        return (gamestate.player[OP_PORT].percent-gamestate.player[PLAYER_PORT].percent, gamestate.player[PLAYER_PORT].percent-gamestate.player[OP_PORT].percent)

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
                stage=melee.Stage.FINAL_DESTINATION, symmetric=False, cpu_level=1, log=False, reward_func=None):
        self.logger = melee.Logger()
        self.log = log
        self.console = melee.Console(path=dolphin_exe_path,
                                    slippi_address=SLIPPI_ADDRESS,
                                    slippi_port=SLIPPI_PORT,
                                    blocking_input=False,
                                    polling_mode=False,
                                    logger=self.logger)
        self.console.render=False
        self.symmetric = symmetric
        self.ctrlr = melee.Controller(console=self.console,
                                    port=PLAYER_PORT,
                                    type=melee.ControllerType.STANDARD)
        if symmetric:
            self.ctrlr_op = melee.Controller(console=self.console,
                                       port=OP_PORT,
                                       type=melee.ControllerType.STANDARD)
        #else:
            # TODO: make self.ctrlr_op a computer controlled opponent
        # TODO: implement sigint stuff

        self.console.run(iso_path=ssbm_iso_path)
        print("Connecting to console...")
        if not self.console.connect():
            print("ERROR: Failed to connect to the console.")
            sys.exit(-1)
        # Plug our controller in
        print("Connecting controller to console...")
        if not self.ctrlr.connect():
            print("ERROR: Failed to connect the controller.")
            sys.exit(-1)
        if not self.ctrlr_op.connect():
            print("ERROR: Failed to connect the controller.")
            sys.exit(-1)
        print("Controllers connected")
        # Step through main menu, player select, stage select scenes # TODO: include frame processing warning stuff?
        print("In menu")
        self.gamestate = ""
        while self.gamestate not in [melee.Menu.IN_GAME, melee.Menu.SUDDEN_DEATH]:
            self.gamestate = self.console.step()
            melee.MenuHelper.menu_helper_simple(self.gamestate,
                                                controller_1=self.ctrlr,
                                                controller_2=self.ctrlr_op,
                                                port_1=PLAYER_PORT,
                                                port_2=OP_PORT,
                                                character_1_selected=char1,
                                                character_2_selected=char2,
                                                stage_selected=stage,
                                                connect_code=CONNECT_CODE,
                                                autostart=True,
                                                swag=True) # TODO: input one last argument to say whether ctrlr_op will be cpu
            if self.log:
                self.logger.logframe(self.gamestate)
                self.logger.writeframe()

        self.get_reward = _default_get_reward if not reward_func else reward_func
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(39,), dtype=np.float32)
        self.num_actions = (len(buttons) + len(intervals))*2 # num actions *2 for press/release and both joysticks
        self.action_space = spaces.Discrete(self.num_actions+1) # plus one for nop

    def _get_state(self):
        """
        [p1_char, p1_x, p1_y, p1_percent, p1_shield, p1_facing, p1_action_enum_value, p1_action_frame, p1_invulnerable, 
         p1_invulnerable_left, p1_hitlag, p1_hitstun_frames_left, p1_jumps_left, p1_on_ground, p1_speed_air_x_self,
         p1_speed_y_self, p1_speed_x_attack, p1_speed_y_attack, p1_speed_ground_x_self, distance_btw_players, ...p2 same attr...]
        """
        p1 = self.gamestate.player[PLAYER_PORT]
        p2 = self.gamestate.player[OP_PORT]
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
        return p1_state, p2_state

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
            ctrlr.tilt_analog(enums.BUTTON_MAIN, tlt[0], tlt[1])
        else: # c joystick tilt
            tlt = intervals[action_idx-(len_b*2+len_i)]
            ctrlr.tilt_analog(enums.BUTTON_C, tlt[0], tlt[1])


    def step(self, action): # step should advance our state (in the form of the obs space)
        prev_gamestate = self.gamestate
        # perform actions
        self._perform_action(0, action["player"])
        self._perform_action(1, action["player_op"])
        # step env
        self.gamestate = self.console.step()
        # collect reward
        reward = self.get_reward(prev_gamestate, self.gamestate)
        state = self._get_state()
        # determine if game is over and write extra info
        done = self.gamestate.player[PLAYER_PORT].action.value <= 0xa or self.gamestate.player[OP_PORT].action.value <= 0xa
        info = {} # TODO write frames skipped to info  (I think if we miss more than 6 frames between steps we might be in trouble)
        return (state[0], reward[0], done, info), (state[1], reward[1], done, info)

    def reset(self):    # should reset state to initial stats

    
    def render(self, mode='human', close=False):    # should render current state on screen
        self.console.render = True
    