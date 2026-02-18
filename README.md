# 🛠️ HDK Commander (GUI)

**The ultimate "All-in-One" toolkit for PlayStation Home restoration, modding, and preservation.**

> **Note:** This is a graphical interface (GUI) for the powerful [hdk-cli](https://github.com/ZephyrCodesStuff/hdk-cli). It allows you to extract, modify, and repack PlayStation Home files without touching a command line.

![HDK Commander Dashboard](https://via.placeholder.com/800x400?text=HDK+Commander+Dashboard)

## 📖 Overview

**HDK Commander** streamlines the complex workflow of editing PlayStation Home scenes. It allows users to turn "Online-Only" scenes (which crash RPCS3) into "Local Offline" scenes that load instantly from the hard drive.

**Key Features:**
* **📦 Smart Extraction:** Auto-detects and unpacks `.pkg`, `.sdat`, `.bar`, and `.sharc` files.
* **🔧 Map & Restore:** Uses regex to rename "hashed" files (e.g., `0a1b2c...`) back to their original human-readable names so you can edit them.
* **💾 One-Click Repacking:** Turns your modified folders back into playable `.sdat` files.
* **🚀 Auto-Optimization:** Optional "Smart Compress" feature uses EdgeZLib to shrink your repacked scenes (often reducing size by 60%+).
* **📚 Built-in Encyclopedia:** Integrated documentation on what every PS Home file type actually does.

---

## ⚡ Quick Start (The "Easy" Way)

We have included a setup script that handles everything for you (installing Rust, downloading the engine, and building the tool).

### Prerequisites
1.  **Windows 10/11**
2.  **[Python 3.x](https://www.python.org/downloads/)** (Make sure to check "Add Python to PATH" during install)
3.  **[Git](https://git-scm.com/downloads)**
4.  **Rust**

### Installation
1.  Download and unzip this repository.
2.  Double-click **`setup.bat`**.
    * *What this does:* It checks if you have Rust as well as other assets installed. If not, it installs it. Then, it downloads the latest `hdk-cli` source code and compiles it specially for your machine.
3.  Once the setup finishes, launch **`hdk_launcher.py`**.

---

## ⚙️ Configuration

**HDK Commander** uses a "Smart Path" system. It will automatically attempt to find the `hdk.exe` binary in the following order:
1.  **Manual Selection:** The path you set via the GUI.
2.  **Portable Mode:** Checks if `hdk.exe` is in the same folder as the script.
3.  **Standard Build:** Checks the `./hdk-cli/target/release/` folder (created by `setup.bat`).

**If the tool says "HDK BINARY NOT FOUND":**
1.  Click the **"Change..."** button at the top of the app.
2.  Navigate to where you compiled `hdk.exe`.
3.  Select it in order to tell Commander where your `hdk.exe` is.

---

## 🎮 Workflow: How to Make Scenes Playable Offline

This is the standard workflow for the **Destination Home** project.

### Step 1: Extract & Clean
1.  Open HDK Commander.
2.  Go to the **Extract** tab.
3.  Select your target file (e.g., `Marketplace.sdat`).
4.  Once extracted, go to **Advanced Tools** -> **Map Directory**.
5.  Select your new extracted folder. This renames the internal files so the game can read them.

### Step 2: The "Offline Patch"
1.  Open the extracted folder.
2.  Find the Scene Config XML (usually named `SCENEID_en-US.xml` or similar).
3.  Open it in **Notepad** or **VS Code**.
4.  **Find and Replace:**
    * **Find:** `https://cdn.destinationhome.live/` (or any http link).
    * **Replace with:** `local:USRDIR/`
5.  Save the file.

### Step 3: Repack
1.  Go to the **Create & Pack** tab.
2.  **Check the box:** `[x] Auto-Optimize (Compress Assets)`.
    * *Note: This makes the file much smaller but takes longer to build.*
3.  Click **Pack Folder -> .SDAT**.
4.  Select your project folder (the one containing `USRDIR`).
5.  Save your new `.sdat` file.

### Step 4: Install to RPCS3
1.  Move your new `.sdat` to: `\dev_hdd0\game\NPIA00010\USRDIR\SCENES\`
2.  Register it in `scenes_offline.xml`.
3.  Launch Destination Home!

---

## 🛠️ Advanced Tools

* **PKG Inspector:** View the Content ID, Region, and file list of a `.pkg` without extracting it.
* **Raw Decrypt:** If you have a loose config file (not in an SDAT) that looks like gibberish, use this to decrypt it.
* **Batch Compression:** You can use the "Compression Utilities" to manually shrink specific `.bar` or `.havok` files.

---

## 🤝 Credits

* **HDK Commander (GUI):** [JuliusJoker]
* **hdk-cli (Core Logic):** [ZephyrCodesStuff](https://github.com/ZephyrCodesStuff/hdk-cli)

## 📄 License
This GUI is open-source.
The underlying `hdk-cli` is licensed under **AGPL-3.0**.