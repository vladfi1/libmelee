""" Gamestate is a single snapshot in time of the game that represents all necessary information
        to make gameplay decisions
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

import melee
from melee import enums

@dataclass(slots=True, unsafe_hash=True)
class Position:
    """Dataclass for position types. Has (x, y) coords."""
    x: np.float32 = np.float32(0)
    y: np.float32 = np.float32(0)

Speed = Position
Cursor = Position

@dataclass(slots=True)
class ECB:
    """ECBs (Environmental collision box) info. It's a diamond with four points that define it."""
    top: Position = field(default_factory=Position)
    bottom: Position = field(default_factory=Position)
    left: Position = field(default_factory=Position)
    right: Position = field(default_factory=Position)

@dataclass(slots=True)
class FoDPlatforms:
    """Dataclass for the platforms on the Fountain of Dreams stage."""
    # Initial values are the same each time, found by experimentation and
    # extrapolating backwards after the platforms start moving.
    left: np.float32 = np.float32(20)
    right: np.float32 = np.float32(28)

class WhispyBlowDirection(Enum):
    NONE = np.uint8(0)
    LEFT = np.uint8(1)
    RIGHT = np.uint8(2)

# https://github.com/project-slippi/slippi-wiki/blob/master/SPEC.md#stadium-transformations
class StadiumTransformationEvent(Enum):
    """Pokemon Stadium transformation event types"""
    FINISHED = 0
    INITIALIZE = 2
    ON_MONITOR = 3
    PREVIOUS_RECEDING = 4
    NEW_RISING = 5
    FINALIZE = 6

class StadiumTransformationType(Enum):
    """Pokemon Stadium transformation types"""
    FIRE = 3
    GRASS = 4
    NORMAL = 5
    ROCK = 6
    WATER = 9

@dataclass(slots=True)
class StadiumTransformation:
    """Current Pokemon Stadium transformation state"""
    event: StadiumTransformationEvent = StadiumTransformationEvent.FINISHED
    type: StadiumTransformationType = StadiumTransformationType.NORMAL

@dataclass(slots=True)
class GameState:
    """Represents the state of a running game of Melee at a given moment in time"""
    frame: int = -10000
    """int: The current frame number. Monotonically increases. Can be negative."""
    stage: enums.Stage = enums.Stage.FINAL_DESTINATION
    """enums.Stage: The current stage being played on"""

    # Stage-specific state
    whispy: Optional[WhispyBlowDirection] = None
    fod_platforms: Optional[FoDPlatforms] = None
    stadium_transformation: Optional[StadiumTransformation] = None

    menu_state: enums.Menu = enums.Menu.IN_GAME
    """enums.MenuState: The current menu scene, such as IN_GAME, or STAGE_SELECT"""
    submenu: enums.SubMenu = enums.SubMenu.UNKNOWN_SUBMENU
    """(enums.SubMenu): The current sub-menu"""
    players: dict[int, 'PlayerState'] = field(default_factory=dict)
    """(dict of int - gamestate.PlayerState): Dict of PlayerState objects. Key is controller port"""
    projectiles: list['Projectile'] = field(default_factory=list)
    """(list of Projectile): All projectiles (items) currently existing"""
    ready_to_start: bool = False
    """(bool): Is the 'ready to start' banner showing at the character select screen?"""
    is_teams: bool = False
    """(bool): Is this a teams game?"""
    distance: float = 0.0
    """(float): Euclidian distance between the two players. (or just Popo for climbers)"""
    menu_selection: int = 0
    """(int): The index of the selected menu item for when in menus."""
    startAt: str = ""
    """(string): Timestamp string of when the game started. Such as '2018-06-22T07:52:59Z'"""
    playedOn: str = ""
    """(string): Platform the game was played on (values include dolphin, console, and network). Might be blank."""
    consoleNick: str = ""
    """(string): The name of the console the replay was created on. Might be blank."""
    _newframe: bool = True
    custom: dict = field(default_factory=dict)
    """(dict): Custom fields to be added by the user"""

@dataclass(slots=True)
class UnknownAnimation:
    value: int = -1

@dataclass(slots=True)
class PlayerState:
    """ Represents the state of a single player """
    # This value is what the character currently is IN GAME
    #   So this will have no meaning while in menus
    #   Also, this will change dynamically if you change characters
    #       IE: Shiek/Zelda
    character: enums.Character = enums.Character.UNKNOWN_CHARACTER
    """(enum.Character): The player's current character"""
    # This value is what character is selected at the character select screen
    #   Don't use this value when in-game
    character_selected: enums.Character = enums.Character.UNKNOWN_CHARACTER
    position: Position = field(default_factory=Position)
    """(Position): x, y character position"""
    percent: int = 0
    """(int): The player's damage"""
    shield_strength: float = 60.
    """(float): The player's shield strength (max 60). Shield breaks at 0"""
    is_powershield: bool = False
    """(bool): Is the current action a Powershield? (not directly determinable via action states)"""
    stock: int = 0
    """(int): The player's remaining stock count"""
    facing: bool = True
    """(bool): Is the character facing right? (left is False). Characters in Melee must always be facing left or right"""
    action: enums.Action | UnknownAnimation = field(default_factory=UnknownAnimation)
    """(enum.Action): The current action (or animation) the character is in"""
    action_frame: int = 0
    """(int): What frame of the Action is the character in? Indexed from 1."""
    invulnerable: bool = False
    """(bool): Is the player invulnerable?"""
    invulnerability_left: int = 0
    """(int): How many frames of invulnerability are left."""
    hitlag_left: int = 0
    """(bool): How many more frames of hitlag there is"""
    hitstun_frames_left: int = 0
    """(int): How many more frames of hitstun there is"""
    jumps_left: int = 0
    """(int): Number of jumps available. Including ground jump. Will be 2 for most characters on ground."""
    on_ground: bool = True
    """(bool): Is the character on the ground?"""
    speed_air_x_self: float = 0
    """(float): Self-induced horizontal air speed"""
    speed_y_self: float = 0
    """(float): Self-induced vertical speed"""
    speed_x_attack: float = 0
    """(float): Attack-induced horizontal speed"""
    speed_y_attack: float = 0
    """(float): Attack-induced vertical speed"""
    speed_ground_x_self: float = 0
    """(float): Self-induced horizontal ground speed"""
    nana: Optional['PlayerState'] = None
    """(enums.PlayerState): Additional player state for Nana, if applicable.
            If the character is not Ice Climbers, Nana will be None.
            Will also be None if this player state is Nana itself.
            Lastly, the secondary climber is called 'Nana' here, regardless of the costume used."""
    cursor: Cursor = field(default_factory=Cursor)
    """(Position): x, y cursor position"""
    coin_down: bool = False
    """(bool): Is the player's character selection coin placed down? (Does not work in Slippi selection screen)"""
    controller_status: enums.ControllerStatus = enums.ControllerStatus.CONTROLLER_UNPLUGGED
    """(enums.ControllerStatus): Status of the player's controller."""
    off_stage: bool = False
    """(bool): Helper variable to say if the character is 'off stage'. """
    iasa: int = 0
    moonwalkwarning: bool = False
    """(bool): Helper variable to tell you that if you dash back right now, it'll moon walk"""
    controller_state: 'melee.ControllerState' = field(default_factory=lambda: melee.ControllerState())
    """(controller.ControllerState): What buttons were pressed for this character"""
    ecb: ECB = field(default_factory=ECB)
    ecb_right: tuple = (0, 0)
    """(float, float): Right edge of the ECB. (x, y) offset from player's center."""
    ecb_left: tuple = (0, 0)
    """(float, float): Left edge of the ECB. (x, y) offset from player's center."""
    ecb_top: tuple = (0, 0)
    """(float, float): Top edge of the ECB. (x, y) offset from player's center."""
    ecb_bottom: tuple = (0, 0)
    """(float, float): Bottom edge of the ECB. (x, y) offset from player's center."""
    costume: int = 0
    """(int): Index for which costume the player is wearing"""
    cpu_level: int = 0
    """(int): CPU level of player. 0 for a libmelee-controller bot or human player."""
    is_holding_cpu_slider: bool = False
    """(bool): Is the player holding the CPU slider in the character select screen?"""
    nickName: str = ""
    """(string): The in-game nickname for the player. Might be blank."""
    connectCode: str = ""
    """(string): The rollback connect code for the player. Might be blank."""
    displayName: str = ""
    """(string): The Slippi Online display name for the play. Might be blank"""
    team_id: int = 0
    """(int): The team ID of the player. This is different than costume, and only relevant during teams."""

@dataclass(slots=True)
class UnknownProjectileType:
    """ Represents an unknown projectile type """
    value: np.uint16

@dataclass(slots=True, unsafe_hash=True)
class Projectile:
    """ Represents the state of a projectile (items, lasers, etc...) """
    # frame: int = 0
    position: Position = field(default_factory=Position)
    """(Position): x, y projectile position"""
    speed: Speed = field(default_factory=Speed)
    """(Position): x, y projectile speed"""
    owner: int = -1
    """(int): Player port of the projectile's owner. -1 for no owner"""
    type: enums.ProjectileType | UnknownProjectileType = enums.ProjectileType.UNKNOWN_PROJECTILE
    """(enums.ProjectileType): Which actual projectile type this is"""
    expiration_frames: float = 0
    """(int): How long the item has been out"""
    subtype: int = 0
    """(int): The subtype of the item. Many projectiles have 'subtypes' that make them different. They're all different, so it's not an enum"""
    spawn_id: np.uint32 = np.uint32(0)

def port_detector(gamestate, character, costume):
    """Autodiscover what port the given character is on

    Slippi Online assigns us a random port when playing online. Find out which we are

    Returns:
        [1-4]: The given character belongs to the returned port
        0: We don't know.

    Args:
        gamestate: Current gamestate
        character: The character we know we picked
        costume: Costume index we picked
    """
    detected_port = 0
    for i, player in gamestate.players.items():
        if player.character == character and player.costume == costume:
            if detected_port > 0:
                return 0
            detected_port = i

    return detected_port
