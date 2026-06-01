# ThorCPY Linux - Dual-screen scrcpy docking and control UI
# Copyright (C) 2026 the_swest
# Contact: Github issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# src/file_browser_ui.py
#
# Two-panel ADB file browser (device <-> local PC) rendered in customtkinter.
# Reuses the platform-agnostic backend in src/file_browser.py. Tcl/Tk is not
# thread-safe, so background results are pushed onto a queue and applied on the
# Tk thread by a periodic _poll() loop rather than calling after() across threads.

import os
import queue
import logging
import customtkinter as ctk

from src.file_browser import (
    FileBrowserBackend, list_local_dir_async, local_op_async, delete_local,
)
from src.platform_compat import apply_dark_titlebar
from src.ui_constants import (
    BG_COLOUR, PANEL_COLOUR, BORDER_COLOUR, TEXT_COLOUR,
    ACCENT_COLOUR, TOP_COLOUR, BOTTOM_COLOUR,
    SUCCESS_COLOUR, DANGER_COLOUR, WARNING_COLOUR,
    make_font, load_calsans, apply_window_icon,
)

logger = logging.getLogger(__name__)


class FileBrowserWindow:
    """A modal-ish CTkToplevel hosting the device/local file browser."""

    def __init__(self, parent, scrcpy_manager):
        load_calsans()
        self.backend = FileBrowserBackend(scrcpy_manager.adb_bin, scrcpy_manager.serial)

        self.device_path = "/sdcard"
        self.local_path = os.path.expanduser("~")
        self.device_entries = []     # list[(name, is_dir, size)]
        self.local_entries = []
        self.device_sel = None       # selected name
        self.local_sel = None
        self.busy = False
        self._tried_fallback = False
        self._device_btns = {}        # name -> (button, is_dir) for cheap recolour
        self._local_btns = {}
        self._queue = queue.Queue()   # background results, drained on the Tk thread

        self.win = ctk.CTkToplevel(parent) if parent else ctk.CTk()
        self.win.title("ThorCPY File Browser")
        self.win.configure(fg_color=BG_COLOUR)
        self.win.geometry("780x620")
        self.win.minsize(640, 480)
        apply_window_icon(self.win)
        if parent:
            self.win.transient(parent)

        self._build_ui()
        self.win.update_idletasks()
        apply_dark_titlebar(self.win)

        self.win.after(50, self._poll)   # start draining background results
        self._load_device(self.device_path)
        self._load_local(self.local_path)

    def _poll(self):
        """Apply queued background-thread results on the Tk thread."""
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn()
                except Exception:
                    logger.exception("File browser result handler failed")
        except queue.Empty:
            pass
        try:
            self.win.after(50, self._poll)
        except Exception:
            pass   # window destroyed

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_columnconfigure(1, weight=1)
        self.win.grid_rowconfigure(1, weight=1)

        # Headers + path bars
        self.device_path_var = ctk.StringVar(value=self.device_path)
        self.local_path_var = ctk.StringVar(value=self.local_path)
        self._build_header(0, "DEVICE", TOP_COLOUR, self.device_path_var, self._refresh_device)
        self._build_header(1, "LOCAL PC", BOTTOM_COLOUR, self.local_path_var, self._refresh_local)

        # Scrollable file lists
        self.device_list = ctk.CTkScrollableFrame(
            self.win, fg_color=PANEL_COLOUR, scrollbar_button_color=BORDER_COLOUR)
        self.device_list.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=4)
        self.device_list.columnconfigure(0, weight=1)

        self.local_list = ctk.CTkScrollableFrame(
            self.win, fg_color=PANEL_COLOUR, scrollbar_button_color=BORDER_COLOUR)
        self.local_list.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=4)
        self.local_list.columnconfigure(0, weight=1)

        # Per-panel action rows
        self._build_actions(0, "dev")
        self._build_actions(1, "loc")

        # Transfer row
        transfer = ctk.CTkFrame(self.win, fg_color="transparent")
        transfer.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(2, 2))
        transfer.columnconfigure(0, weight=1)
        transfer.columnconfigure(1, weight=1)
        self.pull_btn = ctk.CTkButton(transfer, text="Download  v", command=self._pull,
                                      fg_color=SUCCESS_COLOUR, hover_color="#27ae60",
                                      font=make_font(13))
        self.pull_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.push_btn = ctk.CTkButton(transfer, text="Upload  ^", command=self._push,
                                      fg_color=ACCENT_COLOUR, hover_color="#3a7fc1",
                                      font=make_font(13))
        self.push_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Status + progress
        self.status = ctk.CTkLabel(self.win, text="Double-click a folder to open · single-click to select",
                                   text_color=(120, 120, 130) if False else "#7a808f",
                                   font=make_font(12))
        self.status.grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 0))
        self.progress = ctk.CTkProgressBar(self.win, progress_color=ACCENT_COLOUR)
        self.progress.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        self.progress.set(0)
        self.progress.grid_remove()

    def _build_header(self, col, title, colour, path_var, refresh_cmd):
        head = ctk.CTkFrame(self.win, fg_color="transparent")
        head.grid(row=0, column=col, sticky="ew", padx=(10, 5) if col == 0 else (5, 10), pady=(10, 0))
        head.columnconfigure(1, weight=1)
        ctk.CTkLabel(head, text=title, text_color=colour, font=make_font(13, "bold")
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="Refresh", width=70, command=refresh_cmd,
                      fg_color=PANEL_COLOUR, hover_color=BORDER_COLOUR, border_width=1,
                      border_color=BORDER_COLOUR, font=make_font(11)
                      ).grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(head, textvariable=path_var, text_color=TEXT_COLOUR, anchor="w",
                     font=make_font(11)).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 0))

    def _build_actions(self, col, side):
        row = ctk.CTkFrame(self.win, fg_color="transparent")
        row.grid(row=2, column=col, sticky="ew", padx=(10, 5) if col == 0 else (5, 10), pady=2)
        for i in range(4):
            row.columnconfigure(i, weight=1)
        mk = lambda text, cmd, c, color=PANEL_COLOUR: ctk.CTkButton(
            row, text=text, width=10, command=cmd, fg_color=color,
            hover_color=BORDER_COLOUR, border_width=1, border_color=BORDER_COLOUR,
            font=make_font(11))
        mk("< Back", lambda: self._back(side), 0).grid(row=0, column=0, sticky="ew", padx=1)
        mk("New", lambda: self._mkdir(side), 1).grid(row=0, column=1, sticky="ew", padx=1)
        mk("Rename", lambda: self._rename(side), 2).grid(row=0, column=2, sticky="ew", padx=1)
        mk("Delete", lambda: self._delete(side), 3, DANGER_COLOUR).grid(row=0, column=3, sticky="ew", padx=1)

    # ── Listing / rendering ──────────────────────────────────────────────
    def _load_device(self, path):
        self.device_path = path
        self.device_path_var.set(path)
        self.device_sel = None
        self._set_status(f"Loading {path} …", WARNING_COLOUR)

        def _cb(entries, error):
            def _apply():
                if error:
                    if path == "/sdcard" and not self._tried_fallback:
                        self._tried_fallback = True
                        self._load_device("/storage/emulated/0")
                        return
                    self.device_entries = []
                    self._render(self.device_list, [], "dev")
                    self._set_status(f"Error: {error}", DANGER_COLOUR)
                else:
                    self.device_entries = entries or []
                    self._render(self.device_list, self.device_entries, "dev")
                    self._set_status("")
            self._queue.put(_apply)

        self.backend.list_device_dir(path, _cb)

    def _load_local(self, path):
        self.local_path = path
        self.local_path_var.set(path)
        self.local_sel = None

        def _cb(entries, error):
            def _apply():
                if error:
                    self.local_entries = []
                    self._render(self.local_list, [], "loc")
                    self._set_status(f"Error: {error}", DANGER_COLOUR)
                else:
                    self.local_entries = entries or []
                    self._render(self.local_list, self.local_entries, "loc")
            self._queue.put(_apply)

        list_local_dir_async(path, _cb)

    def _bind_scroll(self, widget, frame):
        """Make the mouse wheel scroll `frame` while hovering `widget`.

        customtkinter's CTkScrollableFrame does not reliably forward wheel events
        from child widgets, so we route them to the frame's canvas ourselves.
        Handles X11 (Button-4/5) and Windows/macOS (MouseWheel).
        """
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return

        def _wheel(event):
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            elif getattr(event, "delta", 0):
                canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")
            return "break"

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, _wheel, add="+")

    def _render(self, frame, entries, side):
        for w in frame.winfo_children():
            w.destroy()
        btns = {}
        if side == "dev":
            self._device_btns = btns
        else:
            self._local_btns = btns
        self._bind_scroll(frame, frame)
        if not entries:
            empty = ctk.CTkLabel(frame, text="(empty)", text_color=BORDER_COLOUR,
                                 font=make_font(13))
            empty.pack(pady=8)
            self._bind_scroll(empty, frame)
            return
        sel = self.device_sel if side == "dev" else self.local_sel
        for name, is_dir, size in entries:
            label = f"{'/ ' if is_dir else '  '}{name}"
            if size:
                label = f"{label}    ({size})"
            btn = ctk.CTkButton(
                frame, text=label, anchor="w", height=24,
                fg_color=ACCENT_COLOUR if name == sel else "transparent",
                hover_color=BORDER_COLOUR,
                text_color=TOP_COLOUR if is_dir else TEXT_COLOUR,
                font=make_font(12),
                command=lambda n=name: self._select(side, n),
            )
            # Real double-click to open a folder (timing-independent, so it works
            # even though selecting does not rebuild the list).
            btn.bind("<Double-Button-1>", lambda e, n=name, d=is_dir: self._open(side, n, d))
            # Wheel events over a row must still scroll the list.
            self._bind_scroll(btn, frame)
            btn.pack(fill="x", padx=2, pady=1)
            btns[name] = (btn, is_dir)

    # ── Interaction ──────────────────────────────────────────────────────
    def _select(self, side, name):
        """Single click: select an entry (cheap — just recolours rows)."""
        if side == "dev":
            self.device_sel = name
        else:
            self.local_sel = name
        self._recolor(side)

    def _recolor(self, side):
        btns = self._device_btns if side == "dev" else self._local_btns
        sel = self.device_sel if side == "dev" else self.local_sel
        for name, (btn, _is_dir) in btns.items():
            try:
                btn.configure(fg_color=ACCENT_COLOUR if name == sel else "transparent")
            except Exception:
                pass

    def _open(self, side, name, is_dir):
        """Double click: open a folder; files just get selected."""
        if not is_dir:
            self._select(side, name)
            return
        if side == "dev":
            self._load_device(self.device_path.rstrip("/") + "/" + name)
        else:
            self._load_local(os.path.normpath(os.path.join(self.local_path, name)))

    def _back(self, side):
        if side == "dev":
            parent = self.device_path.rstrip("/").rsplit("/", 1)[0] or "/"
            self._load_device(parent)
        else:
            parent = os.path.dirname(self.local_path)
            if parent and parent != self.local_path:
                self._load_local(parent)

    def _refresh_device(self):
        self._load_device(self.device_path)

    def _refresh_local(self):
        self._load_local(self.local_path)

    # ── Transfers ────────────────────────────────────────────────────────
    def _pull(self):
        if self.busy or not self.device_sel:
            self._set_status("Select a device file first", DANGER_COLOUR)
            return
        name = self.device_sel
        device_path = self.device_path.rstrip("/") + "/" + name
        target = os.path.join(self.local_path, name)
        if os.path.exists(target):
            self._confirm(f"Overwrite '{name}' on local PC?", lambda: self._do_pull(device_path, name))
        else:
            self._do_pull(device_path, name)

    def _do_pull(self, device_path, name):
        self._begin_transfer(f"Downloading {name} …")

        def _prog(p):
            self._queue.put(lambda: self.progress.set(p / 100))

        def _cb(ok, msg):
            def _apply():
                self._end_transfer(ok, msg)
                if ok:
                    self._load_local(self.local_path)
            self._queue.put(_apply)

        self.backend.pull_file(device_path, self.local_path, _cb, _prog)

    def _push(self):
        if self.busy or not self.local_sel:
            self._set_status("Select a local file first", DANGER_COLOUR)
            return
        name = self.local_sel
        local_path = os.path.join(self.local_path, name)
        target = self.device_path.rstrip("/") + "/" + name

        def _after(exists):
            def _apply():
                if exists:
                    self._confirm(f"Overwrite '{name}' on device?", lambda: self._do_push(local_path, name))
                else:
                    self._do_push(local_path, name)
            self._queue.put(_apply)

        self.backend.exists_device(target, _after)

    def _do_push(self, local_path, name):
        self._begin_transfer(f"Uploading {name} …")

        def _prog(p):
            self._queue.put(lambda: self.progress.set(p / 100))

        def _cb(ok, msg):
            def _apply():
                self._end_transfer(ok, msg)
                if ok:
                    self._load_device(self.device_path)
            self._queue.put(_apply)

        self.backend.push_file(local_path, self.device_path, _cb, _prog)

    # ── New folder / rename / delete ─────────────────────────────────────
    def _mkdir(self, side):
        name = self._ask_text("New folder", "Folder name:")
        if not name or "/" in name:
            return
        if side == "dev":
            path = self.device_path.rstrip("/") + "/" + name
            self.backend.mkdir_device(path, self._dev_result())
        else:
            target = os.path.join(self.local_path, name)
            local_op_async(lambda: os.makedirs(target), self._local_result(),
                           "Folder created", "Could not create folder")

    def _rename(self, side):
        cur = self.device_sel if side == "dev" else self.local_sel
        if not cur:
            self._set_status("Select an item to rename", DANGER_COLOUR)
            return
        new = self._ask_text("Rename", "New name:", initial=cur)
        if not new or "/" in new or new == cur:
            return
        if side == "dev":
            old = self.device_path.rstrip("/") + "/" + cur
            dst = self.device_path.rstrip("/") + "/" + new
            self.backend.rename_device(old, dst, self._dev_result())
        else:
            old = os.path.join(self.local_path, cur)
            dst = os.path.join(self.local_path, new)
            local_op_async(lambda: os.rename(old, dst), self._local_result(),
                           "Renamed", "Rename failed")

    def _delete(self, side):
        cur = self.device_sel if side == "dev" else self.local_sel
        if not cur:
            self._set_status("Select an item to delete", DANGER_COLOUR)
            return
        where = "device" if side == "dev" else "local PC"
        if side == "dev":
            path = self.device_path.rstrip("/") + "/" + cur
            self._confirm(f"Delete '{cur}' on {where}?",
                          lambda: self.backend.delete_device(path, self._dev_result()))
        else:
            path = os.path.join(self.local_path, cur)
            self._confirm(f"Delete '{cur}' on {where}?",
                          lambda: local_op_async(lambda: delete_local(path), self._local_result(),
                                                 "Deleted", "Delete failed"))

    # ── Result helpers (marshal onto Tk thread) ──────────────────────────
    def _dev_result(self):
        def _cb(ok, msg):
            self._queue.put(lambda: (self._set_status(msg, SUCCESS_COLOUR if ok else DANGER_COLOUR),
                                       ok and self._load_device(self.device_path)))
        return _cb

    def _local_result(self):
        def _cb(ok, msg):
            self._queue.put(lambda: (self._set_status(msg, SUCCESS_COLOUR if ok else DANGER_COLOUR),
                                       ok and self._load_local(self.local_path)))
        return _cb

    # ── Small dialogs / status ───────────────────────────────────────────
    def _set_status(self, msg, colour="#7a808f"):
        self.status.configure(text=msg, text_color=colour)

    def _begin_transfer(self, msg):
        self.busy = True
        self.pull_btn.configure(state="disabled")
        self.push_btn.configure(state="disabled")
        self.progress.set(0)
        self.progress.grid()
        self._set_status(msg, WARNING_COLOUR)

    def _end_transfer(self, ok, msg):
        self.busy = False
        self.pull_btn.configure(state="normal")
        self.push_btn.configure(state="normal")
        self.progress.grid_remove()
        self._set_status(msg, SUCCESS_COLOUR if ok else DANGER_COLOUR)

    def _ask_text(self, title, prompt, initial=""):
        dlg = ctk.CTkInputDialog(title=title, text=prompt)
        if initial:
            try:
                dlg._entry.insert(0, initial)
            except Exception:
                pass
        val = dlg.get_input()
        return val.strip() if val else None

    def _confirm(self, message, on_yes):
        win = ctk.CTkToplevel(self.win)
        win.title("Confirm")
        win.configure(fg_color=BG_COLOUR)
        win.geometry("360x150")
        win.transient(self.win)
        win.grab_set()
        apply_dark_titlebar(win)
        ctk.CTkLabel(win, text=message, text_color=TEXT_COLOUR, font=make_font(13),
                     wraplength=320).pack(pady=(24, 16), padx=16)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack()

        def _yes():
            win.destroy()
            on_yes()

        ctk.CTkButton(row, text="Yes", width=90, fg_color=DANGER_COLOUR, hover_color="#c0392b",
                      command=_yes, font=make_font(13)).pack(side="left", padx=6)
        ctk.CTkButton(row, text="No", width=90, fg_color=PANEL_COLOUR, hover_color=BORDER_COLOUR,
                      command=win.destroy, font=make_font(13)).pack(side="left", padx=6)


def open_file_browser(parent, scrcpy_manager):
    """Open the file browser window. Requires a connected device."""
    if not scrcpy_manager or not scrcpy_manager.adb_bin or not scrcpy_manager.serial:
        logger.warning("File browser requested without a connected device")
        return None
    return FileBrowserWindow(parent, scrcpy_manager)
