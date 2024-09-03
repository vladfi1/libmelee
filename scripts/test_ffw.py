
import argparse
import logging
import multiprocessing as mp

import melee

if __name__ == '__main__':
  mp.freeze_support()

  parser = argparse.ArgumentParser()

  parser.add_argument('--dolphin', type=str, required=True)
  parser.add_argument('--iso', type=str, required=True)
  parser.add_argument('--slippi_port', default=51441)
  parser.add_argument('--enable_ffw', action='store_true')
  parser.add_argument('--use_exi_inputs', action='store_true')
  parser.add_argument('--user', type=str, default=None)

  args = parser.parse_args()

  console = melee.Console(
      path=args.dolphin,
      online_delay=0,
      slippi_port=args.slippi_port,
      use_exi_inputs=args.use_exi_inputs,
      enable_ffw=args.enable_ffw,
      disable_audio=True,
      save_replays=False,
      copy_home_directory=False,
      fullscreen=False,
      dolphin_home_path=args.user,
      tmp_home_directory=args.user is None,
  )

  controllers: dict[int, melee.Controller] = {}

  PORTS = (1, 2)

  for port in PORTS:
    controllers[port] = melee.Controller(
        console, port, melee.ControllerType.STANDARD)

  def is_menu_state(gamestate: melee.GameState) -> bool:
    return gamestate.menu_state not in [melee.Menu.IN_GAME, melee.Menu.SUDDEN_DEATH]

  def next_gamestate() -> melee.GameState:
    gamestate = console.step()
    if gamestate is None:
      raise TimeoutError('Console timed out.')
    return gamestate

  def step() -> melee.GameState:
    gamestate = next_gamestate()

    menu_frames = 0
    while is_menu_state(gamestate):
      for i, controller in enumerate(controllers.values()):

        melee.MenuHelper.menu_helper_simple(
            gamestate, controller,
            stage_selected=melee.Stage.YOSHIS_STORY,
            autostart=i == 0 and menu_frames > 180,
            swag=False,
            costume=i,
            character_selected=melee.Character.FOX,
            # cpu_level=9,
        )

      gamestate = next_gamestate()
      menu_frames += 1

    return gamestate


  try:
    console.run(
        iso_path=args.iso,
        # environment_vars=env_vars,
        # platform=platform,
    )

    logging.info('Connecting to console...')
    if not console.connect():
      raise RuntimeError(f"Failed to connect to the console on port {args.slippi_port}.")
    logging.info('Connected to console')

    for controller in controllers.values():
      if not controller.connect():
        raise RuntimeError("Failed to connect the controller.")

    for _ in range(300):
      step()

  except KeyboardInterrupt:
    logging.info('Shutting down.')
  finally:
    print('Stopping console')
    console.stop()
    print('Console stopped')
