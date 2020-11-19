"""Helper functions for navigating the Melee menus in ways that would be
cumbersome to do on your own. The goal here is to get you into the game
as easily as possible so you don't have to worry about it. Your AI should
concentrate on playing the game, not futzing with menus.
"""
from melee import enums
import math
import time

class MenuHelper():

    def __init__(self, controller_1,
                        controller_2,
                        character_1_selected,
                        character_2_selected,
                        stage_selected,
                        connect_code,
                        autostart=False,
                        swag=True,
                        make_cpu=False,
                        level=1,
                        verbose=False):
        """Siplified menu helper function to get you through the menus and into a game

        Does everything for you but play the game. Gets you to the right menu screen, picks
        your character, chooses the stage, enters connect codes, etc...

        Args:
            gamestate (gamestate.GameState): The current GameState for this frame
            controller_1 (controller.Controller): A Controller object that the bot will press buttons on
            controller_2 (controller.Controller): A Controller object that the bot will press buttons on
            character_1_selected (enums.Character): The character that controller_1 will play as
            character_2_selected (enums.Character): The character that controller_2 will play as
            stage_selected (enums.Stage): The stage your bot will choose to play on
            connect_code (str): The connect code to direct match with. Leave blank for VS mode.
            cpu_level (int): What CPU level to set this to. 0 for human/bot controlled.
            costume (int): Costume index chosen
            autostart (bool): Automatically start the game when it's ready.
                Useful for BotvBot matches where no human is there to start it.
            swag (bool): What it sounds like
            make_cpu (bool): Whether player on port 2 should be CPU or not
            level (int): Level of CPU to set. Only valid if make_cpu
            verbose (bool): Whether to log important intermediate info
        """
        self.controller_1 = controller_1
        self.controller_2 = controller_2
        self.character_1_selected = character_1_selected
        self.character_2_selected = character_2_selected
        self.stage_selected = stage_selected
        self.connect_code = connect_code
        self.autostart = autostart
        self.swag = swag
        self.make_cpu = make_cpu
        self.level = level
        self.verbose = verbose
        self.name_tag_index = 0
        self.inputs_live = False
        self.cpu_toggled = False
        self.cpu_level_toggled = False
        self.cpu_level = -1
        self.cpu_level_pressed = False
        self.cpu_level_released = False

    def step(self, gamestate):
        """
        Makes all the necessary controller button presses to advance the menu to the desired final state
        given the current frame

        Args:
            gamestate (gamestate.GameState): The current gamestate
        """
        if self.level not in range(1, 10):
            raise ValueError("CPU level must be in [1, 9] but {} was specified".format(self.level))

        # If we're at the character select screen, choose our character
        if gamestate.menu_state in [enums.Menu.CHARACTER_SELECT, enums.Menu.SLIPPI_ONLINE_CSS]:
            if gamestate.submenu == enums.SubMenu.NAME_ENTRY_SUBMENU:
                self.name_tag_index = self.enter_direct_code(gamestate=gamestate,
                                                           controller=self.controller_1,
                                                           connect_code=self.connect_code,
                                                           index=self.name_tag_index)
            else:
                if self.verbose:
                    print("Player {} selecting character {}".format(self.controller_1.port, self.character_1_selected))
                self.choose_character(character=self.character_1_selected,
                                            gamestate=gamestate,
                                            controller=self.controller_1,
                                            rand=True,
                                            swag=self.swag,
                                            start=False,
                                            make_cpu=False,
                                            level=self.level)

                if self.verbose:
                    print("Player {} selecting character {}".format(self.controller_2.port, self.character_2_selected))
                self.choose_character(character=self.character_2_selected,
                                            gamestate=gamestate,
                                            controller=self.controller_2,
                                            rand=True,
                                            swag=False,
                                            start=self.autostart,
                                            make_cpu=self.make_cpu,
                                            level=self.level)

        # If we're at the postgame scores screen, spam START
        elif gamestate.menu_state == enums.Menu.POSTGAME_SCORES:
            self.skip_postgame(controller=self.controller_1)
        # If we're at the stage select screen, choose a stage
        elif gamestate.menu_state == enums.Menu.STAGE_SELECT:
            self.choose_stage(gamestate, self.controller_1)
        elif gamestate.menu_state == enums.Menu.MAIN_MENU:
            if self.connect_code:
                self.choose_direct_online(gamestate=gamestate, controller=self.controller_1)
            else:
                self.choose_versus_mode(gamestate=gamestate, controller=self.controller_1)

    def enter_direct_code(self, gamestate, controller, connect_code, index):
        """At the nametag entry screen, enter the given direct connect code and exit

        Args:
            gamestate (gamestate.GameState): The current GameState for this frame
            controller (controller.Controller): A Controller object to press buttons on
            connect_code (str): The connect code to direct match with. Leave blank for VS mode.
            index (int): Current name tag index

        Returns:
            new index (incremented if we entered a new character)
        """
        # The name entry screen is dead for the first few frames
        #   So if the first character is A, then the input can get eaten
        #   Account for this by making sure we can move off the letter first
        if gamestate.menu_selection != 45:
            self.inputs_live = True

        if not self.inputs_live:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return index

        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return index

        if len(connect_code) == index:
            controller.press_button(enums.Button.BUTTON_START)
            return index

        target_character = connect_code[index]
        target_code = 45
        column = "ABCDEFGHIJ".find(target_character)
        if column != -1:
            target_code = 45 - (column * 5)
        column = "KLMNOPQRST".find(target_character)
        if column != -1:
            target_code = 46 - (column * 5)
        column = "UVWXYZ   #".find(target_character)
        if column != -1:
            target_code = 47 - (column * 5)
        column = "0123456789".find(target_character)
        if column != -1:
            target_code = 48 - (column * 5)

        if gamestate.menu_selection == target_code:
            controller.press_button(enums.Button.BUTTON_A)
            return index + 1

        if gamestate.menu_selection == 57:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return index

        if gamestate.menu_selection < target_code:
            diff = target_code - gamestate.menu_selection
            if diff < 5:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            else:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
        else:
            diff = target_code - gamestate.menu_selection
            if diff > 5:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            else:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)

        return index

    def choose_character(self, character, gamestate, controller, rand=True, swag=False, start=False, make_cpu=False, level=1):
        """Choose a character from the character select menu

        Args:
            character (enums.Character): The character you want to pick
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller object to press buttons on
            rand (bool): Pick random until you get the character (makes this robust to pertubations in the character layout screen)
            start (bool): Automatically start the match when it's ready
            make_cpu (bool): Whether this selected character should be a CPU
            level (int): The level of CPU to set. Only valid if make_cpu

        Note:
            Intended to be called each frame while in the character select menu

        Note:
            All controller cursors must be above the character level for this
            to work. The match won't start otherwise.
        """
        # Figure out where the character is on the select screen
        # NOTE: This assumes you have all characters unlocked
        # Positions will be totally wrong if something is not unlocked
        controlling_port = controller.port
        if controlling_port not in gamestate.player:
            controller.release_all()
            return

        ai_state = gamestate.player[controlling_port]

        # Discover who is the opponent
        opponent_state = None
        for i, player in gamestate.player.items():
            # TODO For now, just assume they're the first controller port that isn't us
            if i != controlling_port:
                opponent_state = player
                break

        cursor_x, cursor_y = ai_state.cursor_x, ai_state.cursor_y
        coin_down = ai_state.coin_down
        character_selected = ai_state.character_selected

        isSlippiCSS = False
        if gamestate.menu_state == enums.Menu.SLIPPI_ONLINE_CSS:
            cursor_x, cursor_y = gamestate.player[1].cursor_x, gamestate.player[1].cursor_y
            isSlippiCSS = True
            character_selected = gamestate.player[1].character_selected
        if isSlippiCSS:
            swag = True

        row = enums.from_internal(character) // 9
        column = enums.from_internal(character) % 9
        #The random slot pushes the bottom row over a slot, so compensate for that
        if row == 2:
            column = column+1
        #re-order rows so the math is simpler
        row = 2-row

        #Go to the random character
        if rand:
            row = 0
            column = 0

        #Height starts at 1, plus half a box height, plus the number of rows
        target_y = 1 + 3.5 + (row * 7.0)
        #Starts at -32.5, plus half a box width, plus the number of columns
        #NOTE: Technically, each column isn't exactly the same width, but it's close enough
        target_x = -32.5 + 3.5 + (column * 7.0)
        #Wiggle room in positioning character
        wiggleroom = 1.5

        # Set our CPU level correctly
        if character_selected == character and (coin_down or cursor_y<0) and make_cpu \
            and (level != self.cpu_level) or self.cpu_level_toggled:
            if self.verbose:
                print("Working on CPU")
            # Need to toggle controller input to be a CPU
            if not self.cpu_toggled:
                if self.verbose:
                    print("Making cpu")
                t_x, t_y = -45 + 15 * controlling_port, -2.5
                room = 1.0
                # If hand isn't over toggle, move it there
                if cursor_x > t_x + room or cursor_x < t_x - room or cursor_y > t_y + room or cursor_y < t_y - room:
                    controller.release_button(enums.Button.BUTTON_A)
                    #Move up if we're too low
                    if cursor_y < t_y - room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
                    #Move down if we're too high
                    elif cursor_y > t_y + room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
                    #Move right if we're too left
                    elif cursor_x < t_x - room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
                    #Move left if we're too right
                    elif cursor_x > t_x + room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
                    return
                # else press/release A to select cpu
                else:
                    if self.verbose:
                        print("over cpu toggle")
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)

                    # Press and release must happen on two different frames to be properly read by dolphin
                    if controller.prev.button[enums.Button.BUTTON_A] == False:
                        # Pressing
                        controller.press_button(enums.Button.BUTTON_A)
                        return
                    else:
                        # Pressed on previous frame so release now
                        controller.release_button(enums.Button.BUTTON_A)
                        self.cpu_toggled = True
                        return

            # CPU is toggled but level slider is not selected 
            elif make_cpu and not self.cpu_level_toggled:
                if self.verbose:
                    print('finding cpu level slider')
                t_x, t_y = -45 + 15 * controlling_port, -14.5
                room = 0.5
                # If hand isn't over toggle, move it there
                if cursor_x > t_x + room or cursor_x < t_x - room or cursor_y > t_y + room or cursor_y < t_y - room:
                    controller.release_button(enums.Button.BUTTON_A)
                    #Move up if we're too low
                    if cursor_y < t_y - room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
                    #Move down if we're too high
                    elif cursor_y > t_y + room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
                    #Move right if we're too left
                    elif cursor_x < t_x - room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
                    #Move left if we're too right
                    elif cursor_x > t_x + room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
                    return
                # Select slider by pressing A
                else:
                    if self.verbose:
                        print("found cpu toggle")
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)
                    controller.press_button(enums.Button.BUTTON_A)
                    self.cpu_level_toggled = True
                    return
            
            # Slidder is selected but level needs to be changed
            elif make_cpu and self.cpu_level_toggled and self.cpu_level != level:
                if self.verbose:
                    print('sliding cpu level toggle')
                # Only horizontal position matters for horizonal slider
                t_x = -46.75 + 15 * controlling_port + 1.23 * level

                # Small tolerance because level is very sensitive to slider position
                room = 0.1

                # If hand isn't over correct cpu level on slider so move it there
                if cursor_x > t_x + room or cursor_x < t_x - room: 
                    controller.release_button(enums.Button.BUTTON_A)
                    self.cpu_level_released = True
                    #Move right if we're too left
                    if cursor_x < t_x - room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 0.7, .5) # Note the finer movements
                    #Move left if we're too right
                    elif cursor_x > t_x + room:
                        controller.tilt_analog(enums.Button.BUTTON_MAIN, 0.3, .5) # Note the finer movements
                    return
                # Release CPU level slider as it's in correct position
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)

                    # Press and release must happen on two different frames to be properly read by dolphin
                    if not self.cpu_level_released:
                        if self.verbose:
                            print("releasing slider")
                        controller.release_button(enums.Button.BUTTON_A)
                        self.cpu_level_released = True
                        return
                    if not self.cpu_level_pressed:
                        if self.verbose:
                            print("pressing A")
                        controller.press_button(enums.Button.BUTTON_A)
                        self.cpu_level_pressed = True
                        return
                    else:
                        if self.verbose:
                            print("releasing A")
                        self.cpu_level = level
                        controller.release_button(enums.Button.BUTTON_A)
                        return
                        
        # We are already set, so let's taunt our opponent
        if character_selected == character and swag and not start:
            delta_x = 3 * math.cos(gamestate.frame / 1.5)
            delta_y = 3 * math.sin(gamestate.frame / 1.5)

            target_x = opponent_state.cursor_x + delta_x
            target_y = opponent_state.cursor_y + delta_y

            diff_x = abs(target_x - cursor_x)
            diff_y = abs(target_y - cursor_y)
            larger_magnitude = max(diff_x, diff_y)

            # Scale down values to between 0 and 1
            x = diff_x / larger_magnitude
            y = diff_y / larger_magnitude

            # Now scale down to be between .5 and 1
            if cursor_x < target_x:
                x = (x/2) + 0.5
            else:
                x = 0.5 - (x/2)
            if cursor_y < target_y:
                y = (y/2) + 0.5
            else:
                y = 0.5 - (y/2)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, x, y)
            return

        if character_selected == character and swag and isSlippiCSS:
            if gamestate.frame % 2 == 0:
                controller.release_all()
            else:
                controller.press_button(enums.Button.BUTTON_Y)
            return

        #We want to get to a state where the cursor is NOT over the character,
        # but it's selected. Thus ensuring the token is on the character
        isOverCharacter = abs(cursor_x - target_x) < wiggleroom and \
            abs(cursor_y - target_y) < wiggleroom

        #Don't hold down on B, since we'll quit the menu if we do
        if controller.prev.button[enums.Button.BUTTON_B] == True:
            controller.release_button(enums.Button.BUTTON_B)
            return

        #If character is selected, and we're in of the area, and coin is down, then we're good
        if (character_selected == character) and coin_down:
            if gamestate.frame % 2 == 0:
                controller.release_all()
                return
            if start and (gamestate.ready_to_start == 0):
                controller.press_button(enums.Button.BUTTON_START)
                return
            else:
                controller.release_all()
                return

        #release start in addition to anything else
        controller.release_button(enums.Button.BUTTON_START)

        #If we're in the right area, select the character
        if isOverCharacter:
            #If we're over the character, but it isn't selected,
            #   then the coin must be somewhere else.
            #   Press B to reclaim the coin

            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)

            # The slippi menu doesn't have a coin down. We can make-do
            if isSlippiCSS and (character_selected != character):
                if gamestate.frame % 5 == 0:
                    controller.press_button(enums.Button.BUTTON_B)
                    controller.release_button(enums.Button.BUTTON_A)
                    return
                else:
                    controller.press_button(enums.Button.BUTTON_A)
                    controller.release_button(enums.Button.BUTTON_B)
                    return

            if (character_selected != character) and coin_down:
                controller.press_button(enums.Button.BUTTON_B)
                controller.release_button(enums.Button.BUTTON_A)
                return
            #Press A to select our character
            else:
                if controller.prev.button[enums.Button.BUTTON_A] == False:
                    controller.press_button(enums.Button.BUTTON_A)
                    return
                else:
                    controller.release_button(enums.Button.BUTTON_A)
                    return
        else:
            #Move in
            controller.release_button(enums.Button.BUTTON_A)
            #Move up if we're too low
            if cursor_y < target_y - wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
                return
            #Move down if we're too high
            if cursor_y > target_y + wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
                return
            #Move right if we're too left
            if cursor_x < target_x - wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
                return
            #Move left if we're too right
            if cursor_x > target_x + wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
                return
        controller.release_all()

    def choose_stage(self, gamestate, controller):
        """Choose a stage from the stage select menu

        Intended to be called each frame while in the stage select menu

        Args:
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller object to press
        """
        if gamestate.frame < 20:
            controller.release_all()
            return
        target_x, target_y = 0, 0
        if self.stage_selected == enums.Stage.BATTLEFIELD:
            target_x, target_y = 1, -9
        if self.stage_selected == enums.Stage.FINAL_DESTINATION:
            target_x, target_y = 6.7, -9
        if self.stage_selected == enums.Stage.DREAMLAND:
            target_x, target_y = 12.5, -9
        if self.stage_selected == enums.Stage.POKEMON_STADIUM:
            target_x, target_y = 15, 3.5
        if self.stage_selected == enums.Stage.YOSHIS_STORY:
            target_x, target_y = 3.5, 15.5
        if self.stage_selected == enums.Stage.FOUNTAIN_OF_DREAMS:
            target_x, target_y = 10, 15.5
        if self.stage_selected == enums.Stage.RANDOM_STAGE:
            target_x, target_y = -13.5, 3.5

        #Wiggle room in positioning cursor
        wiggleroom = 1.5
        #Move up if we're too low
        if gamestate.stage_select_cursor_y < target_y - wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            return
        #Move downn if we're too high
        if gamestate.stage_select_cursor_y > target_y + wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return
        #Move right if we're too left
        if gamestate.stage_select_cursor_x < target_x - wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return
        #Move left if we're too right
        if gamestate.stage_select_cursor_x > target_x + wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
            return

        #If we get in the right area, press A
        controller.press_button(enums.Button.BUTTON_A)

    def skip_postgame(self, controller):
        """ Spam the start button """
        #Alternate pressing start and letting go
        if controller.prev.button[enums.Button.BUTTON_START] == False:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_button(enums.Button.BUTTON_START)

    def change_controller_status(self, controller, gamestate, targetport, port, status, character=None):
        """Switch a given player's controller to be of the given state

        Note:
            There's a condition on this you need to know. The way controllers work
            in Melee, if a controller is plugged in, only that player can make the status
            go to uplugged. If you've ever played Melee, you probably know this. If your
            friend walks away, you have to press the A button on THEIR controller. (or
            else actually unplug the controller) No way around it."""
        ai_state = gamestate.player[controller.port]
        target_x, target_y = 0, -2.2
        if targetport == 1:
            target_x = -31.5
        if targetport == 2:
            target_x = -16.5
        if targetport == 3:
            target_x = -1
        if targetport == 4:
            target_x = 14
        wiggleroom = 1.5

        correctcharacter = (character is None) or \
            (character == gamestate.player[targetport].character_selected)

        #if we're in the right state already, do nothing
        if gamestate.player[targetport].controller_status == status and correctcharacter:
            controller.release_all()
            return

        #Move up if we're too low
        if ai_state.cursor_y < target_y - wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            return
        #Move downn if we're too high
        if ai_state.cursor_y > target_y + wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return
        #Move right if we're too left
        if ai_state.cursor_x < target_x - wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return
        #Move left if we're too right
        if ai_state.cursor_x > target_x + wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
            return

        #If we get in the right area, press A until we're in the right state
        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)
        if not controller.prev.button[enums.Button.BUTTON_A]:
            controller.press_button(enums.Button.BUTTON_A)
        else:
            controller.release_button(enums.Button.BUTTON_A)

    def choose_versus_mode(self, gamestate, controller):
        """Helper function to bring us into the versus mode menu

        Args:
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller to press buttons on
        """
        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return

        if gamestate.menu_state == enums.Menu.MAIN_MENU:
            if gamestate.submenu == enums.SubMenu.MAIN_MENU_SUBMENU:
                if gamestate.menu_selection == 1:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            elif gamestate.submenu == enums.SubMenu.VS_MODE_SUBMENU:
                if gamestate.menu_selection == 0:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            else:
                controller.press_button(enums.Button.BUTTON_B)
        elif gamestate.menu_state == enums.Menu.PRESS_START:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_all()

    def choose_direct_online(self, gamestate, controller):
        """Helper function to bring us into the direct connect online menu

        Args:
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller to press buttons on
        """
        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return
        if gamestate.menu_state == enums.Menu.MAIN_MENU:
            if gamestate.submenu == enums.SubMenu.ONLINE_PLAY_SUBMENU:
                if gamestate.menu_selection == 2:
                    controller.press_button(enums.Button.BUTTON_A)
                elif gamestate.menu_selection == 3:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            elif gamestate.submenu == enums.SubMenu.MAIN_MENU_SUBMENU:
                controller.press_button(enums.Button.BUTTON_A)
            elif gamestate.submenu == enums.SubMenu.ONEP_MODE_SUBMENU:
                if gamestate.menu_selection == 2:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)

            elif gamestate.submenu == enums.SubMenu.NAME_ENTRY_SUBMENU:
                pass
            else:
                controller.press_button(enums.Button.BUTTON_B)
        elif gamestate.menu_state == enums.Menu.PRESS_START:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_all()

    def print_location(self, gamestate, controller):
        if controller.port not in gamestate.player:
            return

        my_state = gamestate.player[controller.port]

        cursor_x, cursor_y = my_state.cursor_x, my_state.cursor_y

        print("My location ({}, {})".format(cursor_x, cursor_y))