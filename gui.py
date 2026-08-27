"""
gui.py
------
Tkinter front-end for Spotify Playlister.

Pick the sync parameters in a window instead of typing CLI flags, then press
Run. The defaults match the values used by .github/workflows/sync.yml.

Run from the repository root (the secrets file and the token cache are
resolved relative to the working directory, exactly as for the CLI):

    python gui.py

On macOS the start date is chosen with the system's own NSDatePicker (needs
pyobjc-framework-Cocoa, in requirements.txt); elsewhere the window falls back
to year / month / day spinboxes.
"""

import argparse
import calendar
import contextlib
import queue
import sys
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, scrolledtext, ttk

from main import main
from src.config import VALID_INTERVALS, VALID_STYLES

try:
    import AppKit
    import Foundation

    NATIVE_DATE_PICKER = sys.platform == "darwin"
except ImportError:  # pyobjc not installed, or not on macOS
    NATIVE_DATE_PICKER = False


# Defaults taken from .github/workflows/sync.yml
DEFAULT_START_DATE = "2016-01-01"
DEFAULT_INTERVAL = 12
DEFAULT_STYLE = "short"
DEFAULT_PREFIX = "Fede's songs"
DEFAULT_SECRETS = "secrets.txt"

_DONE = object()  # sentinel pushed on the queue when the worker finishes


def _nsdate_formatter():
    fmt = Foundation.NSDateFormatter.alloc().init()
    fmt.setDateFormat_("yyyy-MM-dd")
    return fmt


class _QueueWriter:
    """Minimal file-like object that forwards print() output to a queue."""

    def __init__(self, q: "queue.Queue") -> None:
        self._queue = q

    def write(self, text: str) -> int:
        self._queue.put(text)
        return len(text)

    def flush(self) -> None:
        pass


class PlaylisterGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.queue: "queue.Queue" = queue.Queue()

        root.title("Spotify Playlister")

        _default = date.fromisoformat(DEFAULT_START_DATE)
        self.start_date = tk.StringVar(value=DEFAULT_START_DATE)
        self.year       = tk.StringVar(value=f"{_default.year:04d}")
        self.month      = tk.StringVar(value=f"{_default.month:02d}")
        self.day        = tk.StringVar(value=f"{_default.day:02d}")
        self.interval   = tk.StringVar(value=str(DEFAULT_INTERVAL))
        self.style      = tk.StringVar(value=DEFAULT_STYLE)
        self.prefix     = tk.StringVar(value=DEFAULT_PREFIX)
        self.secrets    = tk.StringVar(value=DEFAULT_SECRETS)
        self.private    = tk.BooleanVar(value=False)
        self.no_remove  = tk.BooleanVar(value=False)
        self.dry_run    = tk.BooleanVar(value=False)

        # --- Parameter form -------------------------------------------------------
        form = ttk.Frame(root, padding=10)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Start date").grid(row=0, column=0, sticky="w", pady=2)
        date_box = ttk.Frame(form)
        date_box.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)

        if NATIVE_DATE_PICKER:
            ttk.Entry(
                date_box, textvariable=self.start_date, width=12, state="readonly"
            ).grid(row=0, column=0)
            ttk.Button(date_box, text="Choose...", command=self._pick_date_native).grid(
                row=0, column=1, padx=(5, 0)
            )
        else:
            ttk.Spinbox(
                date_box, textvariable=self.year, from_=2008, to=date.today().year,
                format="%04.0f", width=6,
            ).grid(row=0, column=0)
            ttk.Label(date_box, text="-").grid(row=0, column=1, padx=2)
            ttk.Spinbox(
                date_box, textvariable=self.month, from_=1, to=12,
                format="%02.0f", width=4,
            ).grid(row=0, column=2)
            ttk.Label(date_box, text="-").grid(row=0, column=3, padx=2)
            self.day_spin = ttk.Spinbox(
                date_box, textvariable=self.day, from_=1, to=31,
                format="%02.0f", width=4,
            )
            self.day_spin.grid(row=0, column=4)
            ttk.Label(date_box, text="year - month - day").grid(row=0, column=5, padx=(8, 0))

            # Keep the day spinbox in step with the length of the selected month.
            self.year.trace_add("write", self._update_day_range)
            self.month.trace_add("write", self._update_day_range)

        ttk.Label(form, text="Interval (months)").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form,
            textvariable=self.interval,
            state="readonly",
            values=[str(i) for i in VALID_INTERVALS],
        ).grid(row=1, column=1, columnspan=2, sticky="ew", pady=2)

        ttk.Label(form, text="Naming style").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form,
            textvariable=self.style,
            state="readonly",
            values=VALID_STYLES,
        ).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)

        ttk.Label(form, text="Prefix").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.prefix).grid(
            row=3, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(form, text="Secrets file").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.secrets).grid(row=4, column=1, sticky="ew", pady=2)
        ttk.Button(form, text="Browse...", command=self._browse_secrets).grid(
            row=4, column=2, sticky="e", padx=(5, 0)
        )

        ttk.Checkbutton(
            form, text="Create playlists as private", variable=self.private
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            form, text="Do not remove unliked tracks", variable=self.no_remove
        ).grid(row=6, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(
            form, text="Dry run (no changes to Spotify)", variable=self.dry_run
        ).grid(row=7, column=0, columnspan=3, sticky="w")

        self.run_button = ttk.Button(form, text="Run playlister", command=self._run)
        self.run_button.grid(row=8, column=0, columnspan=3, sticky="e", pady=(10, 0))

        # --- Log pane -------------------------------------------------------------
        self.log = scrolledtext.ScrolledText(root, height=18, width=80, state="disabled")
        self.log.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self.root.after(100, self._poll_queue)

    def _pick_date_native(self) -> None:
        """Open macOS's own NSDatePicker in a modal panel and take the result."""
        fmt = _nsdate_formatter()

        picker = AppKit.NSDatePicker.alloc().initWithFrame_(
            Foundation.NSMakeRect(0, 0, 320, 160)
        )
        picker.setDatePickerStyle_(AppKit.NSDatePickerStyleClockAndCalendar)
        picker.setDatePickerElements_(AppKit.NSDatePickerElementFlagYearMonthDay)
        picker.setDateValue_(fmt.dateFromString_(self.start_date.get()))

        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Start date")
        alert.setInformativeText_(
            "Only tracks saved on or after this date are processed."
        )
        alert.addButtonWithTitle_("Select")
        alert.addButtonWithTitle_("Cancel")
        alert.setAccessoryView_(picker)

        if alert.runModal() == AppKit.NSAlertFirstButtonReturn:
            self.start_date.set(fmt.stringFromDate_(picker.dateValue()))

    def _selected_date(self) -> date:
        """The chosen start date, from whichever picker this platform got."""
        if NATIVE_DATE_PICKER:
            return date.fromisoformat(self.start_date.get())
        return date(int(self.year.get()), int(self.month.get()), int(self.day.get()))

    def _update_day_range(self, *_args) -> None:
        """Clamp the day spinbox to the number of days in the selected month."""
        try:
            last_day = calendar.monthrange(int(self.year.get()), int(self.month.get()))[1]
        except ValueError:
            return  # half-typed year or month; nothing to clamp to yet

        self.day_spin.configure(to=last_day)
        if self.day.get().isdigit() and int(self.day.get()) > last_day:
            self.day.set(f"{last_day:02d}")

    def _browse_secrets(self) -> None:
        path = filedialog.askopenfilename(title="Select secrets file")
        if path:
            self.secrets.set(path)

    def _run(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

        try:
            start_date = self._selected_date()
        except ValueError as exc:
            self._append_log(f"[error] Invalid start date: {exc}\n")
            return

        args = argparse.Namespace(
            start_date=start_date.isoformat(),
            interval=int(self.interval.get()),
            style=self.style.get(),
            prefix=self.prefix.get(),
            private=self.private.get(),
            no_remove=self.no_remove.get(),
            dry_run=self.dry_run.get(),
            secrets=self.secrets.get().strip(),
        )

        self.run_button.state(["disabled"])
        threading.Thread(target=self._worker, args=(args,), daemon=True).start()

    def _worker(self, args: argparse.Namespace) -> None:
        """Run the sync off the UI thread, with stdout forwarded to the queue."""
        try:
            with contextlib.redirect_stdout(_QueueWriter(self.queue)):
                try:
                    main(args)
                except SystemExit:
                    # main() already printed its '[error] ...' line before exiting.
                    pass
                except Exception as exc:
                    print(f"[error] {exc}")
        finally:
            self.queue.put(_DONE)

    def _poll_queue(self) -> None:
        """Drain whatever the worker printed into the log pane (UI thread only)."""
        while True:
            try:
                item = self.queue.get_nowait()
            except queue.Empty:
                break

            if item is _DONE:
                self.run_button.state(["!disabled"])
            else:
                self._append_log(item)

        self.root.after(100, self._poll_queue)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    PlaylisterGUI(root)
    root.mainloop()
