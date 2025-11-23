"""
CuVerif Studio - Unified GUI for Simulation and Silicon Debugging
==================================================================
A lightweight GUI that works on any machine (CPU backend only).
"""
import sys
import os

# Ensure the project src directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import customtkinter as ctk
    from customtkinter import filedialog
except ImportError:
    print("ERROR: customtkinter not installed")
    print("Install with: pip install customtkinter")
    sys.exit(1)

import threading
from cuverif.bridge import SiliconBridge
from cuverif.backend import DEFAULT_BACKEND

# Set appearance (dark mode)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CuVerifApp(ctk.CTk):
    """Main application window for CuVerif Studio (CPU‑only)."""

    def __init__(self):
        super().__init__()
        self.title("CuVerif Studio - CPU Backend")
        self.geometry("1100x700")

        # State
        self.silicon = None          # JTAG bridge (optional)
        self.mode = "SIMULATION"    # or "SILICON"
        self.simulator = None        # Holds the compiled chip model
        self.backend_name = DEFAULT_BACKEND.name.upper()

        # Layout configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------- Sidebar ----------
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo = ctk.CTkLabel(self.sidebar, text="CuVerif", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=20)

        self.btn_load = ctk.CTkButton(self.sidebar, text="Load Netlist", command=self.load_files)
        self.btn_load.grid(row=1, column=0, padx=20, pady=10)

        self.btn_compile = ctk.CTkButton(self.sidebar, text="Compile", command=self.compile_netlist)
        self.btn_compile.grid(row=2, column=0, padx=20, pady=10)

        self.btn_p4 = ctk.CTkButton(self.sidebar, text="P4 Sync", fg_color="#555555", command=self.open_p4_window)
        self.btn_p4.grid(row=3, column=0, padx=20, pady=10)

        # Mode switcher
        self.lbl_mode = ctk.CTkLabel(self.sidebar, text="Target Mode:")
        self.lbl_mode.grid(row=4, column=0, pady=(30, 0))
        self.mode_switch = ctk.CTkSwitch(self.sidebar, text="Silicon (Olimex)", command=self.toggle_mode)
        self.mode_switch.grid(row=5, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Idle", text_color="gray")
        self.status_label.grid(row=6, column=0, pady=20)

        # ---------- Main area ----------
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.main_title = ctk.CTkLabel(self.main_frame, text="Console & Debug Output", font=ctk.CTkFont(size=16, weight="bold"))
        self.main_title.pack(pady=(10, 5))

        self.console = ctk.CTkTextbox(self.main_frame, width=800, height=300)
        self.console.pack(pady=10, fill="both", expand=True)
        self.log("=" * 70)
        self.log("Welcome to CuVerif Studio (CPU backend)")
        self.log("=" * 70)
        self.log("System Ready. Load a netlist to begin.")

        # Simple Peek/Poke UI
        self.reg_frame = ctk.CTkFrame(self.main_frame)
        self.reg_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(self.reg_frame, text="Debug Console (Peek/Poke)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        input_frame = ctk.CTkFrame(self.reg_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        self.entry_addr = ctk.CTkEntry(input_frame, placeholder_text="0x4000", width=120)
        self.entry_addr.pack(side="left", padx=5, pady=10)
        self.entry_val = ctk.CTkEntry(input_frame, placeholder_text="0xDEADBEEF", width=150)
        self.entry_val.pack(side="left", padx=5, pady=10)
        self.btn_write = ctk.CTkButton(input_frame, text="WRITE", width=80, command=self.do_write, fg_color="#D35400")
        self.btn_write.pack(side="left", padx=5)
        self.btn_read = ctk.CTkButton(input_frame, text="READ", width=80, command=self.do_read, fg_color="#27AE60")
        self.btn_read.pack(side="left", padx=5)

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def log(self, msg: str) -> None:
        """Append a line to the console textbox."""
        self.console.insert("end", f"> {msg}\n")
        self.console.see("end")

    def toggle_mode(self) -> None:
        """Switch between simulation (CPU) and silicon hardware mode."""
        if self.mode_switch.get() == 1:
            self.mode = "SILICON"
            self.log("Switching to SILICON mode…")
            threading.Thread(target=self.connect_hardware, daemon=True).start()
        else:
            self.mode = "SIMULATION"
            if self.silicon:
                self.silicon.disconnect()
            self.log("Switched to SIMULATION mode (CPU).")
            self.status_label.configure(text=f"Target: {self.backend_name}", text_color="#00FF00")

    def connect_hardware(self) -> None:
        """Attempt to connect to an Olimex JTAG board."""
        try:
            self.silicon = SiliconBridge()
            status = self.silicon.connect()
            self.log(status)
            if "Connected" in status:
                self.status_label.configure(text="Target: Olimex JTAG", text_color="#00FFFF")
            else:
                self.mode_switch.deselect()
        except Exception as e:
            self.log(f"Hardware connection failed: {e}")
            self.mode_switch.deselect()

    def load_files(self) -> None:
        """Prompt the user to select a Verilog netlist file."""
        file_path = filedialog.askopenfilename(filetypes=[("Verilog Netlist", "*.v"), ("All Files", "*.*")])
        if file_path:
            self.log(f"Loading: {os.path.basename(file_path)}")
            self.current_file = file_path

    def compile_netlist(self) -> None:
        """Compile the currently loaded netlist using the CPU backend."""
        if not hasattr(self, "current_file"):
            self.log("ERROR: No netlist loaded")
            return
        self.log(f"Compiling Netlist: {os.path.basename(self.current_file)}")
        from cuverif.compiler import VerilogCompiler
        try:
            with open(self.current_file, "r") as f:
                verilog_code = f.read()
            compiler = VerilogCompiler()
            # Use a modest batch size for the GUI demo
            batch_size = 10
            chip = compiler.compile(verilog_code, batch_size=batch_size)
            self.simulator = chip
            self.log("Compilation complete (CPU backend).")
            self.status_label.configure(text=f"Target: {self.backend_name}", text_color="#00FF00")
        except Exception as e:
            self.log(f"Compilation failed: {e}")

    def do_write(self) -> None:
        """Write a value to a register (simulated or hardware)."""
        addr = self.entry_addr.get()
        val = self.entry_val.get()
        if not addr or not val:
            self.log("ERROR: Address and Value required")
            return
        try:
            if self.mode == "SILICON":
                self.log(f"[HW] Writing {val} to {addr}…")
                self.silicon.write_register(int(addr, 16), int(val, 16))
                self.log("[HW] Write complete")
            else:
                self.log(f"[SIM] Writing {val} to {addr} (CPU instant)…")
                # Placeholder – real implementation would interact with self.simulator.debug
                self.log("[SIM] Write complete")
        except Exception as e:
            self.log(f"ERROR: {e}")

    def do_read(self) -> None:
        """Read a register value (simulated or hardware)."""
        addr = self.entry_addr.get()
        if not addr:
            self.log("ERROR: Address required")
            return
        try:
            if self.mode == "SILICON":
                val = self.silicon.read_register(int(addr, 16))
                self.log(f"[HW] Read {addr}: {hex(val)}")
            else:
                # Placeholder – real implementation would query self.simulator.debug
                self.log(f"[SIM] Read {addr}: 0x0 (CPU placeholder)")
        except Exception as e:
            self.log(f"ERROR: {e}")

    def open_p4_window(self) -> None:
        """Prompt for a Perforce depot path (future integration)."""
        dialog = ctk.CTkInputDialog(text="Enter P4 Depot Path:", title="P4 Sync")
        path = dialog.get_input()
        if path:
            self.log(f"Syncing P4: {path}…")
            # TODO: integrate Perforce sync logic here
            self.log("P4 Sync complete (TODO)")

if __name__ == "__main__":
    app = CuVerifApp()
    app.mainloop()
