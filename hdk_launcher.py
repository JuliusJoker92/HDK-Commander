import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import shutil
import platform
import json

# =========================================================================
# CONFIGURATION
# =========================================================================
DEFAULT_HDK_PATH = r""
DEFAULT_RESHARC_PATH = r""

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

        self.hdk_path_var.set(found_hdk if found_hdk else "NOT FOUND - Click Change...")
        self.resharc_path_var.set(found_resharc if found_resharc else "NOT FOUND - Click Change...")

        # Restore project path from settings
        saved_project = self.settings.get("project_path", "")
        if saved_project and os.path.isdir(saved_project):
            self.project_path.set(saved_project)

        self._setup_styles()
        self._setup_ui()

        # Restore pack input from settings
        saved_pack_input = self.settings.get("pack_input_path", "")
        if saved_pack_input and os.path.isdir(saved_pack_input):
            self.pack_input_var.set(saved_pack_input)

        # Save settings on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Alerts for missing binaries (only on true first run)
        missing = []
        if not found_hdk:
            missing.append("hdk (hdk-cli)")
        if not found_resharc:
            missing.append("hdk-resharc")

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
        project = self.project_path.get()
        pack_input = self.pack_input_var.get() if hasattr(self, 'pack_input_var') else ""

        data = {
            "hdk_path": hdk if "NOT FOUND" not in hdk else "",
            "resharc_path": resharc if "NOT FOUND" not in resharc else "",
            "project_path": project if project != "No Folder Selected" else "",
            "pack_input_path": pack_input if pack_input != "No folder selected" else "",
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
        # 1. Check saved setting
        saved = self.settings.get(settings_key, "")
        if saved and os.path.exists(saved):
            return saved

        # 2. Check manual default from config
        if manual_default and os.path.exists(manual_default):
            return manual_default

        # 3. Auto-detect
        if IS_MAC or IS_LINUX:
            home = os.path.expanduser("~")
            candidates.append(os.path.join(home, ".cargo", "bin", name))

        return self._find_binary(name, candidates)

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

        style.configure("TLabelframe", background=bg_dark, foreground=text_color)
        style.configure("TLabelframe.Label", background=bg_dark, foreground="#4db8ff")

        style.configure("TNotebook", background=bg_medium, borderwidth=0)
        style.configure("TNotebook.Tab", background=bg_medium, foreground=text_color, padding=[10, 5])
        style.map("TNotebook.Tab", background=[('selected', accent_color)])

        style.configure("TCheckbutton", background=bg_dark, foreground=text_color)
        style.configure("TRadiobutton", background=bg_dark, foreground=text_color)

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

        # Make inner frame expand to fill canvas width
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
            if IS_MAC:
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
            else:
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

        # Row 3: Project Location
        r3 = ttk.Frame(config_frame)
        r3.pack(fill="x", pady=3)
        ttk.Label(r3, text="Active Project:", style="Header.TLabel", width=18).pack(side="left")
        ttk.Label(r3, textvariable=self.project_path, foreground="#ffd700", font=(FONT_MONO, 10)).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(r3, text="Browse Folder...", command=self.select_project, width=15).pack(side="right")

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
        notebook.add(tab_resharc, text="  RE-SHARC (BAR→SHARC)  ")
        self._build_resharc_tab(tab_resharc)

        tab_tools = ttk.Frame(notebook)
        notebook.add(tab_tools, text="  ADVANCED TOOLS  ")
        self._build_tools_tab(tab_tools)

        tab_help = ttk.Frame(notebook)
        notebook.add(tab_help, text="  FILE ENCYCLOPEDIA  ")
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
    # TAB 4: ADVANCED TOOLS
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
    # TAB 5: ENCYCLOPEDIA
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
            ("7. LUA (.lua)", "Lua Script",
             "The programming language of PlayStation Home.\n"
             "Found inside scripts.bar or USRDIR/scripts.\n", None),
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

        add("=" * 70 + "\n\n", "separator")
        add("QUICK WORKFLOW\n", "heading")
        add("-" * 50 + "\n\n", "separator")
        add("1. UNPACK:    Extract .pkg to get the .sdat\n", "command")
        add("2. UNLOCK:    Extract the .sdat to get raw files\n", "command")
        add("3. DIG:       Extract any .bar files inside\n", "command")
        add("4. EDIT:      Modify .xml or .lua files\n", "command")
        add("5. REPACK:    Pack folder → .sdat\n", "command")
        add("6. NORMALIZE: Re-SHARC to convert BAR→SHARC\n", "command")
        add("7. PLAY:      Copy .sdat to RPCS3 USRDIR/SCENES/\n", "command")

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