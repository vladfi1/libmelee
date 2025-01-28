""" Implementation of a SlippiComm client aka 'Slippstream'
                                                    (I'm calling it that)

This can be used to talk to some server implementing the Slippstream protocol
(i.e. the Project Slippi fork of Nintendont or Slippi Ishiiruka).
"""

from enum import Enum
import logging
import enet
import json
import multiprocessing as mp
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event

from melee.enums import Stage

# pylint: disable=too-few-public-methods
class EventType(Enum):
    """ Replay event types """
    GECKO_CODES = 0x10
    PAYLOADS = 0x35
    GAME_START = 0x36
    PRE_FRAME = 0x37
    POST_FRAME = 0x38
    GAME_END = 0x39
    FRAME_START = 0x3a
    ITEM_UPDATE = 0x3b
    FRAME_BOOKEND = 0x3c
    GECKO_LIST = 0x3d
    FOD_INFO = 0x3f
    DL_INFO = 0x40
    PS_INFO = 0x41

    BONES = 0x60

    # This is not used in-game. All menu events have this type.
    # Due to a bug, dolphin sometimes sends these before the game has ended.
    MENU_EVENT = 0x3e

EVENT_TO_STAGE = {
    EventType.FOD_INFO: Stage.FOUNTAIN_OF_DREAMS,
    EventType.DL_INFO: Stage.DREAMLAND,
    EventType.PS_INFO: Stage.POKEMON_STADIUM,
}

class CommType(Enum):
    """ Types of SlippiComm messages """
    HANDSHAKE = 0x01
    REPLAY = 0x02
    KEEPALIVE = 0x03
    MENU = 0x04


class SlippstreamWorker:
    def __init__(
        self,
        address: str,
        port: int,
        buffer: Connection,
        shutdown: Event,
    ):
        self.address = address
        self.port = port
        self._buffer = buffer
        self._shutdown = shutdown

        self._host = enet.Host(None, 1, 0, 0)
        self._peer = None

        self._handshake_data = json.dumps({
            "type" : "connect_request",
            "cursor" : 0,
        }).encode()

    def _send_handshake(self):
        self._peer.send(0, enet.Packet(self._handshake_data))

    def connect(self) -> bool:
        """Connect to the server

        Returns True on success, False on failure
        """
        # Try to connect to the server and send a handshake
        try:
            self._peer = self._host.connect(
                enet.Address(bytes(self.address, 'utf-8'), self.port), 1)
        except OSError as e:
            logging.error(e)
            return False
        try:
            for _ in range(10):
                event = self._host.service(1000)
                if event.type == enet.EVENT_TYPE_CONNECT:
                    self._send_handshake()
                    return True
            logging.error(
                'Could not receive CONNECT event at address '
                f'{self.address}:{self.port}.')
            return False
        except OSError:
            logging.error(e)
            return False

    def run(self):
        connected = self.connect()
        self._buffer.send(connected)
        if not connected:
            return

        while not self._shutdown.is_set():
            event = self._host.service(1000)

            if event.type == enet.EVENT_TYPE_NONE:
                continue  # timeout
            elif event.type == enet.EVENT_TYPE_RECEIVE:
                # This happens at the end of a game for some reason?
                if len(event.packet.data) == 0:
                    # TODO: figure out what to do in this case
                    continue
                self._buffer.send_bytes(event.packet.data)
            elif event.type == enet.EVENT_TYPE_CONNECT:
                # should this happen during the run loop?
                self._send_handshake()
            elif event.type == enet.EVENT_TYPE_DISCONNECT:
                self._buffer.close()
                return

def _run_worker(**kwargs):
    try:
        SlippstreamWorker(**kwargs).run()
    except KeyboardInterrupt:
        pass  # don't spam the console with stack traces

class EnetDisconnected(Exception):
    """Raised when we get an enet disconnection."""

class SlippstreamClient:
    """ Container representing a client to some SlippiComm server """

    def __init__(
        self,
        address="127.0.0.1",
        port=51441,
    ):
        self.address = address
        self.port = port
        self.running = False

        # set up worker process
        self._buffer, worker_buffer = mp.Pipe(False)
        self._shutdown = mp.Event()
        self._worker = mp.Process(
            target=_run_worker,
            kwargs=dict(
                address=address,
                port=port,
                buffer=worker_buffer,
                shutdown=self._shutdown,
            )
        )

        # Not yet supported
        self.playedOn = "dolphin"
        self.timestamp = ""
        self.consoleNick = ""
        self.players = {}

    def shutdown(self):
        """ Close down the socket and connection to the console """
        if self._worker:
            self._shutdown.set()
            self._worker.join()
            self._buffer.close()
            self._worker = None
        self.running = False

    def dispatch(self, polling_mode: bool, timeout: float = 0):
        """Dispatch messages with the peer (read and write packets)"""
        assert self.running, "Can only dispatch while running."

        try:
            if polling_mode and not self._buffer.poll(timeout=timeout):
                return None
            message_bytes = self._buffer.recv_bytes()
        except EOFError:
            raise EnetDisconnected()

        return json.loads(message_bytes)

    def connect(self) -> bool:
        self._worker.start()
        connected = self._buffer.recv()
        if not connected:
            self.shutdown()
        else:
            self.running = True
        return connected
