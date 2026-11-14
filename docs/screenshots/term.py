"""A pseudo-terminal running a command, emulated with pyte, saved as PNG frames (macOS: Menlo)."""

import os
import pty
import select
import struct
import fcntl
import termios
import threading
import time

import pyte
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Menlo.ttc"
SIZE = 15
BG, FG = (30, 30, 30), (212, 212, 212)
NAMED = {
    "black": (0, 0, 0), "red": (205, 49, 49), "green": (13, 188, 121), "brown": (229, 229, 16),
    "yellow": (229, 229, 16), "blue": (36, 114, 200), "magenta": (188, 63, 188), "cyan": (17, 168, 205),
    "white": (229, 229, 229), "brightblack": (102, 102, 102), "brightred": (241, 76, 76),
    "brightgreen": (35, 209, 139), "brightyellow": (245, 245, 67), "brightblue": (59, 142, 234),
    "brightmagenta": (214, 112, 214), "brightcyan": (41, 184, 219), "brightwhite": (255, 255, 255),
}


# Block elements as quadrant masks (TL=1 TR=2 BL=4 BR=8): painted as rectangles that fill the cell exactly, as a
# terminal does. Drawn as font glyphs they leave gaps between rows (the logo and the pane's icon fall apart).
BLOCKS = {"▘": 1, "▝": 2, "▀": 3, "▖": 4, "▌": 5, "▞": 6, "▛": 7, "▗": 8, "▚": 9, "▐": 10, "▜": 11,
          "▄": 12, "▙": 13, "▟": 14, "█": 15}

# Glyphs Claude Code draws that Menlo lacks, drawn as the nearest ones it has.
MISSING = {"⏺": "●", "⏵": "▸", "✻": "✳", "⎿": "└"}


def color(c, default):
    if c == "default":
        return default
    if c in NAMED:
        return NAMED[c]
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


class Term:
    def __init__(self, argv, env, cwd, cols=160, rows=48):
        self.cols, self.rows = cols, rows
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.lock = threading.Lock()
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(cwd)
            os.execvpe(argv[0], argv, env)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while True:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.2)
                if r:
                    data = os.read(self.fd, 65536)
                    if not data:
                        return
                    with self.lock:
                        self.stream.feed(data)
            except OSError:
                return

    def text(self):
        with self.lock:
            return "\n".join(self.screen.display)

    def wait_for(self, needle, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if needle in self.text():
                return True
            time.sleep(0.3)
        raise TimeoutError(f"not on screen after {timeout}s: {needle!r}\n{self.text()}")

    def send(self, s, delay=0.05):
        """Types `s`; an escape sequence (arrow keys) goes in one write, or ESC alone reads as Escape."""
        if s.startswith("\x1b"):
            os.write(self.fd, s.encode())
            return
        for ch in s:
            os.write(self.fd, ch.encode())
            time.sleep(delay)

    def png(self, path, top=0, bottom=None):
        bottom = self.rows if bottom is None else bottom
        reg = ImageFont.truetype(FONT, SIZE, index=0)
        bold = ImageFont.truetype(FONT, SIZE, index=1)
        cw = round(reg.getlength("M"))
        ch = SIZE + 5
        img = Image.new("RGB", (cw * self.cols + 24, ch * (bottom - top) + 24), BG)
        d = ImageDraw.Draw(img)
        with self.lock:
            for y in range(top, bottom):
                line = self.screen.buffer[y]
                for x in range(self.cols):
                    c = line[x]
                    fg, bg = color(c.fg, FG), color(c.bg, BG)
                    if c.reverse:
                        fg, bg = bg, fg
                    px, py = 12 + x * cw, 12 + (y - top) * ch
                    if bg != BG:
                        d.rectangle([px, py, px + cw - 1, py + ch - 1], fill=bg)
                    hw, hh = cw // 2, ch // 2
                    if c.data in BLOCKS:
                        m = BLOCKS[c.data]
                        for bit, (x0, y0, x1, y1) in {
                            1: (0, 0, hw, hh), 2: (hw, 0, cw, hh), 4: (0, hh, hw, ch), 8: (hw, hh, cw, ch),
                        }.items():
                            if m & bit:
                                d.rectangle([px + x0, py + y0, px + x1 - 1, py + y1 - 1], fill=fg)
                    elif 0x1FB00 <= ord(c.data[0]) <= 0x1FB3B:  # sextants: 2x3 cells, as a terminal draws them
                        n = ord(c.data[0]) - 0x1FB00 + 1
                        n += (n >= 21) + (n >= 41)  # the codepoints skip 21 (left half) and 42 (right half)
                        for i in range(6):
                            if n & (1 << i):
                                x0, y0 = (i % 2) * hw, (i // 2) * ch // 3
                                d.rectangle([px + x0, py + y0, px + x0 + hw - 1, py + y0 + ch // 3 - 1], fill=fg)
                    elif c.data == "│":  # unbroken from row to row
                        d.line([px + hw, py, px + hw, py + ch - 1], fill=fg)
                    elif c.data == "─":
                        d.line([px, py + hh, px + cw - 1, py + hh], fill=fg)
                    elif c.data.strip():
                        glyph = MISSING.get(c.data, c.data)
                        d.text((px, py + 2), glyph, font=bold if c.bold else reg, fill=fg)
        img.save(path, optimize=True)
