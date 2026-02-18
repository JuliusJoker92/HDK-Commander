import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import sys

# =========================================================================
# CONFIGURATION
# =========================================================================
# This is your default fallback path. The tool will look here first.
DEFAULT_HDK_PATH = r""

class HDKCommander(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PlayStation Home HDK Commander (Smart Path Edition)")
        self.geometry("1000x850") # Slightly taller for the extra config row
        self.configure(bg="#1e1e1e")

        # Variables
        self.hdk_path_var = tk.StringVar(value="Searching...")
        self.project_path = tk.StringVar(value="No Folder Selected")
        self.status_var = tk.StringVar(value="Ready")

        # Attempt to find the binary immediately
        found_path = self._find_hdk_binary()
        if found_path:
            self.hdk_path_var.set(found_path)
        else:
            self.hdk_path_var.set("HDK.EXE NOT FOUND - PLEASE BROWSE")

        self._setup_styles()
        self._setup_ui()
        
        # Friendly alert if we couldn't find it
        if not found_path:
            messagebox.showinfo("Setup Required", 
                "Could not auto-detect 'hdk.exe'.\n\n"
                "Please use the 'Change...' button at the top to locate your compiled hdk.exe file.")

    def _find_hdk_binary(self):
        # 1. Check your hardcoded default
        if DEFAULT_HDK_PATH and os.path.exists(DEFAULT_HDK_PATH):
            return DEFAULT_HDK_PATH
        
        # 2. Check current directory (Portable Mode)
        local_exe = os.path.join(os.getcwd(), "hdk.exe")
        if os.path.exists(local_exe):
            return local_exe
            
        # 3. Check standard build folder (Standard Setup)
        build_exe = os.path.join(os.getcwd(), "hdk-cli", "target", "release", "hdk.exe")
        if os.path.exists(build_exe):
            return build_exe
            
        return None

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Dark Theme Colors
        bg_dark = "#1e1e1e"
        bg_medium = "#2b2b2b"
        accent_color = "#007acc"
        text_color = "#ffffff"

        style.configure("TFrame", background=bg_dark)
        style.configure("TLabel", background=bg_dark, foreground=text_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#4db8ff")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10, "bold"), foreground="#aaaaaa")
        
        style.configure("TButton", background=bg_medium, foreground=text_color, borderwidth=1, font=("Segoe UI", 9))
        style.map("TButton", background=[('active', accent_color)])
        
        style.configure("TLabelframe", background=bg_dark, foreground=text_color)
        style.configure("TLabelframe.Label", background=bg_dark, foreground="#4db8ff")
        
        style.configure("TNotebook", background=bg_medium, borderwidth=0)
        style.configure("TNotebook.Tab", background=bg_medium, foreground=text_color, padding=[10, 5])
        style.map("TNotebook.Tab", background=[('selected', accent_color)])

    def _setup_ui(self):
        # --- HEADER / CONFIG AREA (NEW) ---
        config_frame = ttk.Frame(self, padding=15)
        config_frame.pack(fill="x")
        
        # Row 1: HDK Location
        r1 = ttk.Frame(config_frame)
        r1.pack(fill="x", pady=5)
        ttk.Label(r1, text="HDK Binary:", style="SubHeader.TLabel", width=15).pack(side="left")
        ttk.Label(r1, textvariable=self.hdk_path_var, foreground="#00ff00", font=("Consolas", 9)).pack(side="left", padx=5)
        ttk.Button(r1, text="Change...", command=self.browse_hdk_exe, width=10).pack(side="right")

        # Row 2: Project Location
        r2 = ttk.Frame(config_frame)
        r2.pack(fill="x", pady=5)
        ttk.Label(r2, text="Active Project:", style="Header.TLabel", width=15).pack(side="left")
        ttk.Label(r2, textvariable=self.project_path, foreground="#ffd700", font=("Consolas", 10)).pack(side="left", padx=5)
        ttk.Button(r2, text="Browse Folder...", command=self.select_project, width=15).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # --- TABS ---
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=10, pady=5)

        # Tab 1: Extract
        tab_extract = ttk.Frame(notebook)
        notebook.add(tab_extract, text="  EXTRACT & DECRYPT  ")
        self._build_extract_tab(tab_extract)

        # Tab 2: Create/Pack
        tab_create = ttk.Frame(notebook)
        notebook.add(tab_create, text="  CREATE & PACK  ")
        self._build_create_tab(tab_create)

        # Tab 3: Advanced Tools
        tab_tools = ttk.Frame(notebook)
        notebook.add(tab_tools, text="  ADVANCED TOOLS  ")
        self._build_tools_tab(tab_tools)

        # Tab 4: Encyclopedia
        tab_help = ttk.Frame(notebook)
        notebook.add(tab_help, text="  FILE ENCYCLOPEDIA  ")
        self._build_help_tab(tab_help)

        # --- CONSOLE ---
        console_frame = ttk.LabelFrame(self, text=" System Output Log ", padding=5)
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.console = scrolledtext.ScrolledText(console_frame, height=10, bg="#101010", fg="#00ff00", 
                                                 insertbackground="white", font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

    # =========================================================================
    # TAB 1: EXTRACT LOGIC
    # =========================================================================
    def _build_extract_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Unpack Game Archives", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(frame, text="Select a file to automatically detect its type (.sdat, .bar, .sharc, .pkg) and extract it.").pack(anchor="w", pady=(0, 20))

        btn = ttk.Button(frame, text="SELECT FILE TO EXTRACT", command=self.extract_file_dialog)
        btn.pack(fill="x", pady=5, ipady=15)

    def extract_file_dialog(self):
        if not self._check_hdk_ready(): return

        filepath = filedialog.askopenfilename(filetypes=[("Home Files", "*.sdat *.bar *.sharc *.pkg")])
        if not filepath: return

        # Auto-detect extension
        ext = os.path.splitext(filepath)[1].lower()
        output_path = filepath + "_extracted"

        cmd = []
        if ext == ".sdat":
            cmd = ["sdat", "extract", "--input", filepath, "--output", output_path]
        elif ext == ".bar":
            cmd = ["bar", "extract", "--input", filepath, "--output", output_path]
        elif ext == ".sharc":
            cmd = ["sharc", "extract", "--input", filepath, "--output", output_path]
        elif ext == ".pkg":
            cmd = ["pkg", "extract", "--input", filepath, "--output", output_path]
        else:
            self.log("Error: Unknown file type.")
            return

        self.run_hdk_command(cmd)

    # =========================================================================
    # TAB 2: CREATE LOGIC
    # =========================================================================
    def _build_create_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Pack Folders into Archives", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(frame, text="Select the active project folder (Top Right) first!", foreground="yellow").pack(anchor="w", pady=(0, 5))

        # Auto-Compress Checkbox
        self.auto_compress = tk.BooleanVar(value=False)
        chk_comp = ttk.Checkbutton(frame, text="Auto-Optimize: Compress Assets (Smaller file, slower build)", variable=self.auto_compress)
        chk_comp.pack(anchor="w", pady=(0, 15))

        # SDAT
        btn_sdat = ttk.Button(frame, text="Pack Folder -> .SDAT (Scene File)", command=lambda: self.pack_dialog("sdat"))
        btn_sdat.pack(fill="x", pady=5, ipady=5)

        # BAR
        btn_bar = ttk.Button(frame, text="Pack Folder -> .BAR (Archive)", command=lambda: self.pack_dialog("bar"))
        btn_bar.pack(fill="x", pady=5, ipady=5)

        # SHARC
        btn_sharc = ttk.Button(frame, text="Pack Folder -> .SHARC (Sound/Anim)", command=lambda: self.pack_dialog("sharc"))
        btn_sharc.pack(fill="x", pady=5, ipady=5)

        # PKG
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15)
        btn_pkg = ttk.Button(frame, text="Pack Folder -> .PKG (Installable Package)", command=lambda: self.pack_dialog("pkg"))
        btn_pkg.pack(fill="x", pady=5, ipady=5)

    def pack_dialog(self, format_type):
        if not self._check_hdk_ready(): return

        input_dir = self.project_path.get()
        if input_dir == "No Folder Selected" or not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Please select a valid Project Folder using the 'Browse' button at the top.")
            return

        output_file = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} File", f"*.{format_type}")],
            initialfile=os.path.basename(input_dir) + f".{format_type}"
        )
        if not output_file: return

        # === PRE-BUILD COMPRESSION LOGIC ===
        if self.auto_compress.get():
            self._batch_compress(input_dir)

        cmd = [format_type, "create", "--input", input_dir, "--output", output_file]
        self.run_hdk_command(cmd)

    def _batch_compress(self, directory):
        hdk_path = self.hdk_path_var.get()
        self.log("-" * 60)
        self.log("AUTO-OPTIMIZE: Compressing assets before packing...")
        
        extensions = ['.bar', '.havok', '.dds', '.xml']
        count = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    try:
                        subprocess.run([hdk_path, "compress", "compress", full_path], 
                                     check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        count += 1
                    except:
                        self.log(f"Warning: Could not compress {file}")
        
        self.log(f"Optimization Complete. Compressed {count} files.")

    # =========================================================================
    # TAB 3: ADVANCED TOOLS
    # =========================================================================
    def _build_tools_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        # MAP
        ttk.Label(frame, text="Map Tool (Restores File Names)", style="Header.TLabel").pack(anchor="w")
        self.map_full_scan = tk.BooleanVar()
        chk_map = ttk.Checkbutton(frame, text="Use Full Regex Scan (Slower, but more accurate)", variable=self.map_full_scan)
        chk_map.pack(anchor="w", pady=(0, 5))
        
        btn_map = ttk.Button(frame, text="Map Directory (Renames hashed files)", command=self.map_dialog)
        btn_map.pack(fill="x", pady=5)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # COMPRESS
        ttk.Label(frame, text="Compression Utilities", style="Header.TLabel").pack(anchor="w")
        btn_comp = ttk.Button(frame, text="Compress File (EdgeZLib)", command=lambda: self.compress_dialog("compress"))
        btn_comp.pack(fill="x", pady=2)
        btn_decomp = ttk.Button(frame, text="Decompress File", command=lambda: self.compress_dialog("decompress"))
        btn_decomp.pack(fill="x", pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        # CRYPT & PKG
        ttk.Label(frame, text="Inspection & Cryptography", style="Header.TLabel").pack(anchor="w")
        btn_inspect = ttk.Button(frame, text="Inspect .PKG File (View Metadata)", command=self.inspect_pkg_dialog)
        btn_inspect.pack(fill="x", pady=2)
        btn_crypt = ttk.Button(frame, text="Raw Decrypt (Advanced Users)", command=lambda: self.crypt_dialog("decrypt"))
        btn_crypt.pack(fill="x", pady=2)

    def map_dialog(self):
        if not self._check_hdk_ready(): return
        target_dir = filedialog.askdirectory(title="Select Directory to Map")
        if not target_dir: return
        
        cmd = ["map", "--input", target_dir]
        if self.map_full_scan.get():
            cmd.append("--full")
            self.log("Note: Full scan enabled. This may take longer.")

        self.run_hdk_command(cmd)

    def compress_dialog(self, mode):
        if not self._check_hdk_ready(): return
        f = filedialog.askopenfilename()
        if not f: return
        self.run_hdk_command(["compress", mode, f])

    def inspect_pkg_dialog(self):
        if not self._check_hdk_ready(): return
        f = filedialog.askopenfilename(filetypes=[("PKG File", "*.pkg")])
        if not f: return
        self.run_hdk_command(["pkg", "inspect", f])

    def crypt_dialog(self, mode):
        if not self._check_hdk_ready(): return
        f = filedialog.askopenfilename()
        if not f: return
        self.run_hdk_command(["crypt", mode], input_file=f)

    # =========================================================================
    # TAB 4: ENCYCLOPEDIA
    # =========================================================================
    def _build_help_tab(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="both", expand=True)
        
        help_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, bg="#1e1e1e", fg="#e0e0e0", font=("Segoe UI", 10))
        help_text.pack(fill="both", expand=True)
        
        guide_content = """
PlayStation Home HDK File Encyclopedia
Based on HDK Documentation & API
--------------------------------------------------

1. SDAT (.sdat) - Secure Data Archive Tape
   - The "Main Container" for a Home Scene. 
   - Usage: This is the file the game loads to generate the world.
   - Command: sdat extract (unpack) / sdat create (pack)

2. SDC (.sdc) - Scene Description Configuration
   - The "Metadata" file.
   - Usage: The PS3 downloads this FIRST to check if the scene is valid.
   - IMPORTANT: If you version-up a scene, you often need to update this file.

3. BAR (.bar) - Binary Archive Resource
   - A general-purpose archive found INSIDE .sdat files.
   - Common types: minigame.bar, scripts.bar, assets.bar.
   - Command: bar extract / bar create

4. SHARC (.sharc) - Sony Home Archive Resource Container
   - Specialized archive for STREAMING data (Audio/BGM).
   - Command: sharc extract / sharc create

5. PKG (.pkg) - PlayStation Package
   - The installer file format for PlayStation 3.
   - Command: pkg extract

6. XML (.xml) - Extensible Markup Language
   - Readable config files.
   - CRITICAL FOR OFFLINE: Edit these to remove 'http://' links and point to local files.

--------------------------------------------------
Quick Workflow Cheat Sheet
--------------------------------------------------
1. UNPACK: Use 'Extract' on a .pkg to get the .sdat.
2. UNLOCK: Use 'Extract' on the .sdat to get raw files.
3. DIG:    Use 'Extract' on any .bar files inside.
4. EDIT:   Modify .xml or .lua files.
5. REPACK: Use 'Create -> Pack SDAT' to build your playable scene.
6. PLAY:   Copy the new .sdat to RPCS3 USRDIR/SCENES/.
        """
        help_text.insert(tk.END, guide_content)
        help_text.config(state=tk.DISABLED)

    # =========================================================================
    # CORE RUNNER
    # =========================================================================
    def browse_hdk_exe(self):
        f = filedialog.askopenfilename(title="Locate hdk.exe", filetypes=[("Executable", "*.exe")])
        if f:
            self.hdk_path_var.set(f)
            self.log(f"HDK Binary manually set to: {f}")

    def select_project(self):
        path = filedialog.askdirectory()
        if path:
            self.project_path.set(path)
            self.log(f"Active Project set to: {path}")

    def _check_hdk_ready(self):
        path = self.hdk_path_var.get()
        if not path or not os.path.exists(path) or "NOT FOUND" in path:
            messagebox.showerror("Configuration Error", "HDK Binary not found!\n\nPlease click 'Change...' at the top and locate your compiled hdk.exe file.")
            return False
        return True

    def run_hdk_command(self, args, input_file=None):
        hdk_path = self.hdk_path_var.get()
        full_cmd = [hdk_path] + args
        self.log("-" * 60)
        self.log(f"RUNNING: {' '.join(args)}")
        
        def target():
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                stdin_val = subprocess.PIPE if input_file else None
                input_data = None

                if input_file:
                    self.log(f"Reading input file: {input_file}")
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
                
                try:
                    out_str = stdout.decode('utf-8', errors='ignore')
                    err_str = stderr.decode('utf-8', errors='ignore')
                except:
                    out_str = "[Binary Data]"
                    err_str = "[Binary Error]"

                if out_str.strip(): self.update_console(out_str)
                if err_str.strip(): self.update_console("LOG: " + err_str)

                if process.returncode == 0:
                    self.update_console("\n>>> SUCCESS <<<")
                else:
                    self.update_console(f"\n!!! FAILED (Code {process.returncode}) !!!")

            except Exception as e:
                self.update_console(f"CRITICAL ERROR: {str(e)}")

        threading.Thread(target=target, daemon=True).start()

    def log(self, msg):
        self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)

    def update_console(self, msg):
        self.after(0, lambda: self.log(msg.strip()))

if __name__ == "__main__":
    app = HDKCommander()
    app.mainloop()