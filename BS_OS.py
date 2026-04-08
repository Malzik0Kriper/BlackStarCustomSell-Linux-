import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os, sys, subprocess, threading, datetime, ctypes, winreg
from pathlib import Path
from PIL import Image, ImageTk
import psutil
import platform

def open_uri(uri: str):
    if platform.system() == "Windows":
        os.startfile(uri)
    else:
        subprocess.Popen(['xdg-open', uri])
 
try:
    import win32gui, win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
 
# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
PROG_DIR    = BASE_DIR / "program"
WALL_DIR    = BASE_DIR / "Wallpaper"
ICON_PATH   = BASE_DIR / "icon.png"
CURSOR_PATH = BASE_DIR / "BSC.cur"
 
# ── Palette ────────────────────────────────────────────────────────────────────
ACCENT    = "#0078D4"
ACCENT_H  = "#1090E0"
BG_DARK   = "#111111"
BG_PANEL  = "#1E1E1E"
BG_CARD   = "#2A2A2A"
BG_HOVER  = "#3A3A3A"     # solid hover — no alpha codes!
TEXT_PRI  = "#FFFFFF"
TEXT_SEC  = "#AAAAAA"
BORDER    = "#3A3A3A"
SEP       = "#2E2E2E"
 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
 
 
# ── Helpers ────────────────────────────────────────────────────────────────────
 
def safe_popen(cmd):
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(cmd, creationflags=flags)
    except Exception as e:
        print(f"[WARN] {cmd}: {e}")
 
 
def open_uri(uri: str):
    """Open ms-settings:, shell:, http, or file paths."""
    try:
        os.startfile(uri)
    except Exception as e:
        print(f"[WARN] startfile {uri}: {e}")
 
 
def get_exe_icon_ctk(path: Path, size=24):
    """Return CTkImage from .exe icon, or None."""
    if not HAS_WIN32:
        return None
    try:
        import win32ui
        large, small = win32gui.ExtractIconEx(str(path), 0)
        hicon = (large or small)
        if not hicon:
            return None
        hicon = hicon[0]
        hdc  = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 32, 32)
        mdc  = hdc.CreateCompatibleDC()
        mdc.SelectObject(hbmp)
        win32gui.DrawIconEx(mdc.GetHandleOutput(), 0, 0, hicon,
                            32, 32, 0, None, win32con.DI_NORMAL)
        info = hbmp.GetInfo()
        bits = hbmp.GetBitmapBits(True)
        img  = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                                bits, "raw", "BGRX", 0, 1)
        img  = img.resize((size, size), Image.LANCZOS)
        win32gui.DestroyIcon(hicon)
        return ctk.CTkImage(img, size=(size, size))
    except Exception:
        return None
 
 
def get_shell_icon_ctk(path: Path, size=28):
    """Return CTkImage via SHGetFileInfoW (ctypes only, no win32com)."""
    if not HAS_WIN32:
        return None
    try:
        import win32ui
        import ctypes.wintypes as wt
 
        SHGFI_ICON      = 0x100
        SHGFI_SMALLICON = 0x001
 
        class SHFILEINFO(ctypes.Structure):
            _fields_ = [("hIcon", wt.HICON),("iIcon", ctypes.c_int),
                        ("dwAttributes", wt.DWORD),
                        ("szDisplayName", ctypes.c_wchar * 260),
                        ("szTypeName", ctypes.c_wchar * 80)]
 
        info  = SHFILEINFO()
        ret   = ctypes.windll.shell32.SHGetFileInfoW(
                    str(path), 0, ctypes.byref(info),
                    ctypes.sizeof(info), SHGFI_ICON | SHGFI_SMALLICON)
        if not ret or not info.hIcon:
            return None
 
        hdc  = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, size, size)
        mdc  = hdc.CreateCompatibleDC()
        mdc.SelectObject(hbmp)
        win32gui.DrawIconEx(mdc.GetHandleOutput(), 0, 0, info.hIcon,
                            size, size, 0, None, win32con.DI_NORMAL)
        bi   = hbmp.GetInfo()
        bits = hbmp.GetBitmapBits(True)
        img  = Image.frombuffer("RGB", (bi["bmWidth"], bi["bmHeight"]),
                                bits, "raw", "BGRX", 0, 1)
        img  = img.resize((size, size), Image.LANCZOS)
        ctypes.windll.user32.DestroyIcon(info.hIcon)
        return ctk.CTkImage(img, size=(size, size))
    except Exception:
        return None
 
 
def get_wallpaper() -> Path | None:
    h     = datetime.datetime.now().hour
    night = h < 7 or h >= 20
    if not WALL_DIR.exists():
        return None
    if night:
        cands = list(WALL_DIR.glob("*night*"))
    else:
        cands = [p for p in WALL_DIR.glob("*.png") if "night" not in p.name.lower()]
    if not cands:
        cands = list(WALL_DIR.glob("*.png"))
    return cands[0] if cands else None
 
 
def get_desktop_items() -> list[Path]:
    desktop = Path(os.path.expanduser("~/Desktop"))
    if not desktop.exists():
        return []
    items = [p for p in sorted(desktop.iterdir()) if not p.name.startswith(".")]
    return items[:40]
 
 
def get_running_windows():
    if not HAS_WIN32:
        return []
    skip = {"", "Default IME", "MSCTFIME UI", "Program Manager"}
    result = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t and t not in skip:
                result.append((t[:30], hwnd))
    win32gui.EnumWindows(cb, None)
    return result[:16]
 
 
def get_installed_programs():
    apps = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, rpath in keys:
        try:
            reg = winreg.OpenKey(hive, rpath)
            for i in range(winreg.QueryInfoKey(reg)[0]):
                try:
                    sub = winreg.OpenKey(reg, winreg.EnumKey(reg, i))
                    name = winreg.QueryValueEx(sub, "DisplayName")[0]
                    try:
                        ico = winreg.QueryValueEx(sub, "DisplayIcon")[0]
                        exe = ico.split(",")[0].strip('"').strip()
                    except Exception:
                        exe = ""
                    if name:
                        apps.append((name.strip(), exe))
                except Exception:
                    pass
        except Exception:
            pass
    seen, unique = set(), []
    for name, exe in sorted(apps, key=lambda x: x[0].lower()):
        if name not in seen:
            seen.add(name)
            unique.append((name, exe))
    return unique
 
 
def set_custom_cursor(path: Path):
    if path.exists():
        try:
            hcur = ctypes.windll.user32.LoadCursorFromFileW(str(path))
            if hcur:
                ctypes.windll.user32.SetSystemCursor(hcur, 32512)
        except Exception:
            pass
 
 
def restore_cursors():
    try:
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    except Exception:
        pass
 
 
def add_tooltip(widget, text: str):
    tip = None
    def show(e):
        nonlocal tip
        tip = tk.Toplevel(widget)
        tip.overrideredirect(True)
        tip.wm_attributes("-topmost", True)
        tk.Label(tip, text=text, bg=BG_CARD, fg=TEXT_PRI,
                 font=("Segoe UI", 9), padx=6, pady=3).pack()
        tip.geometry(f"+{e.x_root+10}+{e.y_root+22}")
    def hide(e):
        nonlocal tip
        if tip:
            tip.destroy(); tip = None
    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")
 
 
# ── Win11 Context Menu ─────────────────────────────────────────────────────────
 
class CtxMenu(tk.Toplevel):
    """items: list of (label, callback) or None for separator."""
    def __init__(self, root, x, y, items):
        super().__init__(root)
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.configure(bg=BORDER)
        inner = tk.Frame(self, bg=BG_PANEL, padx=0, pady=6)
        inner.pack(padx=1, pady=1)
        for item in items:
            if item is None:
                tk.Frame(inner, height=1, bg=SEP).pack(fill="x", padx=10, pady=3)
                continue
            label, cb = item
            row = tk.Frame(inner, bg=BG_PANEL, cursor="hand2")
            row.pack(fill="x", padx=4)
            lbl = tk.Label(row, text=label, bg=BG_PANEL, fg=TEXT_PRI,
                           font=("Segoe UI", 10), anchor="w",
                           padx=14, pady=7)
            lbl.pack(fill="x")
            def enter(e, r=row, l=lbl): r.config(bg=ACCENT); l.config(bg=ACCENT)
            def leave(e, r=row, l=lbl): r.config(bg=BG_PANEL); l.config(bg=BG_PANEL)
            def click(e, c=cb): self._run(c)
            for w in (row, lbl):
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)
                w.bind("<Button-1>", click)
        self.update_idletasks()
        w = self.winfo_reqwidth(); h = self.winfo_reqheight()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        x = min(x, sw-w-8); y = min(y, sh-h-8)
        self.geometry(f"+{x}+{y}")
        self.focus_force()
        self.bind("<FocusOut>", lambda e: self.destroy())
 
    def _run(self, cb):
        self.destroy()
        if cb:
            try: cb()
            except Exception as ex: print(f"[Ctx] {ex}")
 
 
# ── Start Menu ─────────────────────────────────────────────────────────────────
 
class StartMenu(ctk.CTkToplevel):
    def __init__(self, master, programs, anchor_x, anchor_y):
        super().__init__(master)
        self.programs    = programs
        self._inst_cache = None
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.configure(fg_color=BG_PANEL)
 
        # Header
        hdr = ctk.CTkFrame(self, fg_color=BG_DARK, height=52, corner_radius=0)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⬛  BLACKSTAR",
                     font=("Segoe UI", 14, "bold"),
                     text_color=TEXT_PRI).pack(side="left", padx=16)
 
        # Search
        self._q = ctk.StringVar()
        self._q.trace_add("write", self._on_search)
        ctk.CTkEntry(self, placeholder_text="🔍  Пошук...",
                     textvariable=self._q,
                     fg_color=BG_CARD, border_color=BORDER,
                     font=("Segoe UI", 11)
                     ).pack(fill="x", padx=12, pady=(10, 4))
 
        # Tab bar
        tbar = ctk.CTkFrame(self, fg_color="transparent", height=36)
        tbar.pack(fill="x", padx=12); tbar.pack_propagate(False)
        self._tab = tk.StringVar(value="bs")
        ctk.CTkRadioButton(tbar, text="BLACKSTAR", variable=self._tab,
                           value="bs", fg_color=ACCENT,
                           font=("Segoe UI", 10), text_color=TEXT_PRI,
                           command=self._switch).pack(side="left", padx=(0,12))
        ctk.CTkRadioButton(tbar, text="Встановлені", variable=self._tab,
                           value="inst", fg_color=ACCENT,
                           font=("Segoe UI", 10), text_color=TEXT_PRI,
                           command=self._switch).pack(side="left")
 
        # Scroll
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                               scrollbar_button_color=ACCENT)
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
 
        # Footer
        ftr = ctk.CTkFrame(self, fg_color=BG_DARK, height=48, corner_radius=0)
        ftr.pack(fill="x", side="bottom"); ftr.pack_propagate(False)
        ctk.CTkButton(ftr, text="⏻  Живлення",
                      fg_color="transparent", hover_color="#770000",
                      text_color=TEXT_SEC, font=("Segoe UI", 10), width=110,
                      command=self._power).pack(side="right", padx=10, pady=8)
 
        self._render_bs(programs)
 
        self.update_idletasks()
        w = 400; h = 560
        self.geometry(f"{w}x{h}+{anchor_x}+{anchor_y}")
        self.focus_force()
        self.bind("<FocusOut>", lambda e: self.destroy())
 
    # ── helpers ──
    def _clear(self):
        for w in self._scroll.winfo_children():
            w.destroy()
 
    def _row(self, name, icon, cb):
        row = ctk.CTkFrame(self._scroll, fg_color="transparent",
                           corner_radius=8, cursor="hand2")
        row.pack(fill="x", pady=2, padx=4)
        if icon:
            ctk.CTkLabel(row, image=icon, text="").pack(
                side="left", padx=(8,4), pady=4)
        ctk.CTkLabel(row, text=name, font=("Segoe UI",11),
                     text_color=TEXT_PRI, anchor="w").pack(
            side="left", padx=4, pady=8, fill="x", expand=True)
        def enter(e, r=row): r.configure(fg_color=BG_CARD)
        def leave(e, r=row): r.configure(fg_color="transparent")
        for w in (row, *row.winfo_children()):
            w.bind("<Enter>", enter, add="+")
            w.bind("<Leave>", leave, add="+")
            w.bind("<Button-1>", lambda e, c=cb: c(), add="+")
 
    def _render_bs(self, progs):
        self._clear()
        if not progs:
            ctk.CTkLabel(self._scroll, text="Немає .exe у папці program/",
                         text_color=TEXT_SEC).pack(pady=20)
            return
        for p in progs:
            icon = get_exe_icon_ctk(p, 22)
            def launch(path=p):
                self.destroy()
                try: subprocess.Popen([str(path)], cwd=str(path.parent))
                except Exception as ex: print(ex)
            self._row(p.stem, icon, launch)
 
    def _render_inst(self, apps=None):
        self._clear()
        if apps is None:
            ctk.CTkLabel(self._scroll, text="⏳ Завантаження списку...",
                         text_color=TEXT_SEC).pack(pady=20)
            def load():
                if self._inst_cache is None:
                    self._inst_cache = get_installed_programs()
                self.after(0, lambda: self._render_inst(self._inst_cache))
            threading.Thread(target=load, daemon=True).start()
            return
        q = self._q.get().lower()
        filtered = [(n,e) for n,e in apps if q in n.lower()][:150]
        if not filtered:
            ctk.CTkLabel(self._scroll, text="Нічого не знайдено",
                         text_color=TEXT_SEC).pack(pady=20); return
        for name, exe in filtered:
            exe_path = Path(exe) if exe else None
            icon = get_exe_icon_ctk(exe_path, 22) if exe_path and exe_path.exists() else None
            def launch(e=exe, n=name):
                self.destroy()
                if e and Path(e).exists():
                    try: subprocess.Popen([e])
                    except Exception as ex: print(ex)
            self._row(name, icon, launch)
 
    def _switch(self):
        if self._tab.get() == "bs":
            q = self._q.get().lower()
            self._render_bs([p for p in self.programs if q in p.stem.lower()])
        else:
            self._render_inst(self._inst_cache)
 
    def _on_search(self, *_):
        self._switch()
 
    def _power(self):
        m = tk.Menu(self, tearoff=False, bg=BG_PANEL, fg=TEXT_PRI,
                    activebackground=ACCENT, activeforeground=TEXT_PRI,
                    font=("Segoe UI",10), bd=0)
        m.add_command(label="🔒  Блокування",
                      command=lambda: ctypes.windll.user32.LockWorkStation())
        m.add_command(label="🔄  Перезавантаження",
                      command=lambda: os.system("shutdown /r /t 0"))
        m.add_separator()
        m.add_command(label="⏻  Вимкнення",
                      command=lambda: os.system("shutdown /s /t 0"))
        m.tk_popup(self.winfo_rootx()+10,
                   self.winfo_rooty()+self.winfo_height()-60)
 
 
# ── Top App Bar ────────────────────────────────────────────────────────────────
 
class TopAppBar(tk.Frame):
    """Semi-transparent centred bar pinned at the top."""
    PANEL_BG = "#1C1C1C"
 
    def __init__(self, master, programs, **kw):
        super().__init__(master, bg=BG_DARK, height=48, **kw)
        self.programs = list(programs)
        self._icons   = []
        self._build()
 
    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self._icons.clear()
 
        # centre pill
        pill = tk.Frame(self, bg="#1F1F1F", relief="flat")
        pill.place(relx=0.5, rely=0.5, anchor="center")
 
        tk.Label(pill, text="📌", bg="#1F1F1F", fg=TEXT_SEC,
                 font=("Segoe UI",10)).pack(side="left", padx=(8,2), pady=4)
 
        for prog in self.programs[:12]:
            icon = get_exe_icon_ctk(prog, 24)
            self._icons.append(icon)
            if icon:
                btn = ctk.CTkButton(
                    pill, image=icon, text="",
                    width=38, height=36,
                    fg_color="transparent", hover_color=BG_HOVER,
                    corner_radius=8,
                    command=lambda p=prog: self._launch(p))
            else:
                btn = ctk.CTkButton(
                    pill, text=prog.stem[:9],
                    width=80, height=36,
                    fg_color="transparent", hover_color=BG_HOVER,
                    text_color=TEXT_PRI, font=("Segoe UI",9),
                    corner_radius=8,
                    command=lambda p=prog: self._launch(p))
            btn.pack(side="left", padx=2, pady=4)
            add_tooltip(btn, prog.stem)
 
        ctk.CTkButton(pill, text="✏", width=28, height=28,
                      fg_color="transparent", hover_color=BG_HOVER,
                      text_color=TEXT_SEC, font=("Segoe UI",12),
                      corner_radius=8,
                      command=self._edit).pack(side="left", padx=(2,8))
 
    def _launch(self, prog: Path):
        try:
            subprocess.Popen([str(prog)], cwd=str(prog.parent))
        except Exception as ex:
            print(f"[TopBar] {ex}")
 
    def _edit(self):
        EditPinnedDialog(self, self.programs, self._on_done)
 
    def _on_done(self, new):
        self.programs = new
        self._build()
 
 
class EditPinnedDialog(ctk.CTkToplevel):
    def __init__(self, master, current, callback):
        super().__init__(master)
        self.callback = callback; self.current = current
        self.title("Закріплені програми")
        self.geometry("320x440")
        self.configure(fg_color=BG_PANEL)
        self.wm_attributes("-topmost", True)
        ctk.CTkLabel(self, text="Оберіть програми",
                     font=("Segoe UI",13,"bold"),
                     text_color=TEXT_PRI).pack(pady=(16,8))
        scr = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scr.pack(fill="both", expand=True, padx=12)
        self._vars = {}
        for p in sorted(PROG_DIR.glob("*.exe")) if PROG_DIR.exists() else []:
            v = tk.BooleanVar(value=(p in current))
            self._vars[p] = v
            ctk.CTkCheckBox(scr, text=p.stem, variable=v,
                            text_color=TEXT_PRI, font=("Segoe UI",11),
                            fg_color=ACCENT, hover_color=ACCENT_H
                            ).pack(anchor="w", pady=3)
        ctk.CTkButton(self, text="Зберегти",
                      fg_color=ACCENT, hover_color=ACCENT_H,
                      font=("Segoe UI",11,"bold"),
                      command=self._save
                      ).pack(fill="x", padx=12, pady=12)
 
    def _save(self):
        self.callback([p for p,v in self._vars.items() if v.get()])
        self.destroy()
 
 
# ── Desktop ────────────────────────────────────────────────────────────────────
 
class Desktop(tk.Canvas):
    IW = 78; IH = 74
 
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG_DARK, **kw)
        self._bg_photo = None
        self._bg_orig  = None
        self._refs     = []
        self._load_wp()
        self._draw_items()
        self.bind("<Configure>", lambda e: self._resize_bg())
        self.bind("<Button-3>",  self._rclick)
 
    def _load_wp(self):
        wp = get_wallpaper()
        if wp:
            try: self._bg_orig = Image.open(wp)
            except Exception: pass
        self._resize_bg()
 
    def _resize_bg(self):
        if not self._bg_orig: return
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        img = self._bg_orig.resize((w, h), Image.LANCZOS)
        self._bg_photo = ImageTk.PhotoImage(img)
        self.delete("_bg")
        self.create_image(0, 0, anchor="nw", image=self._bg_photo, tags="_bg")
        self.tag_lower("_bg")
 
    def _draw_items(self):
        self.delete("_item")
        self._refs.clear()
        items = get_desktop_items()
 
        screen_h = self.winfo_height() or 700
        max_rows = max(1, (screen_h - 16) // (self.IH + 4))
        col = row = 0
 
        for i, path in enumerate(items):
            x = 14 + col * (self.IW + 8)
            y = 14 + row * (self.IH + 4)
 
            icon = get_shell_icon_ctk(path, 32)
            if icon:
                # pull PIL image out of CTkImage for canvas
                pil = icon._light_image
                tk_img = ImageTk.PhotoImage(pil)
                self._refs.append(tk_img)
                self.create_image(x + self.IW//2, y + 20,
                                  image=tk_img, tags=f"i{i} _item")
            else:
                sym = "📁" if path.is_dir() else "📄"
                self.create_text(x + self.IW//2, y + 20,
                                 text=sym, font=("Segoe UI Emoji",18),
                                 fill=TEXT_PRI, tags=f"i{i} _item")
 
            name = (path.stem if path.suffix else path.name)[:13]
            self.create_text(x + self.IW//2, y + 52,
                             text=name, fill=TEXT_PRI,
                             font=("Segoe UI", 8), width=self.IW,
                             justify="center", tags=f"i{i} _item")
 
            self.tag_bind(f"i{i}", "<Double-Button-1>",
                          lambda e, p=path: self._open(p))
            self.tag_bind(f"i{i}", "<Enter>",
                          lambda e, n=i: self._hover(n, True))
            self.tag_bind(f"i{i}", "<Leave>",
                          lambda e, n=i: self._hover(n, False))
            self.tag_bind(f"i{i}", "<Button-3>",
                          lambda e, p=path: self._item_ctx(e, p))
 
            row += 1
            if row >= max_rows:
                row = 0; col += 1
 
    def _hover(self, idx, on):
        self.delete(f"_hov{idx}")
        if on:
            bb = self.bbox(f"i{idx}")
            if bb:
                x1,y1,x2,y2 = bb
                # solid colour, no alpha hex — fixes TclError
                self.create_rectangle(x1-3, y1-3, x2+3, y2+3,
                                      outline=ACCENT, fill=BG_HOVER,
                                      tags=f"_hov{idx}")
                self.tag_lower(f"_hov{idx}", f"i{idx}")
 
    def _open(self, path: Path):
        try: os.startfile(str(path))
        except Exception as ex: print(f"[Desktop] {ex}")
 
    def _rclick(self, event):
        CtxMenu(self.winfo_toplevel(), event.x_root, event.y_root, [
            ("🔄  Оновити",         self._reload),
            ("📂  Робочий стіл",    lambda: open_uri(str(Path.home()/"Desktop"))),
            None,
            ("🖼️  Змінити шпалери", self._change_wp),
            ("🖥️  Параметри екрану",lambda: open_uri("ms-settings:display")),
            None,
            ("💻  Про систему",     lambda: open_uri("ms-settings:about")),
        ])
 
    def _item_ctx(self, event, path: Path):
        CtxMenu(self.winfo_toplevel(), event.x_root, event.y_root, [
            ("▶️  Відкрити",    lambda: self._open(path)),
            ("📋  Властивості", lambda: ctypes.windll.shell32.ShellExecuteW(
                None,"properties",str(path),None,None,1)),
        ])
 
    def _change_wp(self):
        p = filedialog.askopenfilename(
            filetypes=[("Зображення","*.png *.jpg *.jpeg *.bmp")])
        if p:
            try:
                self._bg_orig = Image.open(p)
                self._resize_bg()
            except Exception: pass
 
    def _reload(self):
        self._load_wp(); self._draw_items()
 
 
# ── Right Vertical Taskbar ────────────────────────────────────────────────────
 
class RightBar(ctk.CTkFrame):
    def __init__(self, master, open_start, **kw):
        super().__init__(master, fg_color="#0E0E0E", width=224,
                         corner_radius=0, **kw)
        self.pack_propagate(False)
        self._open_start = open_start
        self._run_btns   = {}
        self._icon_refs  = []
        self._build()
        self._tick()
        self._poll()
 
    def _build(self):
        # ── Start button ──
        if ICON_PATH.exists():
            try:
                raw = Image.open(ICON_PATH).resize((28,28), Image.LANCZOS)
                self._menu_ctk = ctk.CTkImage(raw, size=(28,28))
                sb = ctk.CTkButton(self, image=self._menu_ctk, text="  Меню",
                                   compound="left", fg_color=ACCENT,
                                   hover_color=ACCENT_H,
                                   font=("Segoe UI",11,"bold"),
                                   height=42, corner_radius=8,
                                   command=self._open_start)
            except Exception:
                sb = ctk.CTkButton(self, text="⬛  Меню", fg_color=ACCENT,
                                   hover_color=ACCENT_H,
                                   font=("Segoe UI",11,"bold"),
                                   height=42, corner_radius=8,
                                   command=self._open_start)
        else:
            sb = ctk.CTkButton(self, text="⬛  Меню", fg_color=ACCENT,
                               hover_color=ACCENT_H,
                               font=("Segoe UI",11,"bold"),
                               height=42, corner_radius=8,
                               command=self._open_start)
        sb.pack(fill="x", padx=10, pady=(14,6))
 
        _sep = lambda: tk.Frame(self, height=1, bg=SEP).pack(fill="x",padx=10,pady=4)
 
        _sep()
 
        # Clock
        self._clk = ctk.CTkLabel(self, text="", font=("Segoe UI",18,"bold"),
                                   text_color=TEXT_PRI)
        self._clk.pack(pady=(6,0))
        self._dt = ctk.CTkLabel(self, text="", font=("Segoe UI",9),
                                 text_color=TEXT_SEC)
        self._dt.pack()
 
        _sep()
 
        ctk.CTkLabel(self, text="Запущені вікна",
                     font=("Segoe UI",10,"bold"),
                     text_color=TEXT_SEC).pack(anchor="w", padx=12)
 
        self._run_scr = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=ACCENT, height=240)
        self._run_scr.pack(fill="x", padx=6, pady=(4,0))
 
        _sep()
 
        ctk.CTkLabel(self, text="Швидкий доступ",
                     font=("Segoe UI",10,"bold"),
                     text_color=TEXT_SEC).pack(anchor="w", padx=12)
 
        quick = [
            ("⚙️  Параметри",   lambda: open_uri("ms-settings:")),
            ("🗂️  Провідник",   lambda: safe_popen(["explorer"])),
            ("🖥️  Диспетчер",   lambda: safe_popen(["taskmgr"])),
            ("🔊  Гучність",    lambda: safe_popen(["sndvol"])),
        ]
        for lbl, cmd in quick:
            ctk.CTkButton(self, text=lbl, anchor="w",
                          fg_color=BG_CARD, hover_color=BG_HOVER,
                          text_color=TEXT_PRI, font=("Segoe UI",10),
                          height=34, corner_radius=6,
                          command=cmd).pack(fill="x", padx=10, pady=2)
 
        _sep()
 
        self._cpu_l = ctk.CTkLabel(self, text="CPU: –",
                                    font=("Segoe UI",9), text_color=TEXT_SEC)
        self._cpu_l.pack(anchor="w", padx=14, pady=1)
        self._ram_l = ctk.CTkLabel(self, text="RAM: –",
                                    font=("Segoe UI",9), text_color=TEXT_SEC)
        self._ram_l.pack(anchor="w", padx=14)
        self._upd_sys()
 
    def _tick(self):
        n = datetime.datetime.now()
        self._clk.configure(text=n.strftime("%H:%M"))
        self._dt.configure(text=n.strftime("%A, %d.%m.%Y"))
        self.after(10000, self._tick)
 
    def _upd_sys(self):
        try:
            self._cpu_l.configure(text=f"CPU: {psutil.cpu_percent():.0f}%")
            self._ram_l.configure(text=f"RAM: {psutil.virtual_memory().percent:.0f}%")
        except Exception: pass
        self.after(3000, self._upd_sys)
 
    def _poll(self):
        wins = get_running_windows()
        cur  = {h for _,h in wins}
        for h in list(self._run_btns):
            if h not in cur:
                self._run_btns[h].destroy()
                del self._run_btns[h]
        for title, hwnd in wins:
            if hwnd not in self._run_btns:
                btn = ctk.CTkButton(
                    self._run_scr, text=title, anchor="w",
                    height=28, fg_color=BG_CARD, hover_color=ACCENT,
                    text_color=TEXT_PRI, font=("Segoe UI",9),
                    corner_radius=6,
                    command=lambda h=hwnd: self._focus(h))
                btn.pack(fill="x", pady=1, padx=2)
                self._run_btns[hwnd] = btn
        self.after(2500, self._poll)
 
    @staticmethod
    def _focus(hwnd):
        if not HAS_WIN32: return
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception: pass
 
 
# ── Shell Window ───────────────────────────────────────────────────────────────
 
class Shell(ctk.CTk):
    def __init__(self):
        super().__init__()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", False)
        self.title("BLACKSTAR Shell")
 
        set_custom_cursor(CURSOR_PATH)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.bind("<Control-Alt-q>", lambda e: self._quit())
 
        self.programs = sorted(PROG_DIR.glob("*.exe")) if PROG_DIR.exists() else []
 
        # Top bar
        self.top = TopAppBar(self, self.programs)
        self.top.pack(fill="x", side="top")
 
        # Middle
        mid = tk.Frame(self, bg=BG_DARK)
        mid.pack(fill="both", expand=True)
 
        self.desk = Desktop(mid)
        self.desk.pack(fill="both", expand=True, side="left")
 
        self.rbar = RightBar(mid, open_start=self._show_start)
        self.rbar.pack(fill="y", side="right")
 
        self._play_sound()
 
    def _show_start(self):
        sw = self.winfo_screenwidth()
        # appears just under the right bar's menu button
        x = sw - 224 - 400
        y = 48
        StartMenu(self, self.programs, max(0, x), y)
 
    def _play_sound(self):
        snd = BASE_DIR / "hellow.mp3"
        if not snd.exists(): return
        def _do():
            try:
                subprocess.Popen(
                    ["powershell","-WindowStyle","Hidden","-c",
                     f"Add-Type -AssemblyName presentationCore;"
                     f"$m=[System.Windows.Media.MediaPlayer]::new();"
                     f"$m.Open('{snd}');$m.Play();Start-Sleep 6"],
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            except Exception: pass
        threading.Thread(target=_do, daemon=True).start()
 
    def _quit(self):
        restore_cursors()
        self.destroy()
        sys.exit(0)
 
 
# ── Entry ──────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    Shell().mainloop()
