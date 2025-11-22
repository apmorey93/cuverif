"""
CuVerif Studio - Unified GUI for Simulation and Silicon Debugging
==================================================================
Modern dark-mode interface that bridges GPU simulation and physical hardware.

Usage:
    python src/gui_app.py

Requirements:
    pip install customtkinter pyftdi p4python
"""

import sys
import os

# Add src to path
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

# Set appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CuVerifApp(ctk.CTk):
    """
    Main application window for CuVerif Studio.
    Provides unified interface for both simulation and hardware debugging.
    """
    def __init__(self):
        super().__init__()

        self.title("CuVerif Studio - GPU & Silicon Debugger")
        self.geometry("1100x700")
        
        # State
        self.silicon = None  # Will be initialized if hardware mode is selected
        self.mode = "SIMULATION"  # or "SILICON"
        self.simulator = None  # Will hold the CuVerif simulation instance

        # --- LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(
            self.sidebar, 
            text="CuVerif", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo.grid(row=0, column=0, padx=20, pady=20)
        
        self.btn_load = ctk.CTkButton(
            self.sidebar, 
            text="Load Netlist", 
            command=self.load_files
        )
        self.btn_load.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_p4 = ctk.CTkButton(
            self.sidebar, 
            text="P4 Sync", 
            fg_color="#555555", 
            command=self.open_p4_window
        )
        self.btn_p4.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_compile = ctk.CTkButton(
            self.sidebar,
            text="Compile",
            command=self.compile_netlist
        )
        self.btn_compile.grid(row=3, column=0, padx=20, pady=10)

        # Mode Switcher
        self.lbl_mode = ctk.CTkLabel(self.sidebar, text="Target Mode:")
        self.lbl_mode.grid(row=8, column=0, pady=(40,0))
        
        self.mode_switch = ctk.CTkSwitch(
            self.sidebar, 
            text="Silicon (Olimex)", 
            command=self.toggle_mode
        )
        self.mode_switch.grid(row=9, column=0, padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(
            self.sidebar, 
            text="Status: Idle", 
            text_color="gray"
        )
        self.status_label.grid(row=10, column=0, pady=20)

        # 2. MAIN AREA
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Title
        self.main_title = ctk.CTkLabel(
            self.main_frame,
            text="Console & Debug Output",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.main_title.pack(pady=(10, 5))
        
        # Console / Logs
        self.console = ctk.CTkTextbox(self.main_frame, width=800, height=300)
        self.console.pack(pady=10, fill="both", expand=True)
        self.log("=" * 70)
        self.log("Welcome to CuVerif Studio")
        self.log("=" * 70)
        self.log("System Ready. Select a Netlist or Connect Hardware.")

        # Register Peek/Poke Dashboard
        self.reg_frame = ctk.CTkFrame(self.main_frame)
        self.reg_frame.pack(pady=10, fill="x")
        
        ctk.CTkLabel(
            self.reg_frame, 
            text="Debug Console (Peek/Poke)",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Input frame
        input_frame = ctk.CTkFrame(self.reg_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        self.entry_addr = ctk.CTkEntry(
            input_frame, 
            placeholder_text="0x4000",
            width=120
        )
        self.entry_addr.pack(side="left", padx=5, pady=10)
        
        self.entry_val = ctk.CTkEntry(
            input_frame, 
            placeholder_text="0xDEADBEEF",
            width=150
        )
        self.entry_val.pack(side="left", padx=5, pady=10)
        
        self.btn_write = ctk.CTkButton(
            input_frame, 
            text="WRITE", 
            width=80, 
            command=self.do_write,
            fg_color="#D35400"
        )
        self.btn_write.pack(side="left", padx=5)
        
        self.btn_read = ctk.CTkButton(
            input_frame, 
            text="READ", 
            width=80, 
            command=self.do_read,
            fg_color="#27AE60"
        )
        self.btn_read.pack(side="left", padx=5)

    # --- ACTIONS ---

    def log(self, msg):
        """Add message to console"""
        self.console.insert("end", f"> {msg}\n")
        self.console.see("end")

    def toggle_mode(self):
        """Switch between simulation and silicon modes"""
        if self.mode_switch.get() == 1:
            self.mode = "SILICON"
            self.log("Switching to SILICON Mode...")
            # Threaded connect to avoid freezing GUI
            threading.Thread(target=self.connect_hardware, daemon=True).start()
        else:
            self.mode = "SIMULATION"
            if self.silicon:
                self.silicon.disconnect()
            self.log("Switched to SIMULATION Mode (GPU).")
            self.status_label.configure(
                text="Target: GPU H100", 
                text_color="#00FF00"
            )

    def connect_hardware(self):
        """Connect to physical JTAG hardware"""
        try:
            self.silicon = SiliconBridge()
            status = self.silicon.connect()
            self.log(status)
            if "Connected" in status:
                self.status_label.configure(
                    text="Target: Olimex JTAG", 
                    text_color="#00FFFF"
                )
            else:
                self.mode_switch.deselect()  # Fallback to simulation
        except Exception as e:
            self.log(f"Hardware connection failed: {e}")
            self.mode_switch.deselect()

    def do_write(self):
        """Execute register write"""
        addr = self.entry_addr.get()
        val = self.entry_val.get()
        
        if not addr or not val:
            self.log("ERROR: Address and Value required")
            return
        
        try:
            if self.mode == "SILICON":
                self.log(f"[HW] Writing {val} to {addr}...")
                self.silicon.write_register(int(addr, 16), int(val, 16))
                self.log(f"[HW] Write complete")
            else:
                self.log(f"[SIM] Writing {val} to {addr} (GPU Instant)...")
                # Call self.simulator.debug.write(...) here
                if self.simulator:
                    # self.simulator.debug.write(addr, val)
                    pass
                self.log(f"[SIM] Write complete")
        except Exception as e:
            self.log(f"ERROR: {e}")
            
    def do_read(self):
        """Execute register read"""
        addr = self.entry_addr.get()
        
        if not addr:
            self.log("ERROR: Address required")
            return
            
        try:
            if self.mode == "SILICON":
                val = self.silicon.read_register(int(addr, 16))
                self.log(f"[HW] Read {addr}: {hex(val)}")
            else:
                # val = self.simulator.debug.read(...)
                self.log(f"[SIM] Read {addr}: 0x0 (Sim Placeholder)")
                if self.simulator:
                    # val = self.simulator.debug.read(addr)
                    pass
        except Exception as e:
            self.log(f"ERROR: {e}")

    def load_files(self):
        """Load Verilog netlist file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Verilog Netlist", "*.v"), ("All Files", "*.*")]
        )
        if file_path:
            self.log(f"Loading: {os.path.basename(file_path)}")
            self.current_file = file_path
            # Store for compilation

    def compile_netlist(self):
        """Compile loaded netlist to CuVerif model"""
        if not hasattr(self, 'current_file'):
            self.log("ERROR: No netlist loaded")
            return
            
        self.log(f"Compiling Netlist: {os.path.basename(self.current_file)}")
        # from cuverif.compiler import NetlistCompiler
        # compiler = NetlistCompiler()
        # compiler.parse_file(self.current_file)
        # python_code = compiler.generate_python()
        self.log("Compilation complete (TODO: integrate compiler)")

    def open_p4_window(self):
        """Open P4 sync dialog"""
        dialog = ctk.CTkInputDialog(
            text="Enter P4 Depot Path:", 
            title="P4 Sync"
        )
        path = dialog.get_input()
        if path:
            self.log(f"Syncing P4: {path}...")
            # from cuverif.p4_manager import SourceControl
            # p4 = SourceControl()
            # result = p4.sync_path(path)
            self.log(f"P4 Sync complete (TODO: integrate P4)")

if __name__ == "__main__":
    app = CuVerifApp()
    app.mainloop()
