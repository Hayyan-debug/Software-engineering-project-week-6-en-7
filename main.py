import asyncio
import pygame
import sys

# Import the main entry point from startmenu
import startmenu

async def main():
    # Initialize the menu state
    # We call the main_menu function from startmenu
    # Note: We need startmenu.main_menu() to be async or yield control
    await startmenu.main_menu_async()

if __name__ == "__main__":
    asyncio.run(main())
