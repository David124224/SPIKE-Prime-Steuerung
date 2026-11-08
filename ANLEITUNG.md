# SPIKE Prime – Steuerung vom PC über Bluetooth

## Dateien
- `hub_programm.py` – läuft **auf dem Hub** (Pybricks)
- `spike_steuerung.py` – läuft **auf dem PC** (Fenster mit Steuerung)

## 1. Pybricks auf den Hub spielen (einmalig)
1. In **Chrome oder Edge** https://code.pybricks.com öffnen.
2. Zahnrad (Einstellungen) → **„Install Pybricks Firmware"** und den Schritten folgen
   (Hub per USB anstecken, Bluetooth-Taste gedrückt halten usw.).
   *Zurück zur LEGO-Firmware geht jederzeit über die LEGO-SPIKE-App.*

## 2. Hub-Programm hochladen (einmalig)
1. Auf code.pybricks.com eine neue Datei anlegen und den Inhalt von `hub_programm.py` hineinkopieren.
2. Oben auf **Bluetooth** klicken, mit dem Hub verbinden, dann auf **▶ Ausführen** klicken.
   Damit ist das Programm auf dem Hub gespeichert.
3. Programm stoppen und **in code.pybricks.com die Verbindung trennen**
   (der Hub kann nur mit einem Gerät gleichzeitig verbunden sein).

## 3. PC-Programm starten
Doppelklick auf **`SPIKE.Steuerung.exe`** (Python wird dafür nicht gebraucht).
Die Datei gibt es auf GitHub unter **Releases** zum Herunterladen.
Tipp: Rechtsklick → „Weitere Optionen" → „Senden an" → „Desktop (Verknüpfung erstellen)".

Hub einschalten → im Fenster **Verbinden** klicken. Das Programm sucht den Hub,
startet das Hub-Programm und zeigt an, an welchen Ports die Motoren und der Sensor erkannt wurden.

## Bedienung
| Taste | Wirkung |
|---|---|
| ← gedrückt halten | linker Motor läuft |
| → gedrückt halten | rechter Motor läuft |
| ← und → zusammen | beide Motoren laufen |
| loslassen | Motor stoppt |

- Beide Motoren drehen **rechts herum** (im Uhrzeigersinn).
- **Hindernis:** Ist etwas näher als der „Stopp-Abstand" (Regler, Standard 100 mm),
  halten beide Motoren an. Hub-Licht rot, „!" auf dem Display. Ist der Weg wieder frei, geht es normal weiter.
- **Tempo:** Regler 10–100 %.
- **Links/Rechts tauschen:** falls die automatische Erkennung die Motoren vertauscht.
- **Sicherheit:** Bricht die Bluetooth-Verbindung ab, stoppen die Motoren nach 0,5 s von selbst.
- **Licht:** Das LEGO-Licht wird automatisch erkannt und leuchtet durchgehend, solange das Programm läuft.

## Anpassen (oben in `hub_programm.py`)
- `LINKS_PORT`, `RECHTS_PORT`, `SENSOR_PORT` – feste Ports eintragen, z. B. `Port.A` (Standard: automatisch;
  der Motor am alphabetisch ersten Port gilt als „links").
- `RICHTUNG` – `Direction.COUNTERCLOCKWISE`, falls die Motoren links herum laufen sollen.
- `MAX_GESCHWINDIGKEIT` – Grad/Sekunde bei 100 % Tempo.
- `LICHT_PORT` – fester Port für das Licht; `LICHT_HELLIGKEIT` (0–100), `LICHT_FARBE` (nur 3x3-Farblichtmatrix).

Nach einer Änderung das Programm erneut über code.pybricks.com hochladen.

## Probleme
- **„Kein Hub gefunden"**: Hub an? Bluetooth am PC an? code.pybricks.com getrennt?
  Oder im Feld „Hub-Name" den Namen des Hubs eintragen (Standard: „Pybricks Hub").
- **„Hub-Programm meldet sich nicht"**: Schritt 2 wiederholen.
- **„Nicht zwei Motoren gefunden"** (rotes X auf dem Hub): Kabel prüfen.
