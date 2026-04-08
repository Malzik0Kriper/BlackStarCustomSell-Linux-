import customtkinter as ctk
import subprocess
import os
import sys
import threading
import glob
import random
import time
import datetime
from pathlib import Path
from PIL import Image, ImageTk
 
# ─── Paths (всі ресурси поруч з цим скриптом) ─────────────────────────────────
BASE_DIR   = Path(__file__).parent.resolve()
WALLPAPER_DIR = BASE_DIR / "Wallpaper"
CURSOR_FILE   = BASE_DIR / "BSC.cur"
HELLO_SOUND   = BASE_DIR / "hellow.mp3"
ICON_FILE     = BASE_DIR / "icon.png"
 
# ─── Pygame sound init ─────────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
 
# ─── CustomTkinter theme ───────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
 
# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════
 
def play_hello():
    """Програє hellow.mp3 в окремому потоці."""
    if not HELLO_SOUND.exists():
        return
    def _play():
        if HAS_PYGAME:
            pygame.mixer.music.load(str(HELLO_SOUND))
            pygame.mixer.music.play()
        else:
            # Fallback: aplay / mpg123
            for cmd in [["mpg123", "-q", str(HELLO_SOUND)],
                        ["aplay", str(HELLO_SOUND)],
                        ["ffplay", "-nodisp", "-autoexit", str(HELLO_SOUND)]]:
                try:
                    subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
                    break
                except FileNotFoundError:
                    continue
    threading.Thread(target=_play, daemon=True).start()
 
 
def set_cursor():
    """Встановлює кастомний курсор через xsetroot (якщо .cur конвертувати)."""
    if not CURSOR_FILE.exists():
        return
    # На Linux .cur → xcursor через xcursorgen або просто встановлюємо системний
    xcursor = BASE_DIR / "BSC_cursor"
    if not xcursor.exists():
        # Спробуємо конвертувати через convert (ImageMagick)
        try:
            subprocess.run(["convert", str(CURSOR_FILE), str(xcursor)],
                           stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pass
    # xsetroot -cursor_name або xcursorgen — якщо недоступно, пропускаємо
    try:
        subprocess.Popen(["xsetroot", "-cursor", str(CURSOR_FILE), str(CURSOR_FILE)],
                         stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
 
 
def set_wallpaper(path: str):
    """Встановлює шпалери через feh або nitrogen або hsetroot."""
    for cmd in [["feh", "--bg-scale", path],
                ["nitrogen", "--set-scaled", path],
                ["hsetroot", "-fill", path],
                ["xwallpaper", "--zoom", path]]:
        try:
            subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
 
 
def get_wallpapers():
    exts = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]
    files = []
    if WALLPAPER_DIR.exists():
        for ext in exts:
            files.extend(glob.glob(str(WALLPAPER_DIR / ext)))
            files.extend(glob.glob(str(WALLPAPER_DIR / ext.upper())))
    return files
 
 
def run_command(cmd: str):
    """Запускає команду в окремому потоці."""
    threading.Thread(target=lambda: subprocess.Popen(
        cmd, shell=True, stderr=subprocess.DEVNULL), daemon=True).start()
 
 
def get_sys_info():
    cpu = mem = "N/A"
    try:
        with open("/proc/loadavg") as f:
            cpu = f.read().split()[0] + " load"
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        total = free = 0
        for l in lines:
            if l.startswith("MemTotal"):
                total = int(l.split()[1])
            elif l.startswith("MemAvailable"):
                free = int(l.split()[1])
        used_pct = 100 - int(free / total * 100) if total else 0
        mem = f"{used_pct}% RAM"
    except Exception:
        pass
    return cpu, mem
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  APP LAUNCHER CONFIG
# ══════════════════════════════════════════════════════════════════════════════
 
APPS = [
    {"name": "Термінал",    "cmd": "xterm",          "icon": "💻"},
    {"name": "Браузер",     "cmd": "firefox",        "icon": "🌐"},
    {"name": "Файли",       "cmd": "pcmanfm",        "icon": "📁"},
    {"name": "Текст",       "cmd": "mousepad",       "icon": "📝"},
    {"name": "Музика",      "cmd": "audacious",      "icon": "🎵"},
    {"name": "Зображення",  "cmd": "eog",            "icon": "🖼"},
    {"name": "Параметри",   "cmd": "xfce4-settings-manager", "icon": "⚙️"},
    {"name": "Диспетчер",   "cmd": "xfce4-taskmanager",      "icon": "📊"},
    {"name": "Калькулятор", "cmd": "galculator",     "icon": "🔢"},
    {"name": "Мережа",      "cmd": "nm-applet",      "icon": "📡"},
    {"name": "Bluetooth",   "cmd": "blueman-manager","icon": "🔵"},
    {"name": "Вийти",       "cmd": "__logout__",     "icon": "🚪"},
]
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  MAIN SHELL WINDOW
# ══════════════════════════════════════════════════════════════════════════════
 
class BlackStarShell(ctk.CTk):
    ACCENT   = "#00d4ff"
    ACCENT2  = "#7c3aed"
    BG       = "#0a0a0f"
    PANEL    = "#11111a"
    CARD     = "#16162a"
    TEXT     = "#e8e8ff"
    SUBTEXT  = "#8888aa"
    SUCCESS  = "#22c55e"
    WARN     = "#f59e0b"
    DANGER   = "#ef4444"
 
    def __init__(self):
        super().__init__()
        self.title("BlackStar OS")
        self.configure(fg_color=self.BG)
 
        # Fullscreen / maximised
        self.attributes("-fullscreen", True)
        self.overrideredirect(False)
 
        # Icon
        if ICON_FILE.exists():
            try:
                img = Image.open(ICON_FILE).resize((32, 32))
                self._icon = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon)
            except Exception:
                pass
 
        # State
        self._wallpapers   = get_wallpapers()
        self._wall_index   = 0
        self._start_open   = False
        self._terminal_buf = []
 
        self._build_ui()
        self._start_clock()
        self._start_sysinfo()
        self._on_startup()
 
    # ── STARTUP ───────────────────────────────────────────────────────────────
    def _on_startup(self):
        play_hello()
        set_cursor()
        if self._wallpapers:
            set_wallpaper(self._wallpapers[0])
        self._update_wallpaper_preview()
        self._show_splash()
 
    def _show_splash(self):
        """Анімований splash-екран при старті."""
        self.splash = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
        self.splash.place(relx=0, rely=0, relwidth=1, relheight=1)
 
        logo = ctk.CTkLabel(self.splash, text="★ BlackStar OS",
                            font=ctk.CTkFont("monospace", 52, "bold"),
                            text_color=self.ACCENT)
        logo.place(relx=0.5, rely=0.4, anchor="center")
 
        sub = ctk.CTkLabel(self.splash, text="Tiny Core Linux Shell — завантаження…",
                           font=ctk.CTkFont("monospace", 16),
                           text_color=self.SUBTEXT)
        sub.place(relx=0.5, rely=0.52, anchor="center")
 
        bar = ctk.CTkProgressBar(self.splash, width=420, progress_color=self.ACCENT,
                                 fg_color="#1a1a2e")
        bar.place(relx=0.5, rely=0.62, anchor="center")
        bar.set(0)
 
        def _anim(v=0.0):
            if v <= 1.0:
                bar.set(v)
                self.after(20, lambda: _anim(v + 0.02))
            else:
                self.splash.destroy()
 
        self.after(400, lambda: _anim())
 
    # ── UI BUILD ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Taskbar (top) ──────────────────────────────────────────────────
        self.taskbar = ctk.CTkFrame(self, height=44, fg_color=self.PANEL,
                                    corner_radius=0)
        self.taskbar.pack(fill="x", side="top")
        self.taskbar.pack_propagate(False)
 
        # Logo / Start button
        self.btn_start = ctk.CTkButton(
            self.taskbar, text="  ★ BlackStar", width=130,
            font=ctk.CTkFont("monospace", 14, "bold"),
            fg_color=self.ACCENT2, hover_color="#5b21b6",
            corner_radius=0, command=self._toggle_start_menu)
        self.btn_start.pack(side="left", padx=(0, 8), fill="y")
 
        # Quick launch icons
        quick = [("💻", "xterm"), ("🌐", "firefox"), ("📁", "pcmanfm"),
                 ("📝", "mousepad"), ("🎵", "audacious")]
        for ico, cmd in quick:
            b = ctk.CTkButton(self.taskbar, text=ico, width=38,
                              font=ctk.CTkFont(size=16), fg_color="transparent",
                              hover_color="#222233", corner_radius=6,
                              command=lambda c=cmd: run_command(c))
            b.pack(side="left", padx=2, pady=4)
 
        # Clock + date (right)
        self.lbl_clock = ctk.CTkLabel(self.taskbar, text="",
                                      font=ctk.CTkFont("monospace", 15, "bold"),
                                      text_color=self.ACCENT)
        self.lbl_clock.pack(side="right", padx=14)
        self.lbl_date = ctk.CTkLabel(self.taskbar, text="",
                                     font=ctk.CTkFont("monospace", 11),
                                     text_color=self.SUBTEXT)
        self.lbl_date.pack(side="right", padx=4)
 
        # Sys info (right)
        self.lbl_sys = ctk.CTkLabel(self.taskbar, text="CPU — | RAM —",
                                    font=ctk.CTkFont("monospace", 11),
                                    text_color=self.SUBTEXT)
        self.lbl_sys.pack(side="right", padx=14)
 
        # ── Desktop area ───────────────────────────────────────────────────
        self.desktop = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
        self.desktop.pack(fill="both", expand=True)
 
        # Desktop icons grid
        self._build_desktop_icons()
 
        # ── Start Menu (hidden initially) ──────────────────────────────────
        self._build_start_menu()
 
        # ── Right panel: widgets ───────────────────────────────────────────
        self._build_right_panel()
 
        # Close start menu on desktop click
        self.desktop.bind("<Button-1>", lambda e: self._close_start_menu())
 
    # ── DESKTOP ICONS ────────────────────────────────────────────────────────
    def _build_desktop_icons(self):
        self.icon_frame = ctk.CTkFrame(self.desktop, fg_color="transparent")
        self.icon_frame.place(x=16, y=16)
 
        icons = [
            ("💻", "Термінал",    "xterm"),
            ("🌐", "Браузер",     "firefox"),
            ("📁", "Файли",       "pcmanfm"),
            ("📝", "Текст",       "mousepad"),
            ("🎵", "Медіа",       "audacious"),
            ("⚙️", "Параметри",  "xfce4-settings-manager"),
            ("📊", "Диспетчер",   "xfce4-taskmanager"),
            ("🔢", "Калькулятор", "galculator"),
        ]
        cols = 1
        for i, (ico, name, cmd) in enumerate(icons):
            r, c = divmod(i, cols)
            f = ctk.CTkFrame(self.icon_frame, fg_color="transparent",
                             corner_radius=10, cursor="hand2")
            f.grid(row=r, column=c, padx=6, pady=4, sticky="w")
 
            lbl_i = ctk.CTkLabel(f, text=ico, font=ctk.CTkFont(size=26))
            lbl_i.pack()
            lbl_n = ctk.CTkLabel(f, text=name,
                                 font=ctk.CTkFont("monospace", 9),
                                 text_color=self.TEXT)
            lbl_n.pack()
 
            for w in (f, lbl_i, lbl_n):
                w.bind("<Double-Button-1>", lambda e, c=cmd: run_command(c))
                w.bind("<Enter>", lambda e, fr=f: fr.configure(fg_color="#1e1e3a"))
                w.bind("<Leave>", lambda e, fr=f: fr.configure(fg_color="transparent"))
 
    # ── START MENU ───────────────────────────────────────────────────────────
    def _build_start_menu(self):
        self.start_menu = ctk.CTkFrame(self, width=300, fg_color=self.PANEL,
                                       corner_radius=12,
                                       border_width=1, border_color=self.ACCENT2)
        # Search
        self.sm_search = ctk.CTkEntry(self.start_menu,
                                      placeholder_text="🔍 Пошук...",
                                      font=ctk.CTkFont("monospace", 13),
                                      fg_color="#1a1a2e", border_color=self.ACCENT2)
        self.sm_search.pack(padx=12, pady=(12, 6), fill="x")
        self.sm_search.bind("<KeyRelease>", self._filter_apps)
 
        self.sm_scroll = ctk.CTkScrollableFrame(self.start_menu, fg_color="transparent",
                                                height=320)
        self.sm_scroll.pack(fill="both", expand=True, padx=6, pady=4)
 
        self._all_app_btns = []
        for app in APPS:
            btn = ctk.CTkButton(
                self.sm_scroll,
                text=f"{app['icon']}  {app['name']}",
                anchor="w",
                font=ctk.CTkFont("monospace", 13),
                fg_color="transparent",
                hover_color="#1e1e3a",
                text_color=self.TEXT,
                command=lambda a=app: self._launch_app(a))
            btn.pack(fill="x", pady=2, padx=4)
            self._all_app_btns.append((btn, app["name"]))
 
        # Footer
        foot = ctk.CTkFrame(self.start_menu, fg_color="#0d0d1a", corner_radius=0)
        foot.pack(fill="x", side="bottom")
        ctk.CTkButton(foot, text="🔒 Блокування", fg_color="transparent",
                      hover_color="#1e1e3a", font=ctk.CTkFont("monospace", 11),
                      command=lambda: run_command("xlock")).pack(side="left", padx=8, pady=6)
        ctk.CTkButton(foot, text="⏻ Вимкнути", fg_color="transparent",
                      hover_color="#3a0a0a", text_color=self.DANGER,
                      font=ctk.CTkFont("monospace", 11),
                      command=self._shutdown_dialog).pack(side="right", padx=8, pady=6)
 
    def _filter_apps(self, _=None):
        q = self.sm_search.get().lower()
        for btn, name in self._all_app_btns:
            if q in name.lower():
                btn.pack(fill="x", pady=2, padx=4)
            else:
                btn.pack_forget()
 
    def _toggle_start_menu(self):
        if self._start_open:
            self._close_start_menu()
        else:
            self._open_start_menu()
 
    def _open_start_menu(self):
        self.start_menu.place(x=0, y=44, relheight=0, height=420)
        self._start_open = True
 
    def _close_start_menu(self):
        self.start_menu.place_forget()
        self._start_open = False
 
    def _launch_app(self, app):
        self._close_start_menu()
        if app["cmd"] == "__logout__":
            self._shutdown_dialog()
        else:
            run_command(app["cmd"])
 
    # ── RIGHT PANEL (clock widget, wallpaper, terminal) ───────────────────────
    def _build_right_panel(self):
        self.rpanel = ctk.CTkFrame(self.desktop, width=270, fg_color=self.PANEL,
                                   corner_radius=0)
        self.rpanel.pack(side="right", fill="y")
        self.rpanel.pack_propagate(False)
 
        # ── Big clock widget ───────────────────────────────────────────────
        clock_card = ctk.CTkFrame(self.rpanel, fg_color=self.CARD, corner_radius=14)
        clock_card.pack(fill="x", padx=10, pady=(14, 6))
 
        self.big_clock = ctk.CTkLabel(clock_card, text="00:00",
                                      font=ctk.CTkFont("monospace", 42, "bold"),
                                      text_color=self.ACCENT)
        self.big_clock.pack(pady=(10, 0))
        self.big_date_lbl = ctk.CTkLabel(clock_card, text="",
                                         font=ctk.CTkFont("monospace", 11),
                                         text_color=self.SUBTEXT)
        self.big_date_lbl.pack(pady=(0, 10))
 
        # ── Wallpaper control ──────────────────────────────────────────────
        wall_card = ctk.CTkFrame(self.rpanel, fg_color=self.CARD, corner_radius=14)
        wall_card.pack(fill="x", padx=10, pady=6)
 
        ctk.CTkLabel(wall_card, text="🖼 Шпалери",
                     font=ctk.CTkFont("monospace", 13, "bold"),
                     text_color=self.TEXT).pack(anchor="w", padx=10, pady=(8, 4))
 
        self.wall_preview = ctk.CTkLabel(wall_card, text="",
                                         width=240, height=130)
        self.wall_preview.pack(padx=10, pady=4)
 
        btn_row = ctk.CTkFrame(wall_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(btn_row, text="◀", width=50,
                      fg_color=self.ACCENT2, hover_color="#5b21b6",
                      command=self._prev_wall).pack(side="left")
        ctk.CTkButton(btn_row, text="Встановити", width=130,
                      fg_color="#1a1a2e", hover_color=self.ACCENT2,
                      command=self._apply_wall).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="▶", width=50,
                      fg_color=self.ACCENT2, hover_color="#5b21b6",
                      command=self._next_wall).pack(side="right")
 
        self.wall_name_lbl = ctk.CTkLabel(wall_card, text="Немає шпалер",
                                          font=ctk.CTkFont("monospace", 10),
                                          text_color=self.SUBTEXT)
        self.wall_name_lbl.pack(pady=(0, 6))
 
        # ── Sound widget ───────────────────────────────────────────────────
        snd_card = ctk.CTkFrame(self.rpanel, fg_color=self.CARD, corner_radius=14)
        snd_card.pack(fill="x", padx=10, pady=6)
 
        ctk.CTkLabel(snd_card, text="🔊 Звук",
                     font=ctk.CTkFont("monospace", 13, "bold"),
                     text_color=self.TEXT).pack(anchor="w", padx=10, pady=(8, 4))
 
        self.vol_slider = ctk.CTkSlider(snd_card, from_=0, to=100,
                                        progress_color=self.ACCENT,
                                        button_color=self.ACCENT2,
                                        command=self._set_volume)
        self.vol_slider.set(80)
        self.vol_slider.pack(fill="x", padx=10, pady=(0, 4))
 
        btn_snd = ctk.CTkFrame(snd_card, fg_color="transparent")
        btn_snd.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(btn_snd, text="▶ Привітання", width=140,
                      fg_color="#1a1a2e", hover_color=self.ACCENT2,
                      command=play_hello).pack(side="left")
        ctk.CTkButton(btn_snd, text="🔇", width=50,
                      fg_color="transparent", hover_color="#1e1e3a",
                      command=lambda: self._set_volume(0)).pack(side="right")
 
        # ── Mini terminal ──────────────────────────────────────────────────
        term_card = ctk.CTkFrame(self.rpanel, fg_color=self.CARD, corner_radius=14)
        term_card.pack(fill="both", expand=True, padx=10, pady=6)
 
        ctk.CTkLabel(term_card, text="💻 Термінал",
                     font=ctk.CTkFont("monospace", 13, "bold"),
                     text_color=self.TEXT).pack(anchor="w", padx=10, pady=(8, 2))
 
        self.term_out = ctk.CTkTextbox(term_card, height=100,
                                       font=ctk.CTkFont("monospace", 11),
                                       fg_color="#06060e", text_color="#00ff88",
                                       corner_radius=8)
        self.term_out.pack(fill="both", expand=True, padx=8, pady=4)
        self.term_out.configure(state="disabled")
 
        inp_row = ctk.CTkFrame(term_card, fg_color="transparent")
        inp_row.pack(fill="x", padx=8, pady=(0, 8))
 
        self.term_prompt = ctk.CTkLabel(inp_row, text="$ ",
                                        font=ctk.CTkFont("monospace", 12),
                                        text_color=self.ACCENT2)
        self.term_prompt.pack(side="left")
 
        self.term_input = ctk.CTkEntry(inp_row, font=ctk.CTkFont("monospace", 12),
                                       fg_color="#06060e", border_color=self.ACCENT2,
                                       text_color="#00ff88")
        self.term_input.pack(side="left", fill="x", expand=True)
        self.term_input.bind("<Return>", self._run_term_cmd)
 
        self._term_write(f"BlackStar OS v1.0 — Tiny Core Linux\n")
        self._term_write(f"Введіть команду та натисніть Enter\n")
 
    # ── WALLPAPER ─────────────────────────────────────────────────────────────
    def _update_wallpaper_preview(self):
        if not self._wallpapers:
            self.wall_name_lbl.configure(text="Немає шпалер у папці Wallpaper")
            return
        path = self._wallpapers[self._wall_index]
        self.wall_name_lbl.configure(text=Path(path).name)
        try:
            img = Image.open(path).resize((240, 130), Image.LANCZOS)
            ctk_img = ctk.CTkImage(img, size=(240, 130))
            self.wall_preview.configure(image=ctk_img, text="")
            self.wall_preview._image = ctk_img  # keep ref
        except Exception:
            self.wall_preview.configure(text="[Помилка зображення]")
 
    def _next_wall(self):
        if self._wallpapers:
            self._wall_index = (self._wall_index + 1) % len(self._wallpapers)
            self._update_wallpaper_preview()
 
    def _prev_wall(self):
        if self._wallpapers:
            self._wall_index = (self._wall_index - 1) % len(self._wallpapers)
            self._update_wallpaper_preview()
 
    def _apply_wall(self):
        if self._wallpapers:
            set_wallpaper(self._wallpapers[self._wall_index])
            self._term_write(f"Шпалери встановлено: {Path(self._wallpapers[self._wall_index]).name}\n")
 
    # ── SOUND ─────────────────────────────────────────────────────────────────
    def _set_volume(self, val):
        v = int(float(val))
        if HAS_PYGAME:
            pygame.mixer.music.set_volume(v / 100)
        # amixer fallback
        try:
            subprocess.Popen(["amixer", "-q", "set", "Master", f"{v}%"],
                             stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
 
    # ── MINI TERMINAL ─────────────────────────────────────────────────────────
    def _term_write(self, text: str):
        self.term_out.configure(state="normal")
        self.term_out.insert("end", text)
        self.term_out.see("end")
        self.term_out.configure(state="disabled")
 
    def _run_term_cmd(self, _=None):
        cmd = self.term_input.get().strip()
        if not cmd:
            return
        self.term_input.delete(0, "end")
        self._term_write(f"$ {cmd}\n")
 
        def _exec():
            try:
                out = subprocess.check_output(
                    cmd, shell=True, stderr=subprocess.STDOUT,
                    timeout=8, text=True)
                self.after(0, lambda: self._term_write(out or "(OK)\n"))
            except subprocess.CalledProcessError as e:
                self.after(0, lambda: self._term_write(e.output or "(помилка)\n"))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._term_write("(таймаут)\n"))
            except Exception as ex:
                self.after(0, lambda: self._term_write(f"Помилка: {ex}\n"))
 
        threading.Thread(target=_exec, daemon=True).start()
 
    # ── CLOCK ─────────────────────────────────────────────────────────────────
    def _start_clock(self):
        def _tick():
            now = datetime.datetime.now()
            t = now.strftime("%H:%M:%S")
            d = now.strftime("%A, %d %B %Y")
            self.lbl_clock.configure(text=t)
            self.lbl_date.configure(text=d)
            self.big_clock.configure(text=now.strftime("%H:%M"))
            self.big_date_lbl.configure(text=d)
            self.after(1000, _tick)
        _tick()
 
    # ── SYS INFO ──────────────────────────────────────────────────────────────
    def _start_sysinfo(self):
        def _update():
            cpu, mem = get_sys_info()
            self.lbl_sys.configure(text=f"CPU {cpu} | {mem}")
            self.after(5000, _update)
        self.after(2000, _update)
 
    # ── SHUTDOWN DIALOG ───────────────────────────────────────────────────────
    def _shutdown_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Вихід")
        dlg.geometry("340x220")
        dlg.configure(fg_color=self.PANEL)
        dlg.grab_set()
        dlg.resizable(False, False)
 
        ctk.CTkLabel(dlg, text="Що ви хочете зробити?",
                     font=ctk.CTkFont("monospace", 15, "bold"),
                     text_color=self.TEXT).pack(pady=(24, 16))
 
        actions = [
            ("⏻  Вимкнути",    "poweroff"),
            ("🔄  Перезавантажити", "reboot"),
            ("🔒  Заблокувати", "xlock"),
            ("❌  Скасувати",   None),
        ]
        for label, cmd in actions:
            color = self.DANGER if "Вимкнути" in label else \
                    self.WARN   if "Перезав"  in label else \
                    self.ACCENT2 if "Заблок"  in label else "#333355"
            def _cb(c=cmd, d=dlg):
                d.destroy()
                if c:
                    run_command(c)
            ctk.CTkButton(dlg, text=label, fg_color=color,
                          hover_color="#555566",
                          font=ctk.CTkFont("monospace", 13),
                          command=_cb).pack(fill="x", padx=30, pady=3)
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Install deps if missing
    try:
        import customtkinter
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "customtkinter", "pillow", "pygame", "--quiet"])
        import customtkinter as ctk
 
    app = BlackStarShell()
    app.mainloop()
