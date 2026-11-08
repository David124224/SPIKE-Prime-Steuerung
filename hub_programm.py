# ============================================================
#  SPIKE Prime – Hub-Programm (Pybricks)
#
#  Dieses Programm läuft AUF DEM HUB. Einmal über
#  https://code.pybricks.com auf den Hub laden (siehe ANLEITUNG.md).
#  Danach startet das PC-Programm "spike_steuerung.py" es automatisch.
#
#  Der PC schickt Zeilen der Form  "<maske>,<tempo>,<grenze>\n"
#     maske : 0 = aus, 1 = linker Motor, 2 = rechter Motor, 3 = beide
#     tempo : 0..100 (%)
#     grenze: Abstand in mm, ab dem angehalten wird
#  Der Hub antwortet mit Statuszeilen  "S <abstand_mm> <blockiert> <maske>"
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, Light
try:
    from pybricks.pupdevices import ColorLightMatrix
except ImportError:
    ColorLightMatrix = None
from pybricks.parameters import Port, Direction, Color
from pybricks.tools import wait, StopWatch
from usys import stdin
from uselect import poll

# ---------- Einstellungen ----------
# None = automatisch erkennen. Sonst z. B. Port.A eintragen.
LINKS_PORT = None
RECHTS_PORT = None
SENSOR_PORT = None
LICHT_PORT = None

# Licht: dauerhaft an
LICHT_HELLIGKEIT = 100       # 0..100 %
LICHT_FARBE = Color.WHITE    # nur für die 3x3-Farblichtmatrix

# Drehrichtung beider Motoren: Direction.CLOCKWISE = rechts herum
RICHTUNG = Direction.CLOCKWISE

MAX_GESCHWINDIGKEIT = 1000  # Grad/Sekunde bei 100 % Tempo
TIMEOUT_MS = 500            # keine Nachricht vom PC -> Motoren aus
STATUS_INTERVALL_MS = 100   # wie oft der Abstand an den PC geht
# -----------------------------------

hub = PrimeHub()
hub.light.on(Color.ORANGE)

ALLE_PORTS = [
    ("A", Port.A), ("B", Port.B), ("C", Port.C),
    ("D", Port.D), ("E", Port.E), ("F", Port.F),
]


def port_name(port):
    for name, p in ALLE_PORTS:
        if p == port:
            return name
    return "?"


# ---------- Geräte suchen ----------
sensor = None
sensor_port = SENSOR_PORT
if sensor_port is None:
    for name, p in ALLE_PORTS:
        if p in (LINKS_PORT, RECHTS_PORT):
            continue
        try:
            sensor = UltrasonicSensor(p)
            sensor_port = p
            break
        except OSError:
            pass
else:
    sensor = UltrasonicSensor(sensor_port)

gefundene_motoren = []
for name, p in ALLE_PORTS:
    if p in (sensor_port, LINKS_PORT, RECHTS_PORT):
        continue
    try:
        gefundene_motoren.append((p, Motor(p, RICHTUNG)))
    except OSError:
        pass

links = Motor(LINKS_PORT, RICHTUNG) if LINKS_PORT is not None else None
rechts = Motor(RECHTS_PORT, RICHTUNG) if RECHTS_PORT is not None else None
links_port, rechts_port = LINKS_PORT, RECHTS_PORT

if links is None and gefundene_motoren:
    links_port, links = gefundene_motoren.pop(0)
if rechts is None and gefundene_motoren:
    rechts_port, rechts = gefundene_motoren.pop(0)

if links is None or rechts is None:
    print("ERR Es wurden nicht zwei Motoren gefunden.")
    hub.light.on(Color.RED)
    hub.display.char("X")
    raise SystemExit

# ---------- Licht suchen und dauerhaft einschalten ----------
belegt = [sensor_port, links_port, rechts_port] + [p for p, _m in gefundene_motoren]


def licht_an(port):
    """Versucht zuerst die 3x3-Farblichtmatrix, dann das einfache LEGO-Licht."""
    if ColorLightMatrix is not None:
        try:
            matrix = ColorLightMatrix(port)
            matrix.on(LICHT_FARBE * (LICHT_HELLIGKEIT / 100))
            return matrix
        except OSError:
            pass
    lampe = Light(port)
    lampe.on(LICHT_HELLIGKEIT)
    return lampe


licht = None
licht_port = LICHT_PORT
if licht_port is not None:
    licht = licht_an(licht_port)
else:
    for name, p in ALLE_PORTS:
        if p in belegt:
            continue
        try:
            licht = licht_an(p)
            licht_port = p
            break
        except OSError:
            pass

if licht is None:
    print("ERR Kein Licht gefunden.")

if sensor is None:
    print("ERR Kein Abstandssensor gefunden - fahre ohne Hindernis-Stopp.")
else:
    sensor.lights.on(30)

print("P", port_name(links_port), port_name(rechts_port),
      port_name(sensor_port) if sensor is not None else "-",
      port_name(licht_port) if licht is not None else "-")

# ---------- Hauptschleife ----------
eingang = poll()
eingang.register(stdin)

puffer = ""
maske = 0
tempo = 50
grenze = 100

uhr = StopWatch()
letzte_nachricht = uhr.time()
letzter_status = 0
war_blockiert = None

hub.light.on(Color.GREEN)
print("rdy")

while True:
    # Alle angekommenen Zeichen vom PC lesen
    while eingang.poll(0):
        zeichen = stdin.read(1)
        if zeichen == "\n":
            teile = puffer.split(",")
            puffer = ""
            if len(teile) == 3:
                try:
                    maske = int(teile[0]) & 3
                    tempo = max(0, min(100, int(teile[1])))
                    grenze = max(0, int(teile[2]))
                    letzte_nachricht = uhr.time()
                except ValueError:
                    pass
        elif len(puffer) < 32:
            puffer += zeichen
        else:
            puffer = ""

    # Sicherheit: Verbindung zum PC weg -> anhalten
    if uhr.time() - letzte_nachricht > TIMEOUT_MS:
        maske = 0

    abstand = sensor.distance() if sensor is not None else 2000
    blockiert = sensor is not None and abstand < grenze

    geschwindigkeit = tempo * MAX_GESCHWINDIGKEIT // 100

    if (maske & 1) and not blockiert:
        links.run(geschwindigkeit)
    else:
        links.brake()

    if (maske & 2) and not blockiert:
        rechts.run(geschwindigkeit)
    else:
        rechts.brake()

    if blockiert != war_blockiert:
        if blockiert:
            hub.light.on(Color.RED)
            hub.display.char("!")
        else:
            hub.light.on(Color.GREEN)
            hub.display.off()
        war_blockiert = blockiert

    if uhr.time() - letzter_status >= STATUS_INTERVALL_MS:
        print("S", abstand, 1 if blockiert else 0, maske)
        letzter_status = uhr.time()

    wait(20)
