# MyBrowser - Python Tkinter Browser

## Overview
A custom web browser built with Python and Tkinter. This is a desktop GUI application that renders HTML/CSS and supports basic browsing functionality.

## Project Structure
```
browser/
  __init__.py     - Package initialization
  app.py          - Main BrowserApp class with Tkinter UI
  tab.py          - Tab management and page rendering
  url.py          - URL parsing
  http.py         - HTTP fetching
  html.py         - HTML parser
  css.py          - CSS parser
  style.py        - Style engine
  layout.py       - Layout engine
  paint.py        - Painter/display list
  dom.py          - DOM nodes

run.py            - Entry point
```

## Running the Application
This is a VNC-based desktop application. It runs via the "Browser App" workflow which displays the Tkinter window in VNC output.

```bash
python run.py
```

## Features
- Tab management (Ctrl+T new, Ctrl+W close)
- Navigation (back, forward, reload, home)
- Address bar with URL entry
- HTML/CSS rendering
- Image support (PNG, GIF, JPG with Pillow)
- Scrolling

## Dependencies
- Python 3.11
- Tkinter (via system packages: tk, tcl, xorg.libX11, xorg.libXft)
- Optional: Pillow for JPG support
