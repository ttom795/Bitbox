# Bitbox

Bitbox is a procedural music generation tool, inspired by BFXR but entirely original. It uses mathematical operations to create waveforms with 6 channels, with SNES, NES and GameBoy presets. No Ai models are used to generate the music - it's just plug and play.

![Screenshot](Screenshots/bitbox.png?raw=true "MainScreen")

## Requirements

Currently the only external module required is NumPy, which is only needed to be downloaded if you're running the raw .py files (e.g. bitbox_app.py). Otherwise, the standalone .exe from Releases should work fine.

## Tabs

### Controls

![Screenshot](Screenshots/controls.png?raw=true "ControlsTab")

This tab controls most of the program. You can adjust the sound generation for each channel as well as adjust the time, scale and key. There's a handful of semi-random "presets" that adjust BPM and key based on moods or scenarios, e.g. dungeons, overworld, that kind of thing.

### Structure

![Screenshot](Screenshots/structure.png?raw=true "StructureTab")

The structure tab allows you to adjust the structure of the music (somewhat self-explanatory). A, B and C are the main sections, all slightly different, while intro and outro ramp-up and dial-down the music, respectively. All are derivative of the base tune and should loop perfectly.

### Motif

![Screenshot](Screenshots/motif.png?raw=true "MotifTab")

The motif tab allows you to create a custom motif that is repeated throughout the generated music.

### Display

![Screenshot](Screenshots/display.png?raw=true "Display")

Here, you get a visual representation of the entire track, with toggles per channel for visibility and the ability to manually adjust notes by dragging them. You can also export the music (this'd be a useless tool otherwise) as a WAV file.
