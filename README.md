messing around with man pages now that i've discovered them

## Plans: 

Basically this should spawn a small window attached to a given process (based on cursor focus) that displays the relevant man pages for said application. I dunno why, seemed neat. It is currently partially working but the positioning is way off (auto position is supposed to attach to the window but usually goes to the top left of whatever monitor you're using at the time) and the man pages are horribly not focused. It also cannot be resized yet.

## Requirements

* Python 3
* PyQt6
* ``python-xlib`` (for X11 environments)
* Optional tools for Wayland support:
  * ``swaymsg`` for Sway/other wlroots compositors
  * ``hyprctl`` for Hyprland

The application now attempts to query these tools when ``WAYLAND_DISPLAY`` is
present to correctly attach the panel to the focused window.  If neither tool is
available it falls back to the X11 backend, which should still work under
XWayland.
