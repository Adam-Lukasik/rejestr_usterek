# -*- coding: utf-8 -*-
"""Anonimizacja screenshotow na LinkedIn - zakrywa kod PS i dane klienta."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

SRC = {
    '1': r'C:\Users\adamj\AppData\Local\Temp\devin-pasted-images\1792428160679355700-27580-1-pasted.png',
    '2': r'C:\Users\adamj\AppData\Local\Temp\devin-pasted-images\1792428160680715800-27580-2-pasted.png',
    '3': r'C:\Users\adamj\AppData\Local\Temp\devin-pasted-images\1792428160681560500-27580-3-pasted.png',
    '4': r'C:\Users\adamj\AppData\Local\Temp\devin-pasted-images\1792428160682443500-27580-4-pasted.png',
}
OUT = os.path.join(os.path.dirname(__file__), 'out')
os.makedirs(OUT, exist_ok=True)

F_SEGOE = r'C:\Windows\Fonts\segoeui.ttf'

def save(im, name):
    """Zapisuje do OUT; jak plik jest zablokowany (otwarty podglad) - zapisuje z _v2."""
    path = os.path.join(OUT, name)
    try:
        im.save(path)
    except OSError:
        alt = path.replace('.png', '_v2.png')
        im.save(alt)
        print('locked:', name, '->', os.path.basename(alt))

def font(sz):
    return ImageFont.truetype(F_SEGOE, sz)

def cover_and_write(im, box, text, text_color, fnt, bg=None, pad_left=None):
    """Zamalowuje box i wypisuje text wyrownany pionowo."""
    dr = ImageDraw.Draw(im)
    if bg is None:
        bg = im.getpixel((box[0] - 4, (box[1] + box[3]) // 2))
    dr.rectangle(box, fill=bg)
    x0, y0, x1, y1 = box
    tw = dr.textlength(text, font=fnt)
    th = fnt.size
    tx = x0 + (pad_left if pad_left is not None else 0)
    ty = y0 + (y1 - y0 - th) / 2 - 1
    dr.text((tx, ty), text, font=fnt, fill=text_color)

# ---- img1 & img2: selektor projektu "PS012732" -> "PS0xxxxx" ----
for key, out_name in (('1', 'shot1_circuit.png'), ('2', 'shot2_connector.png')):
    im = Image.open(SRC[key]).convert('RGB')
    cover_and_write(im, (30, 141, 130, 159), 'PS0xxxxx', (55, 65, 81), font(13),
                    bg=(255, 255, 255))
    save(im, out_name)

# ---- img2: kolumna SIGNAL w tabeli pinoutu -> fikcyjne nazwy ----
im = Image.open(SRC['2']).convert('RGB')
dr = ImageDraw.Draw(im)
px = im.load()
# pasma tekstu w kolumnie SIGNAL (x~262..340, wiersze od y~510)
bands2 = []
in_band = False
for y in range(508, 730):
    has = any(min(px[x, y]) < 180 for x in range(262, 340, 2))
    if has and not in_band:
        start = y
        in_band = True
    elif not has and in_band:
        bands2.append((start, y))
        in_band = False
if in_band:
    bands2.append((start, 730))
bands2 = [(a, b) for a, b in bands2 if 5 <= b - a <= 13]
print('signal rows:', len(bands2), bands2)
FAKE_SIGNALS = [
    "Chassis Batt +", "Comms Power", "Siren 2", "Siren 1",
    "KL15 Power Radio", "Torch Light L", "Torch Light R", "Step Light",
    "USB Feed", "USB Feed 2", "Intercom 12V", "Intercom GND",
    "Beacon L", "Beacon R", "Dome Light", "Cargo Light",
]
f_sig = font(10)
for i, (a, b) in enumerate(bands2):
    mid = (a + b) // 2
    bg = px[243, mid]
    dr.rectangle((246, a - 1, 342, b + 1), fill=bg)
    dr.text((250, a - 1), FAKE_SIGNALS[i % len(FAKE_SIGNALS)],
            font=f_sig, fill=(30, 41, 59))
save(im, 'shot2_connector.png')

# ---- img3: pigulka projektu + kolumna pojazdow ----
im = Image.open(SRC['3']).convert('RGB')
dr = ImageDraw.Draw(im)

# pigulka "PS012732" w selektorze PROJEKT na ciemnym pasku bocznym (x~29..89, y~66..82)
navy = im.getpixel((50, 79))
cover_and_write(im, (34, 67, 82, 80), 'PS0xxxxx', (203, 213, 225), font(9),
                bg=navy)

# wiersze: cienkie linie separatorow w kolumnie pojazdu x=205..345
X0, X1 = 205, 348
px = im.load()
bands = []
in_band = False
for y in range(125, 556):
    has = any(px[x, y] != (255, 255, 255) for x in range(X0, X1, 2))
    if has and not in_band:
        start = y
        in_band = True
    elif not has and in_band:
        bands.append((start, y))
        in_band = False
if in_band:
    bands.append((start, 556))
# separatory wierszy = cienkie pasma (<=3px); wnetrza wierszy miedzy nimi
seps = [(a + b) / 2 for a, b in bands if b - a <= 3]
bounds = [125] + seps + [556]
rows = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
rows = [(a, b) for a, b in rows if b - a >= 12]
print('rows:', len(rows))

FAKE_DEFECTS = [
    ("Left beacon light does not turn on automatically", "Lighting - Exterior"),
    ("No power to the USB port in the patient compartment", "USB - Power supply"),
    ("Side door step light stays on after closing", "Lighting - Interior"),
    ("Display in the cab does not start after ignition", "Cab electronics - Display"),
    ("Rear work lights flicker intermittently", "Lighting - Work lights"),
    ("Siren tone changes unexpectedly while driving", "Siren - Control"),
    ("Panel shows battery voltage 0 V", "Monitoring - Voltage"),
    ("Heater blower does not respond to speed switch", "HVAC - Blower"),
    ("Parking sensor alarm triggers without obstacle", "Sensors - Parking"),
    ("Interior LED strip in the saloon does not dim", "Lighting - Interior"),
    ("Cabinet light flickers when doors open", "Lighting - Cabinet"),
    ("Oxygen outlet indicator is out", "Equipment - Indicator"),
    ("Blue light relay chatters at idle", "Lighting - Relay"),
    ("Intercom between cab and saloon has noise", "Comms - Intercom"),
    ("12V socket in the locker - no output voltage", "12V - Socket"),
    ("Radio resets when the engine starts", "Radio - Power"),
]

f_ps = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 9)
f_veh = font(9)
f_title = font(11)
f_cat = font(9)
for i, (a, b) in enumerate(rows):
    y0 = int(a) + 3
    dr.rectangle((203, a + 1, 815, b - 1), fill=(255, 255, 255))
    dr.text((208, y0), 'PS0xxxxx', font=f_ps, fill=(37, 99, 235))
    dr.text((208, y0 + 10), 'Ambulance - 2024', font=f_veh, fill=(107, 114, 128))
    # chip "EN" + tytul usterki + kategoria
    dr.rounded_rectangle((355, y0, 372, y0 + 10), radius=2,
                         fill=(219, 234, 254))
    dr.text((358, y0), 'EN', font=font(7), fill=(37, 99, 235))
    title, cat = FAKE_DEFECTS[i % len(FAKE_DEFECTS)]
    dr.text((378, y0 - 1), title, font=f_title, fill=(30, 41, 59))
    dr.text((378, y0 + 12), cat, font=f_cat, fill=(100, 116, 139))
# ostatni czesciowo widoczny wiersz na dole (ponizej ostatniego separatora)
dr.rectangle((203, rows[-1][1] + 1, 815, 556), fill=(255, 255, 255))
save(im, 'shot3_registry.png')

# ---- img4: schemat - mocny blur calego (struktura zostaje, tekst nieczytelny)
im = Image.open(SRC['4']).convert('RGB')
im = im.filter(ImageFilter.GaussianBlur(7))
save(im, 'shot4_schematic_blurred.png')
print('done ->', OUT)
