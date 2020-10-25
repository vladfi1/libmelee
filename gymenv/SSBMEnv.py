import gym, melee, sys, signal
from gym import error, spaces, utils
from gym.utils import seeding

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

class SSBMEnv(gym.env):
    metadata = {'render.modes': ['human']}

    def default_get_reward(prev_gamestate, gamestate): # define reward function
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
                       containing the reward for the first agent and second agent
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
                                                swag=True)
            if self.log:
                self.logger.logframe(self.gamestate)
                self.logger.writeframe()

        self.get_reward = default_get_reward if not reward_func else reward_func

    def step(self, action): # step should advance our state (in the form of the obs space)
        prev_gamestate = self.gamestate
        # TODO: perform actions

        # step env
        self.gamestate = self.console.step()
        # collect reward
        reward = self.get_reward(prev_gamestate, self.gamestate)
        # TODO: determine if game is over

        return self.gamestate, reward, 

    # return the new state, reward, done, and extra info
    def reset(self):    # should reset state to initial stats
        
    
    def render(self, mode='human', close=False):    # should render current state on screen
        self.console.render = True
    