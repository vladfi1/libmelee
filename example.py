#!/usr/bin/python3
import argparse
import signal
import sys
import melee
import time

# This example program demonstrates how to use the Melee API to run a console,
#   setup controllers, and send button presses over to a console

def check_port(value):
    ivalue = int(value)
    if ivalue < 1 or ivalue > 4:
        raise argparse.ArgumentTypeError("%s is an invalid controller port. \
                                         Must be 1, 2, 3, or 4." % value)
    return ivalue

parser = argparse.ArgumentParser(description='Example of libmelee in action')
parser.add_argument('--port', '-p', type=check_port,
                    help='The controller port (1-4) your AI will play on',
                    default=1)
parser.add_argument('--opponent', '-o', type=check_port,
                    help='The controller port (1-4) the opponent will play on',
                    default=2)
parser.add_argument('--debug', '-d', action='store_true',
                    help='Debug mode. Creates a CSV of all game states')
parser.add_argument('--address', '-a', default="127.0.0.1",
                    help='IP address of Slippi/Wii')
parser.add_argument('--dolphin_executable_path', '-e', default=None,
                    help='The directory where dolphin is')
parser.add_argument('--connect_code', '-t', default="",
                    help='Direct connect code to connect to in Slippi Online')
parser.add_argument('--iso_path', '-i', default="~/SSMB.iso",
                    help='Full path to Melee ISO file')
parser.add_argument('--cpu', '-c', action='store_true',
                    help='Whether to set oponent as CPU')
parser.add_argument('--cpu_level', '-l', type=int, default=3,
                    help='Level of CPU. Only valid if cpu is true')
parser.add_argument('--verbose', action='store_true',
                    help='Whether to print info to stdout')

args = parser.parse_args()

# This logger object is useful for retroactively debugging issues in your bot
#   You can write things to it each frame, and it will create a CSV file describing the match
log = None
if args.debug:
    log = melee.Logger()

# Create our Console object.
#   This will be one of the primary objects that we will interface with.
#   The Console represents the virtual or hardware system Melee is playing on.
#   Through this object, we can get "GameState" objects per-frame so that your
#       bot can actually "see" what's happening in the game
console = melee.Console(path=args.dolphin_executable_path,
                        slippi_address=args.address,
                        logger=log)

# Create our Controller object
#   The controller is the second primary object your bot will interact with
#   Your controller is your way of sending button presses to the game, whether
#   virtual or physical.
controller = melee.Controller(console=console,
                              port=args.port,
                              type=melee.ControllerType.STANDARD,
                              verbose=args.verbose)

controller_opponent = melee.Controller(console=console,
                                       port=args.opponent,
                                       type=melee.ControllerType.STANDARD,
                                       ai=True,
                                       verbose=args.verbose)

# This isn't necessary, but makes it so that Dolphin will get killed when you ^C
def signal_handler(sig, frame):
    console.stop()
    if args.debug:
        log.writelog()
        print("") #because the ^C will be on the terminal
        print("Log file created: " + log.filename)
    print("Shutting down cleanly...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Run the console
console.run(iso_path=args.iso_path)

# Connect to the console
print("Connecting to console...")
if not console.connect():
    print("ERROR: Failed to connect to the console.")
    sys.exit(-1)
print("Console connected")

# Plug our controller in
#   Due to how named pipes work, this has to come AFTER running dolphin
#   NOTE: If you're loading a movie file, don't connect the controller,
#   dolphin will hang waiting for input and never receive it
print("Connecting controller to console...")
if not controller.connect():
    print("ERROR: Failed to connect the controller.")
    sys.exit(-1)
if not controller_opponent.connect():
    print("ERROR: Failed to connect the controller.")
    sys.exit(-1)
print("Controllers connected")

menu_helper = melee.MenuHelper(controller_1=controller,
                                controller_2=controller_opponent,
                                character_1_selected=melee.Character.CPTFALCON,
                                character_2_selected=melee.Character.FOX,
                                stage_selected=melee.Stage.FINAL_DESTINATION,
                                connect_code=args.connect_code,
                                autostart=True,
                                swag=True,
                                make_cpu=args.cpu,
                                level=args.cpu_level,
                                verbose=args.verbose)

costume = 0

# Main loop
while True:
    # "step" to the next frame
    gamestate = console.step()
    if gamestate is None:
        continue

    # The console object keeps track of how long your bot is taking to process frames
    #   And can warn you if it's taking too long
    if console.processingtime * 1000 > 12:
        print("WARNING: Last frame took " + str(console.processingtime*1000) + "ms to process.")

    # If in game
    if gamestate.menu_state in [melee.Menu.IN_GAME, melee.Menu.SUDDEN_DEATH]:
        # Have both player spam upsmashes
        melee.techskill.upsmashes(gamestate=gamestate, controller=controller)

        if not args.cpu:
            melee.techskill.upsmashes(gamestate=gamestate, controller=controller_opponent)

    # If in menu
    else:
        menu_helper.step(gamestate)
                                            
    if log:
        log.logframe(gamestate)
        log.writeframe()
