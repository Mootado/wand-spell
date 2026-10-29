# Wand Spell

A short adventure for the Raspberry Pi, the Camera Module 2 NoIR, an infrared lamp, and an official Universal interactive wand. The wand tip is retroreflective. The lamp sits against the camera, the tip blooms in the NoIR picture, and the shape of the stroke is the spell.

The story is practice, a burning gate, a frozen lock, a river, and a duel. Tide (a circle) puts fire out and counters a fire attack. Flame (a Z) melts ice and counters an ice attack. Frost (a flat line) freezes the river and counters a water attack. Strike (a diagonal slash) hits a dazed enemy.

## Set up the room

- Use the Pi 3 B+. It has a normal HDMI port, and it is fast enough for this game. Leave the OpenELEC Pi as the Kodi player. The Pi 4 also works, and is a bit smoother, but its video port is micro HDMI.
- The Camera Module 2 plugs into the camera socket beside the HDMI port. The metal contacts on the ribbon face the HDMI port. Power is the micro USB plug, 5V at 2.5A.
- Put the IR lamp tight against the camera lens. Aim both at the player, about 1.5–3 m away, not at the TV. The reflective tip only sends light back toward the lamp.
- Dim the room. The wand tip should be the brightest spot. If the stock tip is weak, add a tiny piece of retroreflective tape.
- The first screen is the camera check. Only the wand tip should be white. `[` and `]` change the threshold. Enter starts the story.

## The Pi 3 needs Raspberry Pi OS

The OpenELEC Pi only runs Kodi. Leave that board and its card alone.

The Pi 3 B+ keeps its OS on a microSD card, not on the board. A card that boots into RetroPie is fine for the hardware, and it should stay the ROM card. RetroPie is an older system image built for emulators. Installing this game on it can break the emulators, and its camera support usually does not match what the wand tracker needs.

A rainbow rectangle that stays on the TV means that card started to boot and then stopped. The system on it is too old for a Pi 3 B+. A flash of that rectangle for a second, followed by a desktop, is normal.

Write Raspberry Pi OS to a second, blank card and swap cards when you want to play the wand game:

1. On the Windows PC, install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Under Raspberry Pi OS (32-bit), choose Raspberry Pi OS. That is the desktop image. Skip Full, Lite, Legacy, and Raspberry Pi Desktop. The last one is for a PC, not a Pi.
3. Write it to that card and boot the Pi 3 from it.

## Run it on the Pi

Raspberry Pi OS already ships the camera stack. Use those system packages so `picamera2` can see NumPy:

```bash
sudo apt install python3-pygame python3-numpy python3-opencv python3-picamera2
cd "Wand Spell"
python3 main.py --fullscreen --debug
```

`--debug` keeps a small threshold view in the corner after the story starts. F11 toggles fullscreen. Escape quits. R starts the story over.

## Try the story on a PC

The camera path is for the Pi. On Windows the number keys cast the same spells:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --keyboard
```

`pygame-ce` supplies the `pygame` module, including on Python 3.14. The Pi keeps using the apt `python3-pygame` package above.

1 circle, 2 zigzag, 3 line, 4 slash.

## Sounds

The game plays short generated tones. Drop a `.ogg` in `assets/audio/` with one of these names and it is used instead: `tide`, `flame`, `frost`, `strike`, `fizzle`, `success`, `hurt`, `daze`, `hit`.
