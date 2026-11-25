# Texture Size Unlocker

### About

This tool check if your copy of the game allows textures files (.bmp images) with dimensions higher than 256x256 pixels and lets you toggle the ability to allow them. Nothing less. Nothing more.

### For the nerds

| Offset in toy2.exe   | Original hex value (restricted textures) | Modded hex value (unrestricted textures) |
| -------- | ------- | ------- |
| 000B071E  | 8B    | 90    |
| 000B071F | C1     | 90    |

### How to run

As this application requires CustomTkinter for the interface's style, make sure to install it with the command `pip install customtkinter` in your terminal. Once done, you can launch the app with the command `python main.py` in your terminal.

### How to build the executable

Run the command `pyinstaller --onefile --windowed --name "Toy Story 2 - Texture Size Unlocker" --icon "ts2.ico" --add-data "ts2.ico;." --collect-all customtkinter main.py` in your terminal.