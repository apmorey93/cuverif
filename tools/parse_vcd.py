"""
VCD Parser for VCS Equivalence Testing
========================================

Parses VCD output from VCS and extracts signal traces for comparison.
"""

import re
import json
from collections import defaultdict

class VCDParser:
    """Simple VCD parser - extracts signal values per cycle."""
    
    def __init__(self, vcd_path):
        self.vcd_path = vcd_path
        self.signals = {}  # {symbol: signal_name}
        self.traces = defaultdict(list)  # {signal_name: [(time, value)]}
        
    def parse(self):
        """Parse VCD file and extract traces."""
        with open(self.vcd_path, 'r') as f:
            lines = f.readlines()
        
        in_definitions = True
        current_time = 0
        
        for line in lines:
            line = line.strip()
            
            # Parse variable definitions
            if line.startswith('$var'):
                # $var wire 1 ! clk $end
                parts = line.split()
                if len(parts) >= 5:
                    symbol = parts[3]
                    name = parts[4]
                    self.signals[symbol] = name
                    
            elif line.startswith('$enddefinitions'):
                in_definitions = False
                
            elif not in_definitions:
                # Time marker
                if line.startswith('#'):
                    current_time = int(line[1:])
                    
                # Value change: "0!" means signal ! changed to 0
                elif len(line) >= 2:
                    value_char = line[0]
                    symbol = line[1:]
                    
                    if symbol in self.signals:
                        signal_name = self.signals[symbol]
                        # Map VCD chars to our format
                        if value_char in ['0', '1']:
                            value = value_char
                        elif value_char in ['x', 'X']:
                            value = 'X'
                        elif value_char in ['z', 'Z']:
                            value = 'Z'
                        else:
                            value = 'X'
                        
                        self.traces[signal_name].append((current_time, value))
        
        return self.traces
    
    def to_cycle_dict(self, cycle_period=10):
        """
        Convert time-based traces to cycle-based dictionary.
        
        Args:
            cycle_period: ns per cycle (default 10)
            
        Returns:
            List of {cycle: N, signals: {sig: value}}
        """
        traces = self.parse()
        
        # Find max time
        max_time = 0
        for signal_traces in traces.values():
            if signal_traces:
                max_time = max(max_time, signal_traces[-1][0])
        
        num_cycles = (max_time // cycle_period) + 1
        
        # Build cycle dict
        result = []
        for cycle in range(num_cycles):
            cycle_time = cycle * cycle_period
            signal_values = {}
            
            for sig_name, sig_traces in traces.items():
                # Find value at this cycle time
                value = 'X'
                for time, val in sig_traces:
                    if time <= cycle_time:
                        value = val
                    else:
                        break
                signal_values[sig_name] = value
            
            result.append({
                "cycle": cycle,
                "signals": signal_values
            })
        
        return result

def parse_vcd_to_json(vcd_path, output_path, cycle_period=10):
    """Parse VCD and save to JSON format matching CuVerif trace."""
    parser = VCDParser(vcd_path)
    trace = parser.to_cycle_dict(cycle_period)
    
    with open(output_path, 'w') as f:
        json.dump(trace, f, indent=2)
    
    print(f"Parsed {len(trace)} cycles from {vcd_path}")
    print(f"Saved to {output_path}")
    
    # Show first few cycles
    print("\nFirst 5 cycles:")
    for t in trace[:5]:
        print(f"  Cycle {t['cycle']}: {t['signals']}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        vcd_file = sys.argv[1]
        json_file = sys.argv[2] if len(sys.argv) > 2 else "tools/trace_vcs.json"
    else:
        vcd_file = "tools/dummy_vcs.vcd"
        json_file = "tools/trace_vcs.json"
    
    parse_vcd_to_json(vcd_file, json_file)
