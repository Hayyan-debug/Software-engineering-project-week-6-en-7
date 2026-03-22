"""
client.py - Gauntlet Galaxy
Gameplay entrypoint.
"""

import pygame

from src.audio import get_shared_audio_manager
from src.entities.hammer_fighter import HammerFighter
from src.entities.sword_fighter import SwordFighter
from src.game.game import Game
from src.network.network_client import NetworkClient


def main() -> None:
    pygame.init()
    audio_manager = get_shared_audio_manager()
    audio_manager.initialize()
    audio_manager.preload()

    # Attempt to connect to server (optional — game runs offline too)
    net = NetworkClient(host="localhost", port=5555)
    connected = net.connect()
    if not connected:
        print("[client] No server found — running in local/offline mode.")
        net = None

    # TODO: replace with actual character-select result from startmenu.py
    arena_id = 0
    fighter_cls_local = SwordFighter
    fighter_cls_remote = HammerFighter

    game = Game(
        arena_id=arena_id,
        fighter_cls_local=fighter_cls_local,
        fighter_cls_remote=fighter_cls_remote,
        net=net,
        audio_manager=audio_manager,
    )
    game.run()


if __name__ == "__main__":
    main()
