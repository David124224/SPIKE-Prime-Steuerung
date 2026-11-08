# Technische Dokumentation

Diese Seite erklärt, wie die SPIKE-Prime-Steuerung aufgebaut ist und wie die Teile zusammenarbeiten.
Die Bedienung steht in der [`ANLEITUNG.md`](../ANLEITUNG.md).

## Überblick

```
┌──────────────────────────┐     Bluetooth Low Energy     ┌──────────────────────────┐
│  PC (Windows)            │  ─────────────────────────▶  │  SPIKE Prime Hub         │
│  spike_steuerung.py      │   "<maske>,<tempo>,<grenze>" │  hub_programm.py         │
│  - Fenster (tkinter)     │                              │  (Pybricks-Firmware)     │
│  - Pfeiltasten           │  ◀─────────────────────────  │  - 2 Motoren             │
│  - Bluetooth (bleak)     │   "S <abstand> <blockiert>…" │  - Abstandssensor, Licht │
└──────────────────────────┘                              └──────────────────────────┘
```

- **Auf dem Hub** läuft statt der LEGO-Firmware die freie Firmware **[Pybricks](https://pybricks.com)**.
  Sie führt MicroPython-Programme aus und bietet eine offene Bluetooth-Schnittstelle.
- **Auf dem PC** läuft ein Python-Programm mit Fenster. Es liest die Pfeiltasten und schickt
  den Tastenzustand per Bluetooth an den Hub.
- Die eigentliche Logik (Motoren, Hindernis-Stopp, Sicherheitsabschaltung) passiert **auf dem Hub**.
  Der PC sagt nur, *was* gewünscht ist.

## Das Bluetooth-Protokoll

### Ebene 1: Pybricks-Schnittstelle

Pybricks stellt einen Bluetooth-Dienst bereit, über den man Programme starten/stoppen und
Text mit dem laufenden Programm austauschen kann (wie eine serielle Konsole).

| Name | UUID / Wert | Bedeutung |
|---|---|---|
| Pybricks-Dienst | `c5f50001-8280-46da-89f4-6d8051e4aeef` | Daran erkennt der PC einen Pybricks-Hub |
| Befehle/Ereignisse | `c5f50002-8280-46da-89f4-6d8051e4aeef` | Eine Eigenschaft für beide Richtungen |
| Befehl `0x00` | Programm stoppen | PC → Hub |
| Befehl `0x01` | gespeichertes Programm starten | PC → Hub |
| Befehl `0x06` + Text | Text an `stdin` des Programms | PC → Hub |
| Ereignis `0x01` + Text | Ausgabe (`print`) des Programms | Hub → PC |

Was das Hub-Programm mit `print()` ausgibt, kommt also am PC als Ereignis `0x01` an.
Was der PC mit Befehl `0x06` schickt, kann das Hub-Programm von `stdin` lesen.

### Ebene 2: Unsere eigenen Nachrichten

Darauf aufbauend schicken sich PC und Hub einfache Textzeilen (jeweils mit `\n` am Ende).

**PC → Hub** (alle 50 ms und sofort bei jeder Änderung):

```
<maske>,<tempo>,<grenze>
```

| Feld | Werte | Bedeutung |
|---|---|---|
| `maske` | 0–3 | Bit 1 = linker Motor, Bit 2 = rechter Motor (0 aus, 1 links, 2 rechts, 3 beide) |
| `tempo` | 0–100 | Geschwindigkeit in Prozent |
| `grenze` | mm | Ab diesem Abstand wird angehalten |

**Hub → PC:**

| Zeile | Bedeutung |
|---|---|
| `P <links> <rechts> <sensor> <licht>` | Erkannte Ports, z. B. `P A B C D` (`-` = nicht gefunden) |
| `rdy` | Hub-Programm ist bereit |
| `S <abstand_mm> <blockiert> <maske>` | Status, alle 100 ms (`blockiert` = 1 bei Hindernis) |
| `ERR <text>` | Fehlermeldung, wird im Fenster angezeigt |

Die Bitmaske hat den Vorteil, dass „beide Tasten gleichzeitig“ ganz natürlich `1 | 2 = 3` ergibt.

## Ablauf einer Verbindung

1. Der PC sucht 15 Sekunden lang nach einem Gerät, das den Pybricks-Dienst anbietet
   (oder, falls ein Hub-Name eingetragen ist, nach diesem Namen).
2. Verbinden und Benachrichtigungen für die Ausgabe des Hubs einschalten.
3. Befehl `0x00` (ein evtl. noch laufendes Programm stoppen), kurz warten, dann `0x01` (starten).
4. Das Hub-Programm sucht seine Geräte, meldet `P …` und dann `rdy`.
   Kommt `rdy` nicht innerhalb von 8 Sekunden, meldet der PC
   „Hub-Programm meldet sich nicht“.
5. Ab jetzt schickt der PC laufend den Tastenzustand.
6. Beim Trennen oder Schließen des Fensters schickt der PC `0,0,0` (alles aus) und stoppt das Programm.

## Das Hub-Programm (`hub_programm.py`)

### Geräte automatisch erkennen

Pybricks wirft einen `OSError`, wenn an einem Port nicht das erwartete Gerät hängt.
Das Programm probiert deshalb einfach der Reihe nach alle Ports A–F durch:

1. **Abstandssensor:** erster Port, an dem `UltrasonicSensor(port)` klappt.
2. **Motoren:** alle übrigen Ports, an denen `Motor(port)` klappt. Der Motor am
   alphabetisch ersten Port wird „links“, der nächste „rechts“.
3. **Licht:** erster freier Port, an dem zuerst die 3×3-Farblichtmatrix, dann das einfache
   Powered-Up-Licht versucht wird.

Feste Ports kann man oben im Programm eintragen (`LINKS_PORT = Port.A` usw.).
Werden keine zwei Motoren gefunden, zeigt der Hub ein rotes **X** und beendet sich.

### Hauptschleife (alle 20 ms)

1. Alle angekommenen Zeichen von `stdin` lesen, ohne zu blockieren (`uselect.poll`).
   Bei `\n` wird die Zeile in `maske`, `tempo`, `grenze` zerlegt.
   Kaputte Zeilen werden ignoriert, der Puffer ist auf 32 Zeichen begrenzt.
2. **Sicherheit:** Kam seit 500 ms keine gültige Zeile mehr, wird `maske = 0` gesetzt.
   Bricht die Bluetooth-Verbindung ab, bleibt der Roboter also nach spätestens einer halben Sekunde stehen.
3. Abstand messen. Ist er kleiner als `grenze`, gilt der Weg als **blockiert**.
4. Jeder Motor läuft nur, wenn sein Bit in der Maske gesetzt ist **und** nichts blockiert.
   Sonst wird er gebremst (`brake()`).
   Geschwindigkeit = `tempo` % von `MAX_GESCHWINDIGKEIT` (1000 °/s).
5. Wenn sich „blockiert“ ändert: Hub-Licht rot + „!“ bzw. wieder grün.
6. Alle 100 ms eine Statuszeile `S …` an den PC.

Hub-Licht: **orange** = startet, **grün** = bereit, **rot** = Hindernis bzw. Fehler.

## Das PC-Programm (`spike_steuerung.py`)

Das Programm hat zwei Teile, die in verschiedenen Threads laufen:

- **`App`** – das Fenster mit **tkinter**. tkinter muss im Haupt-Thread laufen.
- **`HubVerbindung`** – die Bluetooth-Kommunikation mit **[bleak](https://github.com/hbldh/bleak)**.
  bleak arbeitet mit `asyncio`, deshalb läuft dafür eine eigene Event-Schleife in einem Hintergrund-Thread.

Die beiden reden so miteinander:

- **Fenster → Bluetooth:** über `run_coroutine_threadsafe` / `call_soon_threadsafe`
  (z. B. `aktualisieren(maske, tempo, grenze)`).
- **Bluetooth → Fenster:** über eine `queue.Queue`. Das Fenster schaut alle 30 ms nach
  (`nachrichten_pruefen`) und aktualisiert die Anzeige.
  So fasst der Bluetooth-Thread das Fenster nie direkt an.

### Tastatur

- `KeyPress`/`KeyRelease` für ← und → merken sich die gedrückten Tasten in einer Menge.
- Windows schickt beim Gedrückthalten ständig „losgelassen/gedrückt“ (Tastenwiederholung).
  Deshalb wird das Loslassen um 40 ms verzögert. Kommt in der Zeit wieder ein „gedrückt“,
  wird es verworfen. So stottern die Motoren nicht.
- Verliert das Fenster den Fokus, gelten alle Tasten als losgelassen.
- „Links/Rechts tauschen“ vertauscht nur die beiden Bits in der Maske.

### Anzeige

Ein `Canvas` zeigt die beiden Motoren (grau = aus, grün = läuft, rot = blockiert),
den gemessenen Abstand als Zahl und Balken (voller Balken = 1000 mm) und den
eingestellten Stopp-Abstand als orangen Strich. Pybricks meldet 2000 mm, wenn nichts
erkannt wird. Das wird als „frei“ angezeigt.

## Die `.exe` selbst bauen

Die `SPIKE.Steuerung.exe` im Release wurde mit **PyInstaller** aus `spike_steuerung.py`
gebaut (Python 3.14). So geht es auf einem Windows-PC:

```bat
:: einmalig
py -m pip install -r requirements.txt pyinstaller

:: bauen
py -m PyInstaller --onefile --windowed --name "SPIKE Steuerung" spike_steuerung.py
```

- `--onefile` packt alles (Python, bleak, tkinter) in eine einzige Datei.
- `--windowed` verhindert, dass zusätzlich ein schwarzes Konsolenfenster aufgeht.
- Das Ergebnis liegt in `dist\SPIKE Steuerung.exe`.
  `build/`, `dist/` und `*.spec` sind in der `.gitignore` und kommen nicht ins Repository.

Ohne `.exe` kann man das Programm auch direkt starten:

```bat
py -m pip install -r requirements.txt
py spike_steuerung.py
```

### Neue Version veröffentlichen

1. Änderungen committen.
2. Auf GitHub **Releases → Draft a new release**, neuen Tag anlegen (z. B. `v1.1`).
3. Die neue `.exe` anhängen und **Publish release** klicken.

Hinweis: GitHub ersetzt Leerzeichen in Dateinamen von Release-Anhängen durch Punkte.
Aus `SPIKE Steuerung.exe` wird deshalb `SPIKE.Steuerung.exe`.
Der Link „direkter Download“ im README zeigt immer auf diesen Namen im neuesten Release.

## Ideen zum Weiterbauen

- Rückwärtsfahren mit ↓ (dafür ein weiteres Bit in der Maske und `run(-geschwindigkeit)`).
- Lenken durch unterschiedliche Geschwindigkeiten links/rechts statt nur an/aus.
- Den Hindernis-Stopp nur beim Vorwärtsfahren wirken lassen.
