messing around with man pages now that i've discovered them

## Plans:

Basically this should spawn a small window attached to a given process (based on cursor focus) that displays the relevant man pages for said application. I dunno why, seemed neat. It is currently partially working but the positioning is way off (auto position is supposed to attach to the window but usually goes to the top left of whatever monitor you're using at the time) and the man pages are horribly not focused. It also cannot be resized yet.

## Try it

- From source (dev):

  - zsh/bash: `PYTHONPATH=src:. python src/main.py`

- Install locally:
  - `pip install -e .` then run `wingman`

Notes: Linux/X11 only; needs Python 3.12+, PyQt6, python-xlib, requests.
