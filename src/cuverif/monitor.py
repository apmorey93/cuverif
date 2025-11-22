import matplotlib.pyplot as plt
import numpy as np

class Monitor:
    """
    Utility class to sample and visualize signal history.
    Now supports full 4-state visualization with distinct rendering for X states.
    """
    def __init__(self, signals, instance_id=0):
        self.signals = signals
        self.instance_id = instance_id
        # History stores plot-ready values (0.0, 0.5, or 1.0)
        self.history = {k: [] for k in signals} 
        self.time = []
        self.cycle = 0

    def sample(self):
        """
        Samples the current state of all monitored signals.
        Maps V/S pairs to plot values: 0→0.0, 1→1.0, X/Z→0.5
        """
        self.time.append(self.cycle)
        for k, tensor in self.signals.items():
            # Fetch both V and S arrays from GPU
            v_val = tensor.v_data.copy_to_host()[self.instance_id]
            s_val = tensor.s_data.copy_to_host()[self.instance_id]
            
            # Encoding for plotting:
            # If Strength is 0 (X or Z), map to 0.5 (middle line)
            # Else, use the Value bit (0 or 1)
            plot_val = float(v_val) if s_val == 1 else 0.5
            
            self.history[k].append(plot_val)
            
        self.cycle += 1

    def plot(self):
        """
        Generates a digital waveform plot with 4-state visualization.
        - Valid states (0, 1) shown in green
        - Invalid states (X, Z) shown at 0.5 level with red markers
        """
        num_signals = len(self.signals)
        fig, axes = plt.subplots(num_signals, 1, figsize=(12, 2 * num_signals), sharex=True)
        
        if num_signals == 1:
            axes = [axes]
            
        for i, (name, vals) in enumerate(self.history.items()):
            ax = axes[i]
            vals_arr = np.array(vals)
            
            # Draw the main waveform in green
            ax.step(self.time, vals, where='post', color='#00AA00', linewidth=2)
            
            # Highlight X states (value 0.5) with red markers
            is_x = (vals_arr == 0.5)
            if is_x.any():
                x_times = np.array(self.time)[is_x]
                x_vals = vals_arr[is_x]
                ax.plot(x_times, x_vals, 'ro', markersize=6, label='X/Z')
                ax.legend(loc='upper right', fontsize=8)
            
            # Set y-axis to show 3 levels
            ax.set_yticks([0, 0.5, 1])
            ax.set_yticklabels(['0', 'X', '1'])
            ax.set_ylim(-0.1, 1.1)
            ax.set_ylabel(name, rotation=0, ha='right', fontsize=10)
            ax.grid(axis='x', linestyle='--', alpha=0.5)
            
        axes[-1].set_xlabel("Time (Cycles)", fontsize=10)
        fig.suptitle("4-State Logic Waveform Trace", fontsize=14, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

    def export_vcd(self, filename="wave.vcd"):
        """
        Exports the recorded history to a VCD (Value Change Dump) file.
        This allows viewing waveforms in standard EDA tools like Verdi or GTKWave.
        
        Maps internal states to VCD values:
        - 0.0 -> '0'
        - 1.0 -> '1'
        - 0.5 -> 'x' (Unknown)
        """
        print(f"Exporting Instance {self.instance_id} to {filename}...")
        with open(filename, "w") as f:
            # Header
            import datetime
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"$date\n  {date_str}\n$end\n")
            f.write("$version\n  CuVerif GPU Simulator\n$end\n")
            f.write("$timescale\n  1ns\n$end\n")
            f.write("$scope module top $end\n")
            
            # Define Variables
            symbols = {}
            # Generate simple ASCII symbols (!, ", #, etc.)
            for i, name in enumerate(self.signals.keys()):
                sym = chr(33 + i) 
                symbols[name] = sym
                # Define as 1-bit wire
                f.write(f"$var wire 1 {sym} {name} $end\n")
            
            f.write("$upscope $end\n")
            f.write("$enddefinitions $end\n")
            
            # Dump Data
            # Write initial values at time 0
            f.write("#0\n")
            for name, vals in self.history.items():
                if not vals: continue
                
                val = vals[0]
                sym = symbols[name]
                
                # Map float 0.5 -> X for VCD
                vcd_val = 'x'
                if val == 0.0: vcd_val = '0'
                elif val == 1.0: vcd_val = '1'
                
                f.write(f"{vcd_val}{sym}\n")
                
            # Write changes
            for t in range(1, len(self.time)):
                timestamp = self.time[t] * 10 # Scale cycles to ns (10ns period)
                f.write(f"#{timestamp}\n")
                
                for name, vals in self.history.items():
                    val = vals[t]
                    prev_val = vals[t-1]
                    
                    # Only write if value changed
                    if val != prev_val:
                        sym = symbols[name]
                        vcd_val = 'x'
                        if val == 0.0: vcd_val = '0'
                        elif val == 1.0: vcd_val = '1'
                        
                        f.write(f"{vcd_val}{sym}\n")
