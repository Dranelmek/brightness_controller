import queue
import threading
import tkinter as tk

import controller

SCAN_INTERVAL_MS = 3000  # how often to look for connected/disconnected monitors
MIN_BRIGHTNESS = 1
MAX_BRIGHTNESS = 100
TITLE_FONT = ("Franklin Gothic Heavy", 18)
VALUE_FONT = ("consolas", 8)
NOTE_FONT = ("Segoe UI", 8)


class _Writer(threading.Thread):
    """Applies brightness changes off the UI thread.

    Dragging a slider produces many values faster than DDC/CI can apply them,
    so only the latest value per monitor is kept.
    """

    def __init__(self, events):
        super().__init__(daemon=True)
        self._events = events
        self._pending = {}
        self._lock = threading.Lock()
        self._wake = threading.Event()

    def submit(self, monitor, value):
        with self._lock:
            self._pending[monitor.key] = (monitor, value)
        self._wake.set()

    def run(self):
        while True:
            self._wake.wait()
            with self._lock:
                batch = list(self._pending.values())
                self._pending.clear()
                self._wake.clear()
            for monitor, value in batch:
                try:
                    controller.set_brightness(monitor, value)
                    ok = True
                except Exception:
                    ok = False
                self._events.put(("written", monitor.key, ok))


class _MonitorColumn:
    """A labelled vertical slider for one monitor."""

    def __init__(self, parent, monitor, initial, on_change):
        self.monitor = monitor
        self.applied = initial  # last value sent to (or read from) the monitor
        self.touched = False    # user moved it before the initial read finished
        self._on_change = on_change

        self.frame = tk.Frame(parent, padx=10)
        tk.Label(self.frame, text=monitor.name, wraplength=110).pack()
        self.var = tk.IntVar(value=initial)
        self.scale = tk.Scale(
            self.frame, variable=self.var, from_=MAX_BRIGHTNESS, to=MIN_BRIGHTNESS,
            orient=tk.VERTICAL, length=180, width=30, font=VALUE_FONT,
            command=self._changed,
        )
        self.scale.pack()
        self.note = tk.Label(self.frame, text="reading…", font=NOTE_FONT, fg="gray40")
        self.note.pack()

    def _changed(self, _value):
        value = self.var.get()
        if value != self.applied:  # ignore echoes of programmatic updates
            self.applied = value
            self.touched = True
            self._on_change(self, value)

    def show(self, value):
        """Move the slider without sending a new value to the monitor."""
        self.applied = value
        self.var.set(value)

    def set_note(self, text):
        self.note.config(text=text)


class BrightnessApp:
    def __init__(self, root):
        self.root = root
        root.title("Screen Brightness")
        root.resizable(False, False)
        root.minsize(400, 0)

        self._events = queue.Queue()
        self._writer = _Writer(self._events)
        self._writer.start()
        self._columns = {}  # Monitor.key -> _MonitorColumn
        self._scanning = False

        tk.Label(root, text="Brightness", font=TITLE_FONT).pack(padx=20, pady=(10, 0))

        master = tk.Frame(root)
        master.pack(fill=tk.X, padx=10)
        tk.Label(master, text="All monitors").pack(anchor=tk.W)
        self._master_var = tk.IntVar(value=50)
        self._master_applied = 50
        tk.Scale(
            master, variable=self._master_var, from_=MIN_BRIGHTNESS, to=MAX_BRIGHTNESS,
            orient=tk.HORIZONTAL, length=380, width=30, font=VALUE_FONT,
            command=self._master_changed,
        ).pack(fill=tk.X)

        self._status = tk.Label(root, text="Looking for monitors…", font=NOTE_FONT, fg="gray40")
        self._status.pack(pady=(8, 0))
        self._monitor_row = tk.Frame(root)
        self._monitor_row.pack(padx=10, pady=10)

        self._scan()
        self._drain_events()

    # --- slider callbacks -------------------------------------------------

    def _master_changed(self, _value):
        value = self._master_var.get()
        if value == self._master_applied:
            return
        self._master_applied = value
        for column in self._columns.values():
            column.touched = True
            column.show(value)
            self._writer.submit(column.monitor, value)

    def _monitor_changed(self, column, value):
        self._writer.submit(column.monitor, value)

    def _show_master(self, value):
        self._master_applied = value
        self._master_var.set(value)

    # --- background work --------------------------------------------------

    def _scan(self):
        if not self._scanning:
            self._scanning = True
            threading.Thread(target=self._scan_worker, daemon=True).start()
        self.root.after(SCAN_INTERVAL_MS, self._scan)

    def _scan_worker(self):
        try:
            monitors = controller.list_monitors()
        except Exception:
            monitors = None
        self._events.put(("monitors", monitors))

    def _read_worker(self, monitor):
        self._events.put(("read", monitor.key, controller.get_brightness(monitor)))

    def _drain_events(self):
        try:
            while True:
                event = self._events.get_nowait()
                getattr(self, "_on_" + event[0])(*event[1:])
        except queue.Empty:
            pass
        self.root.after(50, self._drain_events)

    # --- event handlers (main thread) -------------------------------------

    def _on_monitors(self, monitors):
        self._scanning = False
        if monitors is None:
            return  # transient enumeration failure; keep what we have

        current = {m.key: m for m in monitors}
        for key in list(self._columns):
            if key not in current:
                self._columns.pop(key).frame.destroy()

        for monitor in monitors:
            column = self._columns.get(monitor.key)
            if column is not None:
                column.monitor = monitor  # index may have shifted
                continue
            column = _MonitorColumn(
                self._monitor_row, monitor, self._master_var.get(), self._monitor_changed
            )
            self._columns[monitor.key] = column
            threading.Thread(target=self._read_worker, args=(monitor,), daemon=True).start()

        # Keep columns in the system's monitor order.
        for monitor in monitors:
            column = self._columns[monitor.key]
            column.frame.pack_forget()
            column.frame.pack(side=tk.LEFT, anchor=tk.N)

        count = len(monitors)
        self._status.config(
            text="No monitors found" if count == 0
            else f"{count} monitor{'s' if count != 1 else ''} found"
        )

    def _on_read(self, key, value):
        column = self._columns.get(key)
        if column is None:
            return
        if value is None:
            column.set_note("level unknown")
        else:
            column.set_note("")
            if not column.touched:
                column.show(value)
        if not any(c.touched for c in self._columns.values()):
            known = [c.applied for c in self._columns.values() if c.note.cget("text") == ""]
            if known:
                self._show_master(round(sum(known) / len(known)))

    def _on_written(self, key, ok):
        column = self._columns.get(key)
        if column is None:
            return
        if not ok:
            column.set_note("not responding")
        elif column.note.cget("text") in ("not responding", "level unknown"):
            column.set_note("")


root = tk.Tk()
app = BrightnessApp(root)
