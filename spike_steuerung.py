"""
SPIKE Prime – PC-Steuerung über Bluetooth (Pybricks)

    Pfeil links   -> linker Motor
    Pfeil rechts  -> rechter Motor
    beide         -> beide Motoren
Der Abstandssensor hält den Roboter an, solange etwas davor ist.

Start:  python spike_steuerung.py
Benötigt:  pip install bleak
"""

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import ttk

from bleak import BleakClient, BleakScanner

# Pybricks-Bluetooth-Protokoll
PYBRICKS_SERVICE = "c5f50001-8280-46da-89f4-6d8051e4aeef"
PYBRICKS_CMD_EVENT = "c5f50002-8280-46da-89f4-6d8051e4aeef"
CMD_STOP_PROGRAM = b"\x00"
CMD_START_PROGRAM = b"\x01"
CMD_WRITE_STDIN = 0x06
EVENT_STDOUT = 0x01

SENDE_INTERVALL = 0.05  # Sekunden


class HubVerbindung:
    """Läuft in einem eigenen Thread mit asyncio und spricht mit dem Hub."""

    def __init__(self, nachrichten: queue.Queue):
        self.nachrichten = nachrichten  # Richtung GUI
        self.maske = 0
        self.tempo = 50
        self.grenze = 100
        self._loop = asyncio.new_event_loop()
        self._client = None
        self._bereit = None
        self._aenderung = None
        self._beenden = None
        self._puffer = ""
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    # ---- von der GUI aufgerufen ----
    def verbinden(self, name_filter: str):
        asyncio.run_coroutine_threadsafe(self._sitzung(name_filter), self._loop)

    def trennen(self):
        if self._beenden is not None:
            self._loop.call_soon_threadsafe(self._beenden.set)

    def aktualisieren(self, maske, tempo, grenze):
        self.maske, self.tempo, self.grenze = maske, tempo, grenze
        if self._aenderung is not None:
            self._loop.call_soon_threadsafe(self._aenderung.set)

    def schliessen(self, timeout=3.0):
        """Beim Programmende: sauber trennen und warten."""
        if self._client is None:
            return
        fertig = threading.Event()
        self._fertig_signal = fertig
        self.trennen()
        fertig.wait(timeout)

    # ---- intern ----
    def _melde(self, art, *daten):
        self.nachrichten.put((art, *daten))

    def _bei_daten(self, _sender, daten: bytearray):
        if not daten or daten[0] != EVENT_STDOUT:
            return
        self._puffer += daten[1:].decode("utf-8", errors="replace")
        while "\n" in self._puffer:
            zeile, self._puffer = self._puffer.split("\n", 1)
            zeile = zeile.strip()
            if not zeile:
                continue
            if zeile == "rdy":
                self._bereit.set()
            elif zeile.startswith("S "):
                teile = zeile.split()
                if len(teile) == 4:
                    self._melde("status", int(teile[1]), teile[2] == "1", int(teile[3]))
            elif zeile.startswith("P "):
                self._melde("ports", zeile[2:].split())
            elif zeile.startswith("ERR"):
                self._melde("fehler", zeile[4:])
            else:
                self._melde("log", zeile)

    async def _schreibe(self, daten: bytes):
        await self._client.write_gatt_char(PYBRICKS_CMD_EVENT, daten, response=True)

    async def _sitzung(self, name_filter: str):
        self._bereit = asyncio.Event()
        self._aenderung = asyncio.Event()
        self._beenden = asyncio.Event()
        self._puffer = ""
        name_filter = name_filter.strip().lower()

        def passt(geraet, werbung):
            if name_filter:
                return bool(geraet.name) and name_filter in geraet.name.lower()
            return PYBRICKS_SERVICE in [u.lower() for u in werbung.service_uuids]

        try:
            self._melde("zustand", "suche", "Suche Hub … (Hub einschalten)")
            geraet = await BleakScanner.find_device_by_filter(passt, timeout=15)
            if self._beenden.is_set():
                return
            if geraet is None:
                self._melde("fehler", "Kein Hub gefunden. Ist Pybricks drauf und der Hub an?")
                return

            self._melde("zustand", "suche", f"Verbinde mit {geraet.name} …")
            self._client = BleakClient(
                geraet, disconnected_callback=lambda _c: self._loop.call_soon_threadsafe(self._beenden.set)
            )
            await self._client.connect()
            await self._client.start_notify(PYBRICKS_CMD_EVENT, self._bei_daten)

            # Falls noch ein altes Programm läuft: stoppen, dann neu starten
            try:
                await self._schreibe(CMD_STOP_PROGRAM)
            except Exception:
                pass
            await asyncio.sleep(0.5)
            await self._schreibe(CMD_START_PROGRAM)

            try:
                await asyncio.wait_for(self._bereit.wait(), timeout=8)
            except asyncio.TimeoutError:
                self._melde("fehler", "Hub-Programm meldet sich nicht. "
                                      "Wurde hub_programm.py mit code.pybricks.com hochgeladen?")
                return

            self._melde("zustand", "verbunden", f"Verbunden mit {geraet.name}")

            # Sende-Schleife: regelmäßig den Tastenzustand schicken (dient auch als Lebenszeichen)
            while not self._beenden.is_set() and self._client.is_connected:
                text = f"{self.maske},{self.tempo},{self.grenze}\n".encode()
                await self._schreibe(bytes([CMD_WRITE_STDIN]) + text)
                self._aenderung.clear()
                try:
                    await asyncio.wait_for(self._aenderung.wait(), timeout=SENDE_INTERVALL)
                except asyncio.TimeoutError:
                    pass
                if self._beenden.is_set():
                    break

        except Exception as fehler:  # noqa: BLE001
            self._melde("fehler", f"Bluetooth-Fehler: {fehler}")
        finally:
            await self._aufraeumen()

    async def _aufraeumen(self):
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                await client.write_gatt_char(
                    PYBRICKS_CMD_EVENT, bytes([CMD_WRITE_STDIN]) + b"0,0,0\n", response=True)
                await client.write_gatt_char(PYBRICKS_CMD_EVENT, CMD_STOP_PROGRAM, response=True)
            except Exception:
                pass
            try:
                await client.disconnect()
            except Exception:
                pass
        self._melde("zustand", "getrennt", "Getrennt")
        signal = getattr(self, "_fertig_signal", None)
        if signal is not None:
            signal.set()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("SPIKE Prime Steuerung")
        root.geometry("520x470")
        root.minsize(480, 440)

        self.nachrichten = queue.Queue()
        self.hub = HubVerbindung(self.nachrichten)
        self.verbunden = False
        self.letzter_fehler = ""
        self.gedrueckt = set()
        self._loslassen_timer = {}

        # --- Verbindung ---
        oben = ttk.Frame(root, padding=10)
        oben.pack(fill="x")
        ttk.Label(oben, text="Hub-Name (leer = automatisch):").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(oben, textvariable=self.name_var, width=14).pack(side="left", padx=5)
        self.knopf = ttk.Button(oben, text="Verbinden", command=self.verbinden_klick)
        self.knopf.pack(side="left")

        self.status_var = tk.StringVar(value="Nicht verbunden")
        ttk.Label(root, textvariable=self.status_var, padding=(10, 0), foreground="#555").pack(anchor="w")
        self.ports_var = tk.StringVar(value="Ports: –")
        ttk.Label(root, textvariable=self.ports_var, padding=(10, 0)).pack(anchor="w")

        # --- Anzeige ---
        self.canvas = tk.Canvas(root, width=480, height=200, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self._baue_anzeige()

        # --- Einstellungen ---
        einst = ttk.Frame(root, padding=(10, 0))
        einst.pack(fill="x")
        ttk.Label(einst, text="Tempo (%)").grid(row=0, column=0, sticky="w")
        self.tempo_var = tk.IntVar(value=50)
        ttk.Scale(einst, from_=10, to=100, variable=self.tempo_var, command=lambda _v: self.senden()
                  ).grid(row=0, column=1, sticky="ew", padx=5)
        self.tempo_lbl = ttk.Label(einst, width=5)
        self.tempo_lbl.grid(row=0, column=2)

        ttk.Label(einst, text="Stopp-Abstand (mm)").grid(row=1, column=0, sticky="w")
        self.grenze_var = tk.IntVar(value=100)
        ttk.Scale(einst, from_=30, to=500, variable=self.grenze_var, command=lambda _v: self.senden()
                  ).grid(row=1, column=1, sticky="ew", padx=5)
        self.grenze_lbl = ttk.Label(einst, width=5)
        self.grenze_lbl.grid(row=1, column=2)

        self.tauschen_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(einst, text="Links/Rechts tauschen", variable=self.tauschen_var,
                        command=self.senden).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        einst.columnconfigure(1, weight=1)

        ttk.Label(root, text="Steuern mit den Pfeiltasten  ←  →  (beide = beide Motoren)",
                  padding=10).pack()

        # --- Tasten ---
        for taste in ("Left", "Right"):
            root.bind(f"<KeyPress-{taste}>", lambda e, t=taste: self.taste_runter(t))
            root.bind(f"<KeyRelease-{taste}>", lambda e, t=taste: self.taste_hoch(t))
        root.bind("<FocusOut>", lambda e: self.alle_los())
        root.protocol("WM_DELETE_WINDOW", self.beenden)

        self.senden()
        self.root.after(30, self.nachrichten_pruefen)

    # ---------- Anzeige ----------
    def _baue_anzeige(self):
        c = self.canvas
        self.motor_l = c.create_rectangle(30, 30, 170, 110, fill="#333", outline="#666", width=2)
        self.motor_r = c.create_rectangle(310, 30, 450, 110, fill="#333", outline="#666", width=2)
        c.create_text(100, 70, text="◀  LINKS", fill="white", font=("Segoe UI", 14, "bold"))
        c.create_text(380, 70, text="RECHTS  ▶", fill="white", font=("Segoe UI", 14, "bold"))
        self.abstand_txt = c.create_text(240, 55, text="– mm", fill="white", font=("Segoe UI", 16, "bold"))
        c.create_text(240, 85, text="Abstand", fill="#aaa", font=("Segoe UI", 10))
        c.create_rectangle(30, 140, 450, 160, outline="#666")
        self.balken = c.create_rectangle(30, 140, 30, 160, fill="#3a8", width=0)
        self.grenz_strich = c.create_line(30, 135, 30, 165, fill="orange", width=2)
        self.warnung = c.create_text(240, 185, text="", fill="#ff5050", font=("Segoe UI", 13, "bold"))

    def zeige_motoren(self, maske, blockiert):
        farbe_an = "#c0392b" if blockiert else "#27ae60"
        self.canvas.itemconfig(self.motor_l, fill=farbe_an if maske & 1 else "#333")
        self.canvas.itemconfig(self.motor_r, fill=farbe_an if maske & 2 else "#333")

    def zeige_abstand(self, mm, blockiert):
        skala = 1000  # mm für vollen Balken
        breite = 420 * min(mm, skala) / skala
        self.canvas.coords(self.balken, 30, 140, 30 + breite, 160)
        self.canvas.itemconfig(self.balken, fill="#c0392b" if blockiert else "#3a8")
        self.canvas.itemconfig(self.abstand_txt, text="frei" if mm >= 2000 else f"{mm} mm")
        self.canvas.itemconfig(self.warnung, text="HINDERNIS – angehalten" if blockiert else "")

    # ---------- Tasten ----------
    def taste_runter(self, taste):
        timer = self._loslassen_timer.pop(taste, None)
        if timer:
            self.root.after_cancel(timer)
        if taste not in self.gedrueckt:
            self.gedrueckt.add(taste)
            self.senden()

    def taste_hoch(self, taste):
        # kurz verzögern, damit die Tasten-Wiederholung kein Flackern auslöst
        self._loslassen_timer[taste] = self.root.after(40, lambda: self._wirklich_los(taste))

    def _wirklich_los(self, taste):
        self._loslassen_timer.pop(taste, None)
        self.gedrueckt.discard(taste)
        self.senden()

    def alle_los(self):
        self.gedrueckt.clear()
        self.senden()

    def senden(self):
        links, rechts = "Left" in self.gedrueckt, "Right" in self.gedrueckt
        if self.tauschen_var.get():
            links, rechts = rechts, links
        maske = (1 if links else 0) | (2 if rechts else 0)
        tempo, grenze = int(self.tempo_var.get()), int(self.grenze_var.get())
        self.tempo_lbl.config(text=f"{tempo}")
        self.grenze_lbl.config(text=f"{grenze}")
        x = 30 + 420 * min(grenze, 1000) / 1000
        self.canvas.coords(self.grenz_strich, x, 135, x, 165)
        self.hub.aktualisieren(maske if self.verbunden else 0, tempo, grenze)
        if not self.verbunden:
            self.zeige_motoren(maske, False)

    # ---------- Verbindung ----------
    def verbinden_klick(self):
        if self.verbunden or self.knopf["text"] == "Abbrechen":
            self.hub.trennen()
        else:
            self.letzter_fehler = ""
            self.knopf.config(text="Abbrechen")
            self.hub.verbinden(self.name_var.get())

    def nachrichten_pruefen(self):
        try:
            while True:
                art, *daten = self.nachrichten.get_nowait()
                if art == "zustand":
                    zustand, text = daten
                    if zustand == "getrennt" and self.letzter_fehler:
                        text = "Getrennt – " + self.letzter_fehler
                    self.status_var.set(text)
                    self.verbunden = zustand == "verbunden"
                    self.knopf.config(text={"verbunden": "Trennen", "suche": "Abbrechen"}
                                      .get(zustand, "Verbinden"))
                    self.senden()
                elif art == "ports":
                    l, r, s, li = (daten[0] + ["-", "-", "-", "-"])[:4]
                    self.ports_var.set(f"Ports:  Motor links {l}   Motor rechts {r}   "
                                       f"Abstandssensor {s}   Licht {li}")
                elif art == "status":
                    mm, blockiert, maske = daten
                    self.zeige_abstand(mm, blockiert)
                    self.zeige_motoren(maske, blockiert)
                elif art == "fehler":
                    self.letzter_fehler = daten[0]
                    self.status_var.set("Fehler: " + daten[0])
                elif art == "log":
                    print("Hub:", daten[0])
        except queue.Empty:
            pass
        self.root.after(30, self.nachrichten_pruefen)

    def beenden(self):
        self.gedrueckt.clear()
        self.hub.schliessen()
        self.root.destroy()


if __name__ == "__main__":
    fenster = tk.Tk()
    App(fenster)
    fenster.mainloop()
