"""World-map summary of Thursday 19 November 2026 in one image.

Draws a 1024x1024 PNG with a pure-Python stdlib renderer: a stylised
world map with six numbered story markers, a bold date banner, and a
legend listing the six verified stories of the day. Deterministic:
no time, no randomness, no network, no external files.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font
# A 5x7 bitmap font. Each glyph is 7 rows of 5 characters; "#" is ink.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px per glyph)."""
    return len(text) * 6 * scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = color

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = color * (x1 - x0)

    def hline(self, x0, x1, y, color):
        self.rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, color)

    def vline(self, x, y0, y1, color):
        self.rect(x, min(y0, y1), 1, abs(y1 - y0) + 1, color)

    def line(self, x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.rect(cx - dx, yy, dx * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=2):
        for t in range(thick):
            rr = r - t
            for ang in range(360):
                import math
                x = cx + int(rr * math.cos(math.radians(ang)))
                y = cy + int(rr * math.sin(math.radians(ang)))
                self.set(x, y, color)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon given as [(x, y), ...]."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.rect(int(xs[j]), y, int(xs[j + 1]) - int(xs[j]) + 1, 1, color)

    def text(self, x, y, s, scale, color):
        for ci, ch in enumerate(s):
            glyph = FONT.get(ch, FONT[" "])
            gx = x + ci * 6 * scale
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(gx + col * scale, y + row * scale,
                                  scale, scale, color)

    def text_centred(self, cx, y, s, scale, color):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)


def write_png(canvas, path):
    """Encode the canvas as a deterministic RGB PNG (filter 0)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    chunks = b""
    for ctype, data in ((b"IHDR", ihdr),
                        (b"IDAT", zlib.compress(bytes(raw), 9)),
                        (b"IEND", b"")):
        chunks += struct.pack(">I", len(data)) + ctype + data
        chunks += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunks)

# ---------------------------------------------------------------- palette
NAVY = bytes((10, 30, 51))
OCEAN = bytes((15, 53, 87))
OCEAN_LINE = bytes((28, 74, 110))
LAND = bytes((232, 220, 195))
LAND_EDGE = bytes((201, 185, 143))
GOLD = bytes((242, 183, 5))
WHITE = bytes((255, 255, 255))
PAPER = bytes((247, 245, 239))
INK = bytes((10, 30, 51))
GREY = bytes((68, 84, 106))
FAINT = bytes((210, 208, 198))
RED = bytes((230, 57, 70))
RED_DARK = bytes((178, 34, 48))

BANNER_H = 118
MAP_TOP, MAP_BOT = BANNER_H, 640
LEGEND_TOP = 640

# Six verified stories of Thursday 19 November 2026.
# (number, headline, subline, lon, lat, map label, label dx, label dy)
STORIES = [
    (1, "GTA VI GOES ON SALE AROUND THE WORLD",
     "VICE CITY OPENS AT MIDNIGHT; CRITICS GIVE IT 99/100",
     174.0, -41.0, "NEW ZEALAND", -150, -34),
    (2, "TRUMP, XI AND PUTIN MEET IN SHENZHEN",
     "FIRST TRILATERAL SUMMIT; NUCLEAR ARMS ON THE TABLE",
     114.0, 22.5, "SHENZHEN", 16, -30),
    (3, "WORLD COURT RULES ON MYANMAR GENOCIDE",
     "ROHINGYA CASE DECIDED IN THE HAGUE AFTER 7 YEARS",
     4.4, 52.0, "THE HAGUE", -118, -32),
    (4, "NASA BRIEFS ON VOYAGER 1, A LIGHT-DAY AWAY",
     "FARTHEST HUMAN-MADE OBJECT, 16 BILLION MILES OUT",
     -77.0, 38.9, "WASHINGTON", -60, -32),
    (5, "CYCLONE AKVAN NEARS INDIA'S EAST COAST",
     "HEAVY RAIN LASHES ANDHRA COAST AS STORM CLOSES IN",
     85.0, 15.0, "BAY OF BENGAL", -20, 30),
    (6, "ATMOSPHERIC RIVER SOAKS CALIFORNIA",
     "HEAVIEST RAIN HITS LOS ANGELES; 30M UNDER FLOOD THREAT",
     -121.0, 37.0, "CALIFORNIA", -140, -30),
]

# Stylised continent outlines as (lon, lat) polygons.
CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-140, 70), (-128, 71), (-115, 73), (-100, 73),
     (-95, 80), (-85, 80), (-78, 73), (-70, 68), (-65, 60), (-56, 52),
     (-60, 46), (-70, 42), (-75, 35), (-80, 26), (-84, 21), (-90, 15),
     (-95, 18), (-105, 20), (-112, 25), (-120, 33), (-125, 42), (-125, 50),
     (-135, 58), (-150, 60), (-160, 58), (-168, 66)],
    # Greenland
    [(-58, 64), (-48, 60), (-35, 64), (-28, 68), (-22, 70), (-30, 76),
     (-50, 76), (-58, 70), (-58, 64)],
    # South America
    [(-80, 10), (-75, 5), (-68, 8), (-60, 5), (-50, 0), (-42, -3),
     (-35, -8), (-40, -20), (-48, -28), (-56, -35), (-62, -41), (-66, -47),
     (-70, -53), (-73, -44), (-73, -30), (-72, -18), (-78, -8), (-80, 2),
     (-80, 10)],
    # Africa
    [(-17, 15), (-12, 27), (-6, 33), (0, 36), (10, 37), (20, 32),
     (30, 31), (34, 28), (38, 20), (43, 12), (51, 11), (48, 2),
     (42, -4), (40, -12), (36, -20), (32, -28), (26, -34), (19, -35),
     (15, -30), (12, -18), (9, -4), (9, 4), (-2, 5), (-10, 6), (-17, 15)],
    # Eurasia
    [(-10, 36), (-9, 43), (-4, 48), (-1, 50), (3, 52), (8, 57),
     (10, 59), (16, 57), (21, 55), (24, 58), (27, 60), (30, 68),
     (38, 68), (50, 68), (62, 70), (75, 72), (90, 75), (105, 76),
     (120, 73), (135, 72), (150, 70), (162, 66), (170, 66), (178, 65),
     (170, 60), (162, 56), (158, 52), (150, 59), (142, 50), (140, 40),
     (132, 36), (127, 35), (122, 31), (116, 24), (110, 20), (106, 10),
     (100, 8), (98, 14), (94, 17), (91, 22), (88, 22), (82, 16),
     (78, 9), (75, 9), (73, 19), (70, 22), (66, 25), (61, 25),
     (57, 27), (53, 28), (49, 30), (44, 29), (40, 34), (36, 36),
     (32, 36), (27, 37), (23, 40), (19, 42), (14, 44), (10, 44),
     (6, 43), (2, 42), (-2, 37), (-9, 37), (-10, 36)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (122, -34), (129, -32), (136, -35),
     (140, -38), (146, -39), (150, -37), (153, -28), (150, -22), (146, -19),
     (142, -11), (137, -12), (132, -12), (127, -14), (122, -17), (117, -20),
     (113, -22)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 38), (141, 41), (143, 43),
     (145, 44), (142, 42), (140, 38), (136, 34), (132, 33), (130, 31)],
    # United Kingdom
    [(-5, 50), (-4, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53),
     (1, 51), (-2, 50), (-5, 50)],
    # Indonesia (Sumatra, Borneo, Java, New Guinea as one rough chain)
    [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8), (120, -9),
     (122, -10), (119, -8), (114, -7), (109, -6), (104, -3), (99, 1),
     (95, 5)],
    [(109, 1), (113, 4), (117, 2), (119, -1), (117, -3), (112, -3),
     (109, 0), (109, 1)],
    [(131, -1), (136, -2), (141, -3), (141, -8), (136, -8), (131, -4),
     (131, -1)],
    # New Zealand
    [(167, -45), (169, -42), (172, -40), (175, -38), (177, -38),
     (176, -40), (173, -42), (170, -44), (167, -46), (167, -45)],
]


def lonlat_to_xy(lon, lat):
    x = int((lon + 180.0) / 360.0 * W)
    y = int(MAP_TOP + (85.0 - lat) / 145.0 * (MAP_BOT - MAP_TOP))
    return x, y


def draw_banner(cv):
    cv.rect(0, 0, W, BANNER_H, NAVY)
    cv.text_centred(W // 2, 10, "THE WORLD IN ONE DAY", 2, GOLD)
    cv.text_centred(W // 2, 34, "THURSDAY 19 NOVEMBER 2026", 5, WHITE)
    cv.text_centred(W // 2, 88, "SIX STORIES FROM SIX CORNERS OF THE MAP", 2,
                    bytes((200, 214, 228)))
    cv.rect(0, BANNER_H - 4, W, 4, GOLD)


def draw_map(cv):
    cv.rect(0, MAP_TOP, W, MAP_BOT - MAP_TOP, OCEAN)
    # Graticule, faint.
    for lon in range(-150, 181, 30):
        x = int((lon + 180.0) / 360.0 * W)
        cv.vline(x, MAP_TOP, MAP_BOT - 1, OCEAN_LINE)
    for lat in range(-60, 86, 30):
        _, y = lonlat_to_xy(0, lat)
        cv.hline(0, W - 1, y, OCEAN_LINE)
    # Continents.
    for poly in CONTINENTS:
        pts = [lonlat_to_xy(lon, lat) for lon, lat in poly]
        cv.polygon(pts, LAND)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            cv.line(x0, y0, x1, y1, LAND_EDGE)
    # Compass note, top left of the ocean.
    cv.text(16, MAP_TOP + 14, "NORTH", 2, bytes((150, 180, 205)))
    cv.text(16, MAP_TOP + 32, "AMERICA", 2, bytes((150, 180, 205)))
    cv.text(880, MAP_TOP + 14, "PACIFIC", 2, bytes((150, 180, 205)))
    cv.text(880, MAP_TOP + 32, "OCEAN", 2, bytes((150, 180, 205)))


def draw_markers(cv):
    for num, _h, _s, lon, lat, label, dx, dy in STORIES:
        x, y = lonlat_to_xy(lon, lat)
        cv.circle(x, y, 19, RED)
        cv.ring(x, y, 19, RED_DARK, 2)
        cv.circle(x, y, 13, RED)
        cv.text_centred(x, y - 10, str(num), 3, WHITE)
        # Label with a small dark plate so it reads over land and sea.
        lw = text_width(label, 2)
        lx, ly = x + dx, y + dy
        cv.rect(lx - 5, ly - 4, lw + 10, 22, NAVY)
        cv.text(lx, ly, label, 2, WHITE)


def draw_legend(cv):
    cv.rect(0, LEGEND_TOP, W, H - LEGEND_TOP, PAPER)
    cv.rect(0, LEGEND_TOP, W, 3, GOLD)
    row_h = (H - LEGEND_TOP - 40) // 6
    for i, (num, head, sub, _lon, _lat, _lab, _dx, _dy) in enumerate(STORIES):
        y0 = LEGEND_TOP + 3 + i * row_h
        if i:
            cv.hline(24, W - 24, y0, FAINT)
        cy = y0 + row_h // 2
        cv.circle(52, cy, 20, RED)
        cv.text_centred(52, cy - 10, str(num), 3, WHITE)
        cv.text(90, y0 + 9, head, 3, INK)
        cv.text(90, y0 + 34, sub, 2, GREY)
    fy = LEGEND_TOP + 3 + 6 * row_h + 8
    cv.text_centred(W // 2, fy, "EVERY STORY HAPPENED OR WAS FIRST REPORTED ON 19 NOVEMBER 2026",
                    2, NAVY)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_banner(cv)
    draw_map(cv)
    draw_markers(cv)
    draw_legend(cv)
    write_png(cv, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
