import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import shutil
import platform
import json
from pathlib import Path
from datetime import datetime

# =========================================================================
# CONFIGURATION
# =========================================================================
DEFAULT_HDK_PATH = r""
DEFAULT_RESHARC_PATH = r""
DEFAULT_UNLUAC_PATH = r""

# Settings file — lives next to the script
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hdk_settings.json")

# =========================================================================
# PLATFORM DETECTION
# =========================================================================
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

BIN_EXT = ".exe" if IS_WINDOWS else ""

if IS_MAC:
    FONT_MAIN = "SF Pro Text"
    FONT_HEADER = "SF Pro Display"
    FONT_MONO = "Menlo"
elif IS_WINDOWS:
    FONT_MAIN = "Segoe UI"
    FONT_HEADER = "Segoe UI"
    FONT_MONO = "Consolas"
else:
    FONT_MAIN = "DejaVu Sans"
    FONT_HEADER = "DejaVu Sans"
    FONT_MONO = "DejaVu Sans Mono"


class HDKCommander(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PlayStation Home HDK Commander")
        self.geometry("1050x900")
        self.configure(bg="#1e1e1e")

        # Variables
        self.hdk_path_var = tk.StringVar(value="Searching...")
        self.resharc_path_var = tk.StringVar(value="Searching...")
        self.unluac_path_var = tk.StringVar(value="Searching...")
        self.project_path = tk.StringVar(value="No Folder Selected")

        # Load saved settings (returns dict, may be empty)
        self.settings = self._load_settings()

        # Resolve binary paths: saved settings → manual default → auto-detect
        found_hdk = self._resolve_binary_path("hdk_path", "hdk", DEFAULT_HDK_PATH, [
            f"hdk{BIN_EXT}",
            os.path.join("hdk-cli", "target", "release", f"hdk{BIN_EXT}"),
        ])
        found_resharc = self._resolve_binary_path("resharc_path", "hdk-resharc", DEFAULT_RESHARC_PATH, [
            f"hdk-resharc{BIN_EXT}",
            os.path.join("hdk-resharc", "target", "release", f"hdk-resharc{BIN_EXT}"),
        ])

        # Resolve unluac jar: saved settings → manual default → auto-detect nearby
        found_unluac = self._resolve_jar_path("unluac_path", DEFAULT_UNLUAC_PATH, [
            "unluac-verbose.jar",
            "unluac.jar",
            os.path.join("tools", "unluac-verbose.jar"),
            os.path.join("tools", "unluac.jar"),
        ])

        self.hdk_path_var.set(found_hdk if found_hdk else "NOT FOUND - Click Change...")
        self.resharc_path_var.set(found_resharc if found_resharc else "NOT FOUND - Click Change...")
        self.unluac_path_var.set(found_unluac if found_unluac else "NOT FOUND - Click Change...")

        # Restore project path from settings
        saved_project = self.settings.get("project_path", "")
        if saved_project and os.path.isdir(saved_project):
            self.project_path.set(saved_project)

        # LUAC decompiler state
        self.luac_is_running = False
        self.luac_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total': 0}

        self._setup_styles()
        self._setup_ui()

        # Restore pack input from settings
        saved_pack_input = self.settings.get("pack_input_path", "")
        if saved_pack_input and os.path.isdir(saved_pack_input):
            self.pack_input_var.set(saved_pack_input)

        # Restore LUAC directories from settings
        saved_luac_project = self.settings.get("luac_project_dir", "")
        if saved_luac_project and os.path.isdir(saved_luac_project):
            self.luac_project_var.set(saved_luac_project)
        saved_luac_output = self.settings.get("luac_output_dir", "")
        if saved_luac_output and os.path.isdir(saved_luac_output):
            self.luac_output_var.set(saved_luac_output)
        saved_luac_keywords = self.settings.get("luac_search_keywords", "")
        if saved_luac_keywords:
            self.luac_keywords_var.set(saved_luac_keywords)
        saved_luac_workers = self.settings.get("luac_workers", 4)
        if saved_luac_workers:
            self.luac_workers_var.set(int(saved_luac_workers))

        # Save settings on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Alerts for missing binaries (only on true first run)
        missing = []
        if not found_hdk:
            missing.append("hdk (hdk-cli)")
        if not found_resharc:
            missing.append("hdk-resharc")
        if not found_unluac:
            missing.append("unluac-verbose.jar (LUAC Decompiler)")

        if missing:
            messagebox.showinfo("Setup Required",
                f"Could not auto-detect:\n  • " + "\n  • ".join(missing) + "\n\n"
                "Use the 'Change...' buttons at the top to locate them.\n"
                "You can still use the features for whichever tool IS found.")

    # =========================================================================
    # SETTINGS PERSISTENCE
    # =========================================================================
    def _load_settings(self):
        """Load saved settings from JSON file."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def _save_settings(self):
        """Save current paths to JSON file."""
        hdk = self.hdk_path_var.get()
        resharc = self.resharc_path_var.get()
        unluac = self.unluac_path_var.get()
        project = self.project_path.get()
        pack_input = self.pack_input_var.get() if hasattr(self, 'pack_input_var') else ""

        data = {
            "hdk_path": hdk if "NOT FOUND" not in hdk else "",
            "resharc_path": resharc if "NOT FOUND" not in resharc else "",
            "unluac_path": unluac if "NOT FOUND" not in unluac else "",
            "project_path": project if project != "No Folder Selected" else "",
            "pack_input_path": pack_input if pack_input != "No folder selected" else "",
            # LUAC decompiler settings
            "luac_project_dir": self.luac_project_var.get() if hasattr(self, 'luac_project_var') and self.luac_project_var.get() != "No folder selected" else "",
            "luac_output_dir": self.luac_output_var.get() if hasattr(self, 'luac_output_var') and self.luac_output_var.get() != "No folder selected" else "",
            "luac_search_keywords": self.luac_keywords_var.get() if hasattr(self, 'luac_keywords_var') else "save, load, persist",
            "luac_workers": self.luac_workers_var.get() if hasattr(self, 'luac_workers_var') else 4,
        }

        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _on_close(self):
        """Save settings and exit."""
        self._save_settings()
        self.destroy()

    def _resolve_binary_path(self, settings_key, name, manual_default, candidates):
        """Try: saved setting → manual default → auto-detect."""
        saved = self.settings.get(settings_key, "")
        if saved and os.path.exists(saved):
            return saved

        if manual_default and os.path.exists(manual_default):
            return manual_default

        if IS_MAC or IS_LINUX:
            home = os.path.expanduser("~")
            candidates.append(os.path.join(home, ".cargo", "bin", name))

        return self._find_binary(name, candidates)

    def _resolve_jar_path(self, settings_key, manual_default, candidates):
        """Try: saved setting → manual default → search nearby."""
        saved = self.settings.get(settings_key, "")
        if saved and os.path.exists(saved):
            return saved

        if manual_default and os.path.exists(manual_default):
            return manual_default

        for candidate in candidates:
            if os.path.isabs(candidate) and os.path.exists(candidate):
                return candidate
            full = os.path.join(os.getcwd(), candidate)
            if os.path.exists(full):
                return full
            # Also check next to the script itself
            script_dir = os.path.dirname(os.path.abspath(__file__))
            beside = os.path.join(script_dir, candidate)
            if os.path.exists(beside):
                return beside

        return None

    def _find_binary(self, name, search_names):
        """Search CWD-relative paths, then system PATH."""
        for candidate in search_names:
            if os.path.isabs(candidate) and os.path.exists(candidate):
                return candidate
            full = os.path.join(os.getcwd(), candidate)
            if os.path.exists(full):
                return full

        found = shutil.which(name)
        if found:
            return found
        return None

    # =========================================================================
    # STYLES
    # =========================================================================
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        bg_dark = "#1e1e1e"
        bg_medium = "#2b2b2b"
        accent_color = "#007acc"
        text_color = "#ffffff"

        style.configure("TFrame", background=bg_dark)
        style.configure("TLabel", background=bg_dark, foreground=text_color, font=(FONT_MAIN, 10))
        style.configure("Header.TLabel", font=(FONT_HEADER, 12, "bold"), foreground="#4db8ff")
        style.configure("SubHeader.TLabel", font=(FONT_MAIN, 10, "bold"), foreground="#aaaaaa")

        style.configure("TButton", background=bg_medium, foreground=text_color, borderwidth=1, font=(FONT_MAIN, 9))
        style.map("TButton", background=[('active', accent_color)])

        style.configure("Accent.TButton", background="#005a9e", foreground=text_color, borderwidth=1, font=(FONT_MAIN, 10, "bold"))
        style.map("Accent.TButton", background=[('active', '#007acc')])

        style.configure("Danger.TButton", background="#8b0000", foreground=text_color, borderwidth=1, font=(FONT_MAIN, 9))
        style.map("Danger.TButton", background=[('active', '#cc0000')])

        style.configure("TLabelframe", background=bg_dark, foreground=text_color)
        style.configure("TLabelframe.Label", background=bg_dark, foreground="#4db8ff")

        style.configure("TNotebook", background=bg_medium, borderwidth=0)
        style.configure("TNotebook.Tab", background=bg_medium, foreground=text_color, padding=[10, 5])
        style.map("TNotebook.Tab", background=[('selected', accent_color)])

        style.configure("TCheckbutton", background=bg_dark, foreground=text_color)
        style.configure("TRadiobutton", background=bg_dark, foreground=text_color)

        style.configure("TScale", background=bg_dark)

        # Progress bar style
        style.configure("Custom.Horizontal.TProgressbar", troughcolor=bg_medium, background="#007acc")

    # =========================================================================
    # SCROLLABLE TAB HELPER
    # =========================================================================
    def _make_scrollable_tab(self, parent, padding=20):
        """Creates a consistent scrollable frame inside a tab. Returns the inner frame to pack widgets into."""
        canvas = tk.Canvas(parent, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)

        inner_frame = ttk.Frame(canvas, padding=padding)

        inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            if canvas.winfo_exists():
                if IS_MAC:
                    canvas.yview_scroll(int(-1 * event.delta), "units")
                else:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        return inner_frame

    # =========================================================================
    # UI SETUP
    # =========================================================================
    def _setup_ui(self):
        # === HEADER / CONFIG AREA ===
        config_frame = ttk.Frame(self, padding=15)
        config_frame.pack(fill="x")

        # Row 1: HDK Binary
        r1 = ttk.Frame(config_frame)
        r1.pack(fill="x", pady=3)
        ttk.Label(r1, text="HDK Binary:", style="SubHeader.TLabel", width=18).pack(side="left")
        ttk.Label(r1, textvariable=self.hdk_path_var, foreground="#00ff00", font=(FONT_MONO, 9)).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(r1, text="Change...", command=lambda: self._browse_exe("hdk", self.hdk_path_var), width=10).pack(side="right")

        # Row 2: Re-SHARC Binary
        r2 = ttk.Frame(config_frame)
        r2.pack(fill="x", pady=3)
        ttk.Label(r2, text="Re-SHARC Binary:", style="SubHeader.TLabel", width=18).pack(side="left")
        ttk.Label(r2, textvariable=self.resharc_path_var, foreground="#00ff00", font=(FONT_MONO, 9)).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(r2, text="Change...", command=lambda: self._browse_exe("hdk-resharc", self.resharc_path_var), width=10).pack(side="right")

        # Row 3: Unluac JAR
        r3 = ttk.Frame(config_frame)
        r3.pack(fill="x", pady=3)
        ttk.Label(r3, text="Unluac JAR:", style="SubHeader.TLabel", width=18).pack(side="left")
        ttk.Label(r3, textvariable=self.unluac_path_var, foreground="#00ff00", font=(FONT_MONO, 9)).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(r3, text="Change...", command=self._browse_jar, width=10).pack(side="right")

        # Row 4: Project Location
        r4 = ttk.Frame(config_frame)
        r4.pack(fill="x", pady=3)
        ttk.Label(r4, text="Active Project:", style="Header.TLabel", width=18).pack(side="left")
        ttk.Label(r4, textvariable=self.project_path, foreground="#ffd700", font=(FONT_MONO, 10)).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(r4, text="Browse Folder...", command=self.select_project, width=15).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # === TABS ===
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=10, pady=5)

        tab_extract = ttk.Frame(notebook)
        notebook.add(tab_extract, text="  EXTRACT  ")
        self._build_extract_tab(tab_extract)

        tab_create = ttk.Frame(notebook)
        notebook.add(tab_create, text="  CREATE & PACK  ")
        self._build_create_tab(tab_create)

        tab_resharc = ttk.Frame(notebook)
        notebook.add(tab_resharc, text="  RE-SHARC  ")
        self._build_resharc_tab(tab_resharc)

        tab_luac = ttk.Frame(notebook)
        notebook.add(tab_luac, text="  LUAC DECOMPILER  ")
        self._build_luac_tab(tab_luac)

        tab_tools = ttk.Frame(notebook)
        notebook.add(tab_tools, text="  ADVANCED TOOLS  ")
        self._build_tools_tab(tab_tools)

        tab_help = ttk.Frame(notebook)
        notebook.add(tab_help, text="  ENCYCLOPEDIA  ")
        self._build_help_tab(tab_help)

        # === CONSOLE ===
        console_frame = ttk.LabelFrame(self, text=" System Output Log ", padding=5)
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.console = scrolledtext.ScrolledText(console_frame, height=10, bg="#101010", fg="#00ff00",
                                                  insertbackground="white", font=(FONT_MONO, 9))
        self.console.pack(fill="both", expand=True)

        self.console.tag_configure("error", foreground="#ff4444")
        self.console.tag_configure("success", foreground="#44ff44")
        self.console.tag_configure("info", foreground="#4db8ff")
        self.console.tag_configure("warning", foreground="#ff8800")

        self.log(f"Platform: {platform.system()} {platform.machine()} ({sys.platform})", "info")
        if os.path.exists(SETTINGS_FILE):
            self.log("Settings loaded from previous session.", "info")

    # =========================================================================
    # TAB 1: EXTRACT
    # =========================================================================
    def _build_extract_tab(self, parent):
        frame = self._make_scrollable_tab(parent)

        ttk.Label(frame, text="Unpack Game Archives", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(frame, text="Select a file to automatically detect its type and extract it.\nSupports: .sdat, .bar, .sharc, .pkg").pack(anchor="w", pady=(0, 20))

        btn = ttk.Button(frame, text="SELECT FILE TO EXTRACT", command=self.extract_file_dialog, style="Accent.TButton")
        btn.pack(fill="x", pady=5, ipady=15)

    def extract_file_dialog(self):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return

        filepath = filedialog.askopenfilename(filetypes=[
            ("All Home Files", "*.sdat *.bar *.sharc *.pkg"),
            ("SDAT Files", "*.sdat"),
            ("BAR Archives", "*.bar"),
            ("SHARC Archives", "*.sharc"),
            ("PKG Packages", "*.pkg"),
        ])
        if not filepath: return

        ext = os.path.splitext(filepath)[1].lower()
        output_path = filepath + "_extracted"

        type_map = {".sdat": "sdat", ".bar": "bar", ".sharc": "sharc", ".pkg": "pkg"}
        archive_type = type_map.get(ext)
        if not archive_type:
            self.log("Error: Unknown file type.", "error")
            return

        cmd = [archive_type, "x", "-i", filepath, "-o", output_path]
        self.run_hdk_command(cmd)

    # =========================================================================
    # TAB 2: CREATE & PACK
    # =========================================================================
    def _build_create_tab(self, parent):
        frame = self._make_scrollable_tab(parent)

        ttk.Label(frame, text="Pack Folders into Archives", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        # --- Input Folder Selection ---
        ttk.Label(frame, text="1. Select the folder you want to pack:", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        input_row = ttk.Frame(frame)
        input_row.pack(fill="x", pady=(0, 10))

        self.pack_input_var = tk.StringVar(value="No folder selected")
        ttk.Label(input_row, textvariable=self.pack_input_var, foreground="#ffd700", font=(FONT_MONO, 9)).pack(side="left", fill="x", expand=True)
        ttk.Button(input_row, text="Browse...", command=self._browse_pack_input, width=10).pack(side="right")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

        # --- Options ---
        ttk.Label(frame, text="2. Options:", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))

        self.auto_compress = tk.BooleanVar(value=False)
        chk_comp = ttk.Checkbutton(frame, text="Auto-Optimize: Compress assets before packing (slower build)", variable=self.auto_compress)
        chk_comp.pack(anchor="w", pady=(0, 5))

        self.compress_algo = tk.StringVar(value="lzma")
        algo_frame = ttk.Frame(frame)
        algo_frame.pack(anchor="w", pady=(0, 10))
        ttk.Label(algo_frame, text="  Algorithm: ").pack(side="left")
        ttk.Radiobutton(algo_frame, text="LZMA (default, better ratio)", variable=self.compress_algo, value="lzma").pack(side="left", padx=5)
        ttk.Radiobutton(algo_frame, text="ZLib (faster)", variable=self.compress_algo, value="zlib").pack(side="left", padx=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

        # --- Pack Buttons ---
        ttk.Label(frame, text="3. Choose output format:", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))

        btn_sdat = ttk.Button(frame, text="Pack Folder → .SDAT (Scene File)", command=lambda: self.pack_dialog("sdat"), style="Accent.TButton")
        btn_sdat.pack(fill="x", pady=5, ipady=8)

        btn_bar = ttk.Button(frame, text="Pack Folder → .BAR (Archive)", command=lambda: self.pack_dialog("bar"))
        btn_bar.pack(fill="x", pady=5, ipady=5)

        btn_sharc = ttk.Button(frame, text="Pack Folder → .SHARC (Sound/Anim)", command=lambda: self.pack_dialog("sharc"))
        btn_sharc.pack(fill="x", pady=5, ipady=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)
        btn_pkg = ttk.Button(frame, text="Pack Folder → .PKG (Installable Package)", command=lambda: self.pack_dialog("pkg"))
        btn_pkg.pack(fill="x", pady=5, ipady=5)

    def _browse_pack_input(self):
        initial_dir = None
        proj = self.project_path.get()
        if proj and proj != "No Folder Selected" and os.path.isdir(proj):
            initial_dir = proj

        folder = filedialog.askdirectory(title="Select Folder to Pack", initialdir=initial_dir)
        if folder:
            self.pack_input_var.set(folder)
            self.log(f"Pack input set to: {folder}", "info")
            self._save_settings()

    def pack_dialog(self, format_type):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return

        input_dir = self.pack_input_var.get()
        if input_dir == "No folder selected" or not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Please select a folder to pack using the 'Browse...' button in the Create & Pack tab.")
            return

        base_name = os.path.basename(input_dir)
        if base_name.endswith("_extracted"):
            base_name = base_name.replace("_extracted", "")
        base_name, _ = os.path.splitext(base_name)
        clean_default_name = f"{base_name}.{format_type}"

        initial_dir = None
        proj = self.project_path.get()
        if proj and proj != "No Folder Selected" and os.path.isdir(proj):
            initial_dir = proj
        else:
            initial_dir = os.path.dirname(input_dir)

        output_file = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} File", f"*.{format_type}")],
            initialfile=clean_default_name,
            initialdir=initial_dir
        )
        if not output_file: return

        if self.auto_compress.get():
            self._batch_compress(input_dir)

        cmd = [format_type, "c", "-i", input_dir, "-o", output_file]
        self.run_hdk_command(cmd)

    def _batch_compress(self, directory):
        hdk_path = self.hdk_path_var.get()
        algo = self.compress_algo.get()
        self.log("=" * 60, "info")
        self.log(f"AUTO-OPTIMIZE: Compressing assets with {algo.upper()} before packing...", "info")

        extensions = ['.bar', '.havok', '.hkx', '.dds', '.xml']
        count = 0

        for root, dirs, files in os.walk(directory):
            for file in files:
                has_known_ext = any(file.lower().endswith(ext) for ext in extensions)
                has_no_ext = "." not in file

                if has_known_ext or has_no_ext:
                    full_path = os.path.join(root, file)
                    temp_path = full_path + ".tmp"

                    try:
                        startupinfo = self._get_startupinfo()
                        subprocess.run(
                            [hdk_path, "compress", "c", "-a", algo, "-i", full_path, "-o", temp_path],
                            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            startupinfo=startupinfo
                        )
                        shutil.move(temp_path, full_path)
                        count += 1
                    except Exception:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

        self.log(f"Optimization Complete. Compressed {count} files.", "success")

    # =========================================================================
    # TAB 3: RE-SHARC
    # =========================================================================
    def _build_resharc_tab(self, parent):
        frame = self._make_scrollable_tab(parent)

        ttk.Label(frame, text="BAR → SHARC Normalizer", style="Header.TLabel").pack(anchor="w", pady=(0, 5))

        desc = ("Converts legacy BAR-based .sdat files into the modern SHARC format.\n"
                "Required for revival servers that expect SHARC-based SDATs.\n"
                "Uses Zephyr's hdk-resharc tool.\n\n"
                "Output: <n>.normalized.sdat + <n>.normalized.txt (timestamp)")
        ttk.Label(frame, text=desc, wraplength=900, justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

        ttk.Label(frame, text="Single File", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))
        btn_single = ttk.Button(frame, text="SELECT .SDAT FILE TO NORMALIZE",
                                command=self.resharc_single_dialog, style="Accent.TButton")
        btn_single.pack(fill="x", pady=5, ipady=12)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(frame, text="Batch Mode (Multiple Files)", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))
        btn_batch = ttk.Button(frame, text="SELECT MULTIPLE .SDAT FILES",
                               command=self.resharc_batch_dialog)
        btn_batch.pack(fill="x", pady=5, ipady=8)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(frame, text="Folder Scan", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))
        btn_folder = ttk.Button(frame, text="SELECT FOLDER TO SCAN & NORMALIZE ALL",
                                command=self.resharc_folder_dialog)
        btn_folder.pack(fill="x", pady=5, ipady=8)

    def resharc_single_dialog(self):
        if not self._check_binary_ready(self.resharc_path_var, "Re-SHARC"): return
        filepath = filedialog.askopenfilename(
            title="Select SDAT to Normalize",
            filetypes=[("SDAT Files", "*.sdat"), ("All Files", "*.*")]
        )
        if not filepath: return
        self.log("=" * 60, "info")
        self.log(f"Re-SHARC: Normalizing {os.path.basename(filepath)}...", "info")
        self._run_resharc([filepath])

    def resharc_batch_dialog(self):
        if not self._check_binary_ready(self.resharc_path_var, "Re-SHARC"): return
        filepaths = filedialog.askopenfilenames(
            title="Select SDAT Files to Normalize",
            filetypes=[("SDAT Files", "*.sdat"), ("All Files", "*.*")]
        )
        if not filepaths: return
        self.log("=" * 60, "info")
        self.log(f"Re-SHARC Batch: Normalizing {len(filepaths)} file(s)...", "info")
        self._run_resharc(list(filepaths))

    def resharc_folder_dialog(self):
        if not self._check_binary_ready(self.resharc_path_var, "Re-SHARC"): return
        folder = filedialog.askdirectory(title="Select Folder to Scan for .sdat Files")
        if not folder: return

        sdat_files = [os.path.join(folder, f) for f in os.listdir(folder)
                      if f.lower().endswith(".sdat") and ".normalized." not in f.lower()]

        if not sdat_files:
            messagebox.showinfo("No Files Found", f"No .sdat files found in:\n{folder}")
            return

        self.log("=" * 60, "info")
        self.log(f"Re-SHARC Folder Scan: Found {len(sdat_files)} .sdat file(s)", "info")
        for sf in sdat_files:
            self.log(f"  • {os.path.basename(sf)}")
        self._run_resharc(sdat_files)

    def _run_resharc(self, file_list):
        resharc_path = self.resharc_path_var.get()
        full_cmd = [resharc_path] + file_list

        self.log(f"COMMAND: {os.path.basename(resharc_path)} {' '.join(os.path.basename(f) for f in file_list)}")

        def target():
            try:
                startupinfo = self._get_startupinfo()
                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,
                    startupinfo=startupinfo
                )
                stdout, stderr = process.communicate()
                out_str = stdout.decode('utf-8', errors='ignore')
                err_str = stderr.decode('utf-8', errors='ignore')

                if out_str.strip(): self.update_console(out_str)
                if err_str.strip(): self.update_console("LOG: " + err_str)

                if process.returncode == 0:
                    self.update_console("\n>>> RE-SHARC COMPLETE <<<", "success")
                    for f in file_list:
                        base = os.path.splitext(f)[0]
                        norm_sdat = base + ".normalized.sdat"
                        norm_txt = base + ".normalized.txt"
                        if os.path.exists(norm_sdat):
                            self.update_console(f"  Output: {norm_sdat}", "success")
                        if os.path.exists(norm_txt):
                            self.update_console(f"  Timestamp: {norm_txt}", "info")
                else:
                    self.update_console(f"\n!!! RE-SHARC FAILED (Code {process.returncode}) !!!", "error")

            except FileNotFoundError:
                self.update_console("CRITICAL: hdk-resharc executable not found!", "error")
            except Exception as e:
                self.update_console(f"CRITICAL ERROR: {str(e)}", "error")

        threading.Thread(target=target, daemon=True).start()

    # =========================================================================
    # TAB 4: LUAC DECOMPILER
    # =========================================================================
    def _build_luac_tab(self, parent):
        frame = self._make_scrollable_tab(parent)

        ttk.Label(frame, text="LUAC Decompiler", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(frame, text="Bulk decompile .luac bytecode files into readable .lua source.\n"
                  "Requires Java installed and unluac-verbose.jar (set path at top of window).",
                  wraplength=900, justify="left").pack(anchor="w", pady=(0, 10))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

        # --- Directories ---
        ttk.Label(frame, text="1. Directories", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))

        # LUAC Project Dir
        proj_row = ttk.Frame(frame)
        proj_row.pack(fill="x", pady=3)
        ttk.Label(proj_row, text="LUAC Source Folder:", width=20).pack(side="left")
        self.luac_project_var = tk.StringVar(value="No folder selected")
        ttk.Label(proj_row, textvariable=self.luac_project_var, foreground="#ffd700", font=(FONT_MONO, 9)).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(proj_row, text="Browse...", command=self._browse_luac_project, width=10).pack(side="right")

        # LUAC Output Dir
        out_row = ttk.Frame(frame)
        out_row.pack(fill="x", pady=3)
        ttk.Label(out_row, text="Decompiled Output:", width=20).pack(side="left")
        self.luac_output_var = tk.StringVar(value="No folder selected")
        ttk.Label(out_row, textvariable=self.luac_output_var, foreground="#ffd700", font=(FONT_MONO, 9)).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(out_row, text="Browse...", command=self._browse_luac_output, width=10).pack(side="right")

        # Workers
        worker_row = ttk.Frame(frame)
        worker_row.pack(fill="x", pady=(5, 5))
        ttk.Label(worker_row, text="Parallel Workers:").pack(side="left")
        self.luac_workers_var = tk.IntVar(value=4)
        ttk.Scale(worker_row, from_=1, to=16, variable=self.luac_workers_var,
                  orient=tk.HORIZONTAL, length=200).pack(side="left", padx=10)
        self.luac_workers_label = ttk.Label(worker_row, text="4")
        self.luac_workers_label.pack(side="left")
        self.luac_workers_var.trace_add("write", lambda *_: self.luac_workers_label.config(
            text=str(self.luac_workers_var.get())))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # --- Action Buttons ---
        ttk.Label(frame, text="2. Actions", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))

        btn_scan = ttk.Button(frame, text="SCAN FOR .LUAC FILES",
                              command=self.luac_scan, style="Accent.TButton")
        btn_scan.pack(fill="x", pady=5, ipady=8)

        self.luac_decompile_btn = ttk.Button(frame, text="DECOMPILE ALL",
                                             command=self.luac_decompile_all, style="Accent.TButton")
        self.luac_decompile_btn.pack(fill="x", pady=5, ipady=8)

        self.luac_stop_btn = ttk.Button(frame, text="STOP DECOMPILATION",
                                        command=self.luac_stop, style="Danger.TButton")
        self.luac_stop_btn.pack(fill="x", pady=5, ipady=5)

        btn_tree = ttk.Button(frame, text="EXPORT DIRECTORY TREE (.txt + .json)",
                              command=self.luac_export_tree)
        btn_tree.pack(fill="x", pady=5, ipady=5)

        # --- Progress & Stats ---
        self.luac_progress = ttk.Progressbar(frame, mode='determinate', style="Custom.Horizontal.TProgressbar")
        self.luac_progress.pack(fill="x", pady=(10, 3))

        self.luac_stats_label = ttk.Label(frame, text="No scan performed yet.", foreground="#888888")
        self.luac_stats_label.pack(anchor="w", pady=(0, 5))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # --- Keyword Search ---
        ttk.Label(frame, text="3. Keyword Search", style="SubHeader.TLabel").pack(anchor="w", pady=(5, 5))
        ttk.Label(frame, text="Search through .lua / .luac files for specific keywords.",
                  foreground="#888888").pack(anchor="w", pady=(0, 5))

        kw_row = ttk.Frame(frame)
        kw_row.pack(fill="x", pady=3)
        ttk.Label(kw_row, text="Keywords (comma-separated):").pack(side="left")
        self.luac_keywords_var = tk.StringVar(value="save, load, persist")
        kw_entry = ttk.Entry(kw_row, textvariable=self.luac_keywords_var, font=(FONT_MONO, 9))
        kw_entry.pack(side="left", fill="x", expand=True, padx=5)

        loc_row = ttk.Frame(frame)
        loc_row.pack(fill="x", pady=3)
        ttk.Label(loc_row, text="Search in:").pack(side="left")
        self.luac_search_location = tk.StringVar(value="Output")
        ttk.Radiobutton(loc_row, text="Source Folder (raw .luac)", variable=self.luac_search_location, value="Project").pack(side="left", padx=10)
        ttk.Radiobutton(loc_row, text="Output Folder (decompiled .lua)", variable=self.luac_search_location, value="Output").pack(side="left", padx=10)

        btn_search = ttk.Button(frame, text="SEARCH KEYWORDS", command=self.luac_search_keywords)
        btn_search.pack(fill="x", pady=5, ipady=5)

    # --- LUAC: Browse helpers ---
    def _browse_luac_project(self):
        initial = None
        proj = self.project_path.get()
        if proj and proj != "No Folder Selected" and os.path.isdir(proj):
            initial = proj
        folder = filedialog.askdirectory(title="Select folder containing .luac files", initialdir=initial)
        if folder:
            self.luac_project_var.set(folder)
            self.log(f"LUAC source folder: {folder}", "info")
            self._save_settings()

    def _browse_luac_output(self):
        folder = filedialog.askdirectory(title="Select output folder for decompiled .lua files")
        if folder:
            self.luac_output_var.set(folder)
            self.log(f"LUAC output folder: {folder}", "info")
            self._save_settings()

    # --- LUAC: Scan ---
    def luac_scan(self):
        project_dir = self.luac_project_var.get()
        if not project_dir or not os.path.isdir(project_dir):
            messagebox.showerror("Error", "Please select a LUAC Source Folder first.")
            return

        self.log("=" * 60, "info")
        self.log("Scanning for .luac files...", "info")

        def scan_thread():
            try:
                luac_files = list(Path(project_dir).rglob('*.luac'))
                self.luac_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total': len(luac_files)}
                self._update_luac_stats()
                self.update_console(f"Found {len(luac_files)} .luac files.", "success")

                output_dir = self.luac_output_var.get()
                if output_dir and os.path.isdir(output_dir):
                    self.update_console(f"Output will go to: {output_dir}", "info")
                else:
                    self.update_console("No output directory set. Please set one before decompiling.", "warning")
            except Exception as e:
                self.update_console(f"Scan failed: {e}", "error")

        threading.Thread(target=scan_thread, daemon=True).start()

    # --- LUAC: Decompile ---
    def luac_decompile_all(self):
        project_dir = self.luac_project_var.get()
        output_dir = self.luac_output_var.get()

        if not project_dir or not os.path.isdir(project_dir):
            messagebox.showerror("Error", "Please select a LUAC Source Folder first.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Please select a Decompiled Output folder first.")
            return

        unluac = self.unluac_path_var.get()
        if not unluac or "NOT FOUND" in unluac or not os.path.exists(unluac):
            messagebox.showerror("Error", "Unluac JAR not found!\n\nPlease set the path using 'Change...' at the top of the window.")
            return

        if self.luac_is_running:
            messagebox.showwarning("Busy", "Decompilation already in progress.")
            return

        self.luac_is_running = True
        self.luac_decompile_btn.config(state='disabled')
        self.log("=" * 60, "info")
        self.log("Starting LUAC decompilation...", "info")

        def decompile_thread():
            try:
                project_path = Path(project_dir)
                output_path = Path(output_dir)
                luac_files = list(project_path.rglob('*.luac'))

                self.luac_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total': len(luac_files)}
                self._update_luac_stats()

                for luac_file in luac_files:
                    if not self.luac_is_running:
                        break

                    relative = luac_file.relative_to(project_path)
                    lua_out = output_path / relative.with_suffix('.lua')
                    lua_out.parent.mkdir(parents=True, exist_ok=True)

                    if lua_out.exists():
                        self.luac_stats['skipped'] += 1
                        self.update_console(f"  Skipped (exists): {relative}")
                    else:
                        try:
                            startupinfo = self._get_startupinfo()
                            result = subprocess.run(
                                ['java', '-jar', unluac, str(luac_file)],
                                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                                check=True, startupinfo=startupinfo
                            )
                            with open(lua_out, 'w', encoding='utf-8') as f:
                                f.write(result.stdout)
                            self.luac_stats['success'] += 1
                            self.update_console(f"  Decompiled: {relative}", "success")
                        except FileNotFoundError:
                            self.update_console("CRITICAL: 'java' not found. Is Java installed and in PATH?", "error")
                            self.luac_is_running = False
                            break
                        except subprocess.CalledProcessError as e:
                            self.luac_stats['failed'] += 1
                            err_msg = e.stderr.strip() if e.stderr else "Unknown error"
                            self.update_console(f"  Failed: {relative} — {err_msg}", "error")
                        except Exception as e:
                            self.luac_stats['failed'] += 1
                            self.update_console(f"  Error: {relative} — {e}", "error")

                    self.after(0, self._update_luac_stats)

                if self.luac_is_running:
                    s = self.luac_stats
                    self.update_console(
                        f"\n>>> DECOMPILATION COMPLETE — "
                        f"{s['success']} OK / {s['failed']} Failed / {s['skipped']} Skipped <<<", "success")
                else:
                    self.update_console("\n--- Decompilation stopped by user ---", "warning")

            except Exception as e:
                self.update_console(f"CRITICAL: {e}", "error")
            finally:
                self.luac_is_running = False
                self.after(0, lambda: self.luac_decompile_btn.config(state='normal'))

        threading.Thread(target=decompile_thread, daemon=True).start()

    def luac_stop(self):
        if self.luac_is_running:
            self.luac_is_running = False
            self.log("Stopping decompilation...", "warning")
        else:
            self.log("No decompilation in progress.", "info")

    def _update_luac_stats(self):
        s = self.luac_stats
        total = s['total']
        done = s['success'] + s['failed'] + s['skipped']
        text = f"Total: {total}  |  Success: {s['success']}  |  Failed: {s['failed']}  |  Skipped: {s['skipped']}"
        self.luac_stats_label.config(text=text)
        if total > 0:
            self.luac_progress['value'] = (done / total) * 100

    # --- LUAC: Export Tree ---
    def luac_export_tree(self):
        project_dir = self.luac_project_var.get()
        if not project_dir or not os.path.isdir(project_dir):
            messagebox.showerror("Error", "Please select a LUAC Source Folder first.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Directory Tree As"
        )
        if not save_path:
            return

        self.log("Exporting directory tree...", "info")

        def export_thread():
            try:
                base_save = Path(save_path).with_suffix('')

                # TXT (human-readable)
                txt_path = base_save.with_suffix('.txt')
                tree_lines = []
                for root, dirs, files in os.walk(project_dir):
                    level = root.replace(project_dir, '').count(os.sep)
                    indent = '    ' * level
                    tree_lines.append(f'{indent}[DIR] {os.path.basename(root)}/')
                    sub_indent = '    ' * (level + 1)
                    for f in sorted(files):
                        tree_lines.append(f'{sub_indent}{f}')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(tree_lines))
                self.update_console(f"  Tree (TXT): {txt_path}", "success")

                # JSON (machine-readable)
                def path_to_dict(p):
                    d = {'name': os.path.basename(p), 'type': 'directory'}
                    children_dirs = sorted([
                        path_to_dict(os.path.join(p, c))
                        for c in os.listdir(p) if os.path.isdir(os.path.join(p, c))
                    ], key=lambda x: x['name'])
                    children_files = sorted([
                        {'name': c, 'type': 'file'}
                        for c in os.listdir(p) if os.path.isfile(os.path.join(p, c))
                    ], key=lambda x: x['name'])
                    d['children'] = children_dirs + children_files
                    return d

                json_path = base_save.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(path_to_dict(project_dir), f, indent=4)
                self.update_console(f"  Tree (JSON): {json_path}", "success")

                self.update_console(">>> TREE EXPORT COMPLETE <<<", "success")

            except Exception as e:
                self.update_console(f"Tree export failed: {e}", "error")

        threading.Thread(target=export_thread, daemon=True).start()

    # --- LUAC: Keyword Search ---
    def luac_search_keywords(self):
        location = self.luac_search_location.get()
        if location == "Project":
            target_dir = self.luac_project_var.get()
        else:
            target_dir = self.luac_output_var.get()

        if not target_dir or not os.path.isdir(target_dir):
            messagebox.showerror("Error", f"Please select the {'Source' if location == 'Project' else 'Output'} folder first.")
            return

        keywords_str = self.luac_keywords_var.get()
        if not keywords_str.strip():
            messagebox.showerror("Error", "Please enter keywords to search for.")
            return

        keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        self.log("=" * 60, "info")
        self.log(f"Searching for: {', '.join(keywords)} in {location} folder...", "info")
        self._save_settings()

        def search_thread():
            try:
                search_path = Path(target_dir)
                results = {}

                files_to_search = [p for p in search_path.rglob('*')
                                   if p.is_file() and p.suffix in ('.lua', '.luac')]

                for file in files_to_search:
                    try:
                        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                        found = [(kw, content.count(kw)) for kw in keywords if kw in content]
                        if found:
                            results[str(file.relative_to(search_path))] = found
                    except Exception:
                        pass

                if results:
                    self.update_console("\n--- KEYWORD SEARCH RESULTS ---", "info")
                    sorted_results = sorted(results.items(),
                                            key=lambda item: sum(c for _, c in item[1]), reverse=True)
                    for file_path, matches in sorted_results:
                        total = sum(c for _, c in matches)
                        self.update_console(f"\n  {file_path} ({total} matches):", "success")
                        for kw, count in sorted(matches, key=lambda x: x[1], reverse=True):
                            self.update_console(f"    '{kw}': {count} times")
                    self.update_console(f"\nFound matches in {len(results)} file(s).", "info")
                else:
                    self.update_console("No keywords found in any files.", "warning")

            except Exception as e:
                self.update_console(f"Search failed: {e}", "error")

        threading.Thread(target=search_thread, daemon=True).start()

    # =========================================================================
    # TAB 5: ADVANCED TOOLS
    # =========================================================================
    def _build_tools_tab(self, parent):
        frame = self._make_scrollable_tab(parent)

        # ---- MAP TOOL ----
        ttk.Label(frame, text="Map Tool (Restore File Names)", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Recovers original file paths from hash-named archive entries.").pack(anchor="w", pady=(0, 5))

        self.map_full_scan = tk.BooleanVar()
        chk_map = ttk.Checkbutton(frame, text="Use Full Regex Scan (slower, more accurate)", variable=self.map_full_scan)
        chk_map.pack(anchor="w", pady=(0, 3))

        uuid_frame = ttk.Frame(frame)
        uuid_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(uuid_frame, text="UUID (for objects only):").pack(side="left")
        self.map_uuid_var = tk.StringVar(value="")
        uuid_entry = ttk.Entry(uuid_frame, textvariable=self.map_uuid_var, width=45, font=(FONT_MONO, 9))
        uuid_entry.pack(side="left", padx=5)
        ttk.Label(uuid_frame, text="(leave blank for scenes)", foreground="#888888").pack(side="left")

        btn_map = ttk.Button(frame, text="Map Directory (Renames hashed files)", command=self.map_dialog)
        btn_map.pack(fill="x", pady=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # ---- COMPRESSION ----
        ttk.Label(frame, text="Compression (EdgeZLib / EdgeLZMA)", style="Header.TLabel").pack(anchor="w")

        algo_frame2 = ttk.Frame(frame)
        algo_frame2.pack(anchor="w", pady=(5, 5))
        self.tool_compress_algo = tk.StringVar(value="lzma")
        ttk.Label(algo_frame2, text="Algorithm: ").pack(side="left")
        ttk.Radiobutton(algo_frame2, text="LZMA (default)", variable=self.tool_compress_algo, value="lzma").pack(side="left", padx=5)
        ttk.Radiobutton(algo_frame2, text="ZLib", variable=self.tool_compress_algo, value="zlib").pack(side="left", padx=5)

        btn_comp = ttk.Button(frame, text="Compress File", command=lambda: self.compress_dialog("c"))
        btn_comp.pack(fill="x", pady=2)
        btn_decomp = ttk.Button(frame, text="Decompress File", command=lambda: self.compress_dialog("d"))
        btn_decomp.pack(fill="x", pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # ---- CRYPTOGRAPHY ----
        ttk.Label(frame, text="Cryptography (Blowfish CTR)", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Encrypt, decrypt, or auto-detect files. Optional type hint for IV recovery.").pack(anchor="w", pady=(0, 5))

        type_frame = ttk.Frame(frame)
        type_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(type_frame, text="Type hint (optional):").pack(side="left")
        self.crypt_type_var = tk.StringVar(value="auto-detect")
        type_combo = ttk.Combobox(type_frame, textvariable=self.crypt_type_var, width=20, state="readonly",
                                   values=["auto-detect", "odc", "xml", "scene-list", "lua", "bar", "pem", "hcdb"])
        type_combo.pack(side="left", padx=5)

        btn_encrypt = ttk.Button(frame, text="Encrypt File", command=lambda: self.crypt_dialog("e"))
        btn_encrypt.pack(fill="x", pady=2)
        btn_decrypt = ttk.Button(frame, text="Decrypt File", command=lambda: self.crypt_dialog("d"))
        btn_decrypt.pack(fill="x", pady=2)
        btn_auto = ttk.Button(frame, text="Auto-Detect (Encrypt/Decrypt)", command=lambda: self.crypt_dialog("a"))
        btn_auto.pack(fill="x", pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # ---- PKG INSPECT ----
        ttk.Label(frame, text="PKG Inspection", style="Header.TLabel").pack(anchor="w")
        btn_inspect = ttk.Button(frame, text="Inspect .PKG File (View Metadata)", command=self.inspect_pkg_dialog)
        btn_inspect.pack(fill="x", pady=5)

    def map_dialog(self):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return
        target_dir = filedialog.askdirectory(title="Select Directory to Map")
        if not target_dir: return

        cmd = ["map", "-i", target_dir]
        uuid_val = self.map_uuid_var.get().strip()
        if uuid_val:
            cmd.extend(["-u", uuid_val])
        if self.map_full_scan.get():
            cmd.append("--full")
            self.log("Note: Full regex scan enabled. This may take longer.", "info")
        self.run_hdk_command(cmd)

    def compress_dialog(self, mode):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return

        f = filedialog.askopenfilename(title="Select file to compress/decompress")
        if not f: return

        default_suffix = ".compressed" if mode == "c" else ".decompressed"
        out_f = filedialog.asksaveasfilename(
            title="Save output as...",
            initialfile=os.path.basename(f) + default_suffix
        )
        if not out_f: return

        algo = self.tool_compress_algo.get()
        cmd = ["compress", mode, "-a", algo, "-i", f, "-o", out_f]
        self.run_hdk_command(cmd)

    def crypt_dialog(self, mode):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return
        f = filedialog.askopenfilename()
        if not f: return
        cmd = ["crypt", mode]
        type_hint = self.crypt_type_var.get()
        if mode in ("d", "a") and type_hint != "auto-detect":
            cmd.extend(["-t", type_hint])
        self.run_hdk_command(cmd, input_file=f)

    def inspect_pkg_dialog(self):
        if not self._check_binary_ready(self.hdk_path_var, "HDK"): return
        f = filedialog.askopenfilename(filetypes=[("PKG File", "*.pkg")])
        if not f: return
        self.run_hdk_command(["pkg", "i", f])

    # =========================================================================
    # TAB 6: ENCYCLOPEDIA
    # =========================================================================
    def _build_help_tab(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="both", expand=True)

        help_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, bg="#1e1e1e", fg="#e0e0e0", font=(FONT_MAIN, 10))
        help_text.pack(fill="both", expand=True)

        help_text.tag_configure("title", foreground="#4db8ff", font=(FONT_HEADER, 14, "bold"))
        help_text.tag_configure("heading", foreground="#ffd700", font=(FONT_HEADER, 11, "bold"))
        help_text.tag_configure("subheading", foreground="#00cc88", font=(FONT_MAIN, 10, "bold"))
        help_text.tag_configure("body", foreground="#e0e0e0", font=(FONT_MAIN, 10))
        help_text.tag_configure("command", foreground="#00ff00", font=(FONT_MONO, 10))
        help_text.tag_configure("warning", foreground="#ff8800", font=(FONT_MAIN, 10, "italic"))
        help_text.tag_configure("separator", foreground="#555555")

        def add(text, tag="body"):
            help_text.insert(tk.END, text, tag)

        add("PlayStation Home HDK File Encyclopedia\n", "title")
        add("Based on hdk-cli README & hdk-resharc\n", "subheading")
        add("=" * 70 + "\n\n", "separator")

        add("FILE FORMATS\n", "heading")
        add("-" * 50 + "\n\n", "separator")

        entries = [
            ("1. SDAT (.sdat)", "Secure Data Archive Tape",
             "The main container for a Home Scene. Contains geometry, textures, scripts, physics.\n"
             "This is the file the game loads to generate the world.\n"
             "WARNING: Timestamps are written as big-endian. Parse .time files accordingly.\n",
             "sdat x / sdat c  (aliases: extract/create)"),
            ("2. SDC (.sdc)", "Scene Description Configuration",
             "Metadata file. The PS3 downloads this FIRST to check scene validity.\n"
             "Contains: Version number, Age Rating, Content ID, .sdat link.\n"
             "IMPORTANT: If you version-up a scene, update this file too!\n", None),
            ("3. BAR (.bar)", "Binary Archive Resource (LEGACY)",
             "General-purpose archive found INSIDE .sdat files.\n"
             "Entries are XTEA-encrypted. Place a .time file in the input dir for a custom timestamp.\n"
             "NOTE: This is the LEGACY format. Modern servers expect SHARC.\n",
             "bar x / bar c"),
            ("4. SHARC (.sharc)", "Sony Home Archive Resource Container (MODERN)",
             "The modern archive format, replacing BAR in later Home builds.\n"
             "Uses SegmentedZlibWriter internally for compression.\n"
             "Revival servers typically expect SHARC-based SDATs.\n",
             "sharc x / sharc c"),
            ("5. PKG (.pkg)", "PlayStation Package",
             "The installer format for PlayStation 3.\n"
             "You can inspect, extract, or create PKG files.\n",
             "pkg i / pkg x / pkg c  (inspect/extract/create)"),
            ("6. XML (.xml)", "Extensible Markup Language",
             "Readable config files. Defines object placement, mini-game params.\n"
             "CRITICAL FOR OFFLINE: Edit to remove 'http://' links!\n", None),
            ("7. LUA (.lua) / LUAC (.luac)", "Lua Script / Compiled Lua Bytecode",
             "The programming language of PlayStation Home.\n"
             "Found inside scripts.bar or USRDIR/scripts.\n"
             ".luac files are compiled bytecode — use the LUAC Decompiler tab to convert\n"
             "them back into readable .lua source with unluac-verbose.jar.\n", None),
            ("8. HKX (.hkx)", "Havok Physics",
             "Defines collision and animations. Proprietary binary format.\n", None),
            ("9. DDS (.dds)", "DirectDraw Surface",
             "Standard texture format for 3D models in Home.\n", None),
        ]

        for title, subtitle, desc, cmd in entries:
            add(f"{title} — {subtitle}\n", "subheading")
            add(desc)
            if cmd:
                add("   Command: ", "body"); add(f"{cmd}\n", "command")
            add("\n")

        add("=" * 70 + "\n\n", "separator")
        add("TOOLS REFERENCE\n", "heading")
        add("-" * 50 + "\n\n", "separator")

        add("hdk-cli\n", "subheading")
        add("   Crypt: ", "body"); add("crypt e | crypt d | crypt a", "command"); add("  (encrypt / decrypt / auto)\n")
        add("   Type hints (-t): ", "body"); add("odc, xml, scene-list, lua, bar, pem, hcdb\n", "command")
        add("   Compress: ", "body"); add("compress c | compress d", "command"); add("  with  "); add("-a lzma | -a zlib\n\n", "command")
        add("   Map: ", "body"); add("map -i <dir> [--full] [-u <uuid>]\n", "command")
        add("   Use -u for object archives only (NOT scenes).\n\n")

        add("hdk-resharc\n", "subheading")
        add("   Usage: ", "body"); add("hdk-resharc file1.sdat file2.sdat ...\n", "command")
        add("   No flags. Just raw file paths. Outputs .normalized.sdat\n\n")

        add("LUAC Decompiler\n", "subheading")
        add("   Requires: ", "body"); add("Java + unluac-verbose.jar\n", "command")
        add("   Converts compiled .luac bytecode back to readable .lua source.\n")
        add("   Includes keyword search and directory tree export.\n\n")

        add("=" * 70 + "\n\n", "separator")
        add("QUICK WORKFLOW\n", "heading")
        add("-" * 50 + "\n\n", "separator")
        add("1. UNPACK:    Extract .pkg to get the .sdat\n", "command")
        add("2. UNLOCK:    Extract the .sdat to get raw files\n", "command")
        add("3. DIG:       Extract any .bar files inside\n", "command")
        add("4. DECOMPILE: Use LUAC Decompiler tab on any .luac scripts\n", "command")
        add("5. EDIT:      Modify .xml or .lua files\n", "command")
        add("6. REPACK:    Pack folder → .sdat\n", "command")
        add("7. NORMALIZE: Re-SHARC to convert BAR→SHARC\n", "command")
        add("8. PLAY:      Copy .sdat to RPCS3 USRDIR/SCENES/\n", "command")

        help_text.config(state=tk.DISABLED)

    # =========================================================================
    # CORE UTILITIES
    # =========================================================================
    def _get_startupinfo(self):
        if IS_WINDOWS:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None

    def _browse_exe(self, name, path_var):
        if IS_WINDOWS:
            ftypes = [("Executable", "*.exe"), ("All Files", "*.*")]
        elif IS_MAC:
            ftypes = [("All Files", "*"), ("Unix Executable", "*")]
        else:
            ftypes = [("All Files", "*")]

        f = filedialog.askopenfilename(title=f"Locate {name} executable", filetypes=ftypes)
        if f:
            if not IS_WINDOWS and not os.access(f, os.X_OK):
                result = messagebox.askyesno("Not Executable",
                    f"'{os.path.basename(f)}' is not marked as executable.\n\n"
                    "Would you like to make it executable now?\n"
                    f"(chmod +x {f})")
                if result:
                    try:
                        os.chmod(f, os.stat(f).st_mode | 0o755)
                        self.log(f"Made {os.path.basename(f)} executable (chmod +x)", "info")
                    except Exception as e:
                        self.log(f"Failed to chmod: {e}", "error")

            path_var.set(f)
            self.log(f"{name} binary set to: {f}", "info")
            self._save_settings()

    def _browse_jar(self):
        f = filedialog.askopenfilename(
            title="Locate unluac .jar file",
            filetypes=[("Java Archives", "*.jar"), ("All Files", "*.*")]
        )
        if f:
            self.unluac_path_var.set(f)
            self.log(f"Unluac JAR set to: {f}", "info")
            self._save_settings()

    def select_project(self):
        path = filedialog.askdirectory()
        if path:
            self.project_path.set(path)
            self.log(f"Active Project set to: {path}", "info")
            self._save_settings()

    def _check_binary_ready(self, path_var, label):
        path = path_var.get()
        if not path or "NOT FOUND" in path:
            messagebox.showerror("Configuration Error",
                f"{label} binary not found!\n\nPlease click 'Change...' at the top to locate it.")
            return False
        if not os.path.exists(path):
            messagebox.showerror("Configuration Error",
                f"{label} binary path is invalid:\n{path}\n\nPlease click 'Change...' to re-locate it.")
            return False
        return True

    def run_hdk_command(self, args, input_file=None):
        hdk_path = self.hdk_path_var.get()
        full_cmd = [hdk_path] + args
        self.log("-" * 60)
        self.log(f"RUNNING: hdk {' '.join(args)}")

        def target():
            try:
                startupinfo = self._get_startupinfo()
                stdin_val = subprocess.PIPE if input_file else None
                input_data = None

                if input_file:
                    self.log(f"Piping input file: {input_file}")
                    with open(input_file, 'rb') as f:
                        input_data = f.read()

                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=stdin_val,
                    text=False,
                    startupinfo=startupinfo
                )

                stdout, stderr = process.communicate(input=input_data)
                out_str = stdout.decode('utf-8', errors='ignore')
                err_str = stderr.decode('utf-8', errors='ignore')

                if out_str.strip(): self.update_console(out_str)
                if err_str.strip(): self.update_console("LOG: " + err_str)

                if process.returncode == 0:
                    self.update_console("\n>>> SUCCESS <<<", "success")
                else:
                    self.update_console(f"\n!!! FAILED (Code {process.returncode}) !!!", "error")

            except FileNotFoundError:
                self.update_console("CRITICAL: Executable not found at the configured path!", "error")
            except Exception as e:
                self.update_console(f"CRITICAL ERROR: {str(e)}", "error")

        threading.Thread(target=target, daemon=True).start()

    def log(self, msg, tag=None):
        if tag:
            self.console.insert(tk.END, msg + "\n", tag)
        else:
            self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)

    def update_console(self, msg, tag=None):
        self.after(0, lambda: self.log(msg.strip(), tag))


if __name__ == "__main__":
    app = HDKCommander()
    app.mainloop()