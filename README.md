# SPIKE Prime – Fernsteuerung vom PC über Bluetooth

Mit diesem Projekt steuert man einen **LEGO Education SPIKE Prime**-Roboter vom Windows-PC aus
über Bluetooth – mit den Pfeiltasten.

| Taste | Wirkung |
|---|---|
| ← gedrückt halten | linker Motor läuft |
| → gedrückt halten | rechter Motor läuft |
| ← und → zusammen | beide Motoren laufen |
| loslassen | Motor stoppt |

Zusätzlich:
- **Abstandssensor:** Ist etwas näher als der eingestellte Stopp-Abstand, hält der Roboter an,
  bis der Weg wieder frei ist.
- **Licht:** Ein angeschlossenes LEGO-Licht leuchtet durchgehend.
- **Sicherheit:** Reißt die Bluetooth-Verbindung ab, stoppen die Motoren nach 0,5 Sekunden.

## Hardware

- LEGO SPIKE Prime Hub
- 2 × SPIKE-Motor
- 1 × SPIKE-Abstandssensor (Ultraschall)
- 1 × LEGO-Licht (Powered-Up-Licht oder SPIKE 3×3-Farblichtmatrix)
- Windows-PC mit Bluetooth

Die Ports (A–F) sind egal, das Programm erkennt alle Geräte selbst.

## Schnellstart für die nächste Gruppe

1. **Pybricks-Firmware** auf den Hub spielen: <https://code.pybricks.com> in Chrome oder Edge öffnen →
   Zahnrad → *Install Pybricks Firmware*. (Zurück zur LEGO-Firmware geht jederzeit mit der SPIKE-App.)
2. **Hub-Programm hochladen:** Inhalt von [`hub_programm.py`](hub_programm.py) in code.pybricks.com
   einfügen, per Bluetooth verbinden, ▶ klicken. Danach die Verbindung in code.pybricks.com **trennen**.
3. **PC-Programm:** `SPIKE Steuerung.exe` unter
   [Releases](../../releases/latest) herunterladen und per Doppelklick starten.
   Windows-Warnung „Der Computer wurde geschützt“ → *Weitere Informationen* → *Trotzdem ausführen*.
4. Hub einschalten → **Verbinden** klicken → mit den Pfeiltasten fahren.

Ausführliche Bedienung und Fehlerhilfe: [`ANLEITUNG.md`](ANLEITUNG.md)

## Wie es programmiert wurde

Aufbau, Bluetooth-Protokoll, Erklärung des Codes und wie man die `.exe` selbst baut:
**[`docs/TECHNIK.md`](docs/TECHNIK.md)**

## Dateien

| Datei | Zweck |
|---|---|
| `hub_programm.py` | Läuft **auf dem Hub** (MicroPython mit Pybricks) |
| `spike_steuerung.py` | Läuft **auf dem PC** (Python, Fenster mit Steuerung) |
| `requirements.txt` | Python-Bibliotheken für das PC-Programm |
| `ANLEITUNG.md` | Bedienungsanleitung |
| `docs/TECHNIK.md` | Technische Dokumentation |
