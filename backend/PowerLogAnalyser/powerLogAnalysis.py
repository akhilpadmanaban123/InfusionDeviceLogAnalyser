from .batteryStatusDecoder import BatteryStatusSummarizer
import sys, os
import json , csv

"""
This code defines and uses a class called PowerLogAnalyzer to 
analyze chunks of battery power log data — particularly numeric parameters 
and bitfield status registers — and prints a readable summary for each chunk.
"""

parameter_definitions = {
    "SOH": {"min": 80, "max": 100, "unit": "%", "desc": "State of Health"},
    "Volt": {"min": 0, "max": 65535, "unit": "mV", "desc": "Battery voltage- This read-word function returns the sum of the measured cell voltages."},
    #.....  hidden due to confidentiality....These are available in battery manual bq40z50 battery manual
    "ChgrStatus" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/ChargerStatus.txt"},
    "GaugeStatus" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/GaugeStatus.txt"},
    "PFStatus" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/ProtectionFaultStatus.txt"},
    "PFAlert" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/ProtectionFaultAlert.txt"},
    "SafetyStatus" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/SafetyStatus.txt"},
    "SafetyAlert" : {"type": "bitfield", "file": "RAG_DATA/BitsDef/SafetyAlert.txt"},
}


class PowerLogAnalyzer:
    def __init__(self, parameter_defs):
        self.param_defs = parameter_defs
        self.bitfield_defs = self.load_bitfields()

    def load_bit_defs(self, path, bit_key):
        namespace = {}
        # Construct an absolute path from the project root
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', path)
        with open(full_path, "r") as f:
            exec(f.read(), {}, namespace)
        return namespace[bit_key]
    
    def load_bitfields(self):
        # Load hex to meaning mapping from your RAG_DATA text files
        return {
            "BattStatus": self.load_bit_defs("RAG_DATA/BitsDef/BatteryStatus.txt", "bit_defs"),
            "ChgrStatus": self.load_bit_defs("RAG_DATA/BitsDef/ChargerStatus.txt","charging_status_bit_defs"),
            "OperationalStatus": self.load_bit_defs("RAG_DATA/BitsDef/OperationalStatus.txt","operational_status_bit_defs"),
            "GaugeStatus": self.load_bit_defs("RAG_DATA/BitsDef/GaugeStatus.txt", "gauging_status_bit_defs"),
            "PFStatus": self.load_bit_defs("RAG_DATA/BitsDef/ProtectionFaultStatus.txt","pf_status_bit_defs"),
            "PFAlert": self.load_bit_defs("RAG_DATA/BitsDef/ProtectionFaultAlert.txt","pf_alert_bit_defs"),
            "SafetyStatus": self.load_bit_defs("RAG_DATA/BitsDef/SafetyStatus.txt","safety_status_bit_defs"),
            "SafetyAlert": self.load_bit_defs("RAG_DATA/BitsDef/SafetyAlert.txt","safety_alert_bit_defs"),
            }

    # This function analyzes numeric parameters, checking their values against defined min/max ranges.
    def analyze_numeric_param(self, name, values):
        param = self.param_defs.get(name, {})
        if not param or not values:
            return f"{name}: No data available"

        try:
            values = [float(v) for v in values if str(v).replace('.', '', 1).lstrip('-').isdigit()]
        except:
            return f"{name}: Invalid data format"

        if not values:
            return f"{name}: No valid numeric entries"

        unit = param.get("unit", "")
        defined_min = param.get("min", float('-inf'))
        defined_max = param.get("max", float('inf'))

        min_val = min(values)
        max_val = max(values)
        avg_val = round(sum(values) / len(values), 2)

        summary_parts = []

        # Special case: data is all zero  symbols are added for better readability
        if min_val == 0 and max_val == 0:
            summary_parts.append(f"min={min_val}❗")
            summary_parts.append(f"max={max_val}❗")
            summary_parts.append(f"avg={avg_val}❗")
            note = " (⚠️ Data may be missing or uninitialized)"
        else:
            # Append min with warning if needed
            if min_val < defined_min:
                summary_parts.append(f"min={min_val}⚠️")
            else:
                summary_parts.append(f"min={min_val}")

            # Append max with warning if needed
            if max_val > defined_max:
                summary_parts.append(f"max={max_val}⚠️")
            else:
                summary_parts.append(f"max={max_val}")

            # Append avg with warning if needed
            if avg_val < defined_min or avg_val > defined_max:
                summary_parts.append(f"avg={avg_val}⚠️")
            else:
                summary_parts.append(f"avg={avg_val}")
            note = ""

        return (
            f"{name}: {', '.join(summary_parts)} {unit} "
            f"(Expected: {defined_min}–{defined_max} {unit}){note}"
        ).strip()

    #This function analyzes bitfield parameters, decoding their hex values into human-readable meanings.
    def analyze_bitfield_param(self, name, values):
        unique = list(dict.fromkeys(values))
        results = []
        for hex_val in unique:
            try:
                decoded = BatteryStatusSummarizer.decode_hex_status(hex_val, self.bitfield_defs[name])
                results.append(f"{hex_val} → " + "; ".join(decoded))
            except Exception as e:
                results.append(f"{hex_val} → Error decoding: {str(e)}")
        return f"{name}: " + " | ".join(results)

    # This function checks if the data is numeric or bitfield, and then calls the appropriate analysis function.
    def analyze_chunk(self, chunk):
        analysis = []
        for param in chunk:
            if param not in self.param_defs:
                continue

            values = chunk[param] if isinstance(chunk[param], list) else [chunk[param]]
            if self.param_defs[param].get("type") == "bitfield":
                analysis.append(self.analyze_bitfield_param(param, values))
            else:
                analysis.append(self.analyze_numeric_param(param, values))
        
        return "\n".join(a for a in analysis if a)

def get_parameter_definitions():
    analyzer = PowerLogAnalyzer(parameter_definitions)
    return parameter_definitions, analyzer.bitfield_defs

def analyze_power_log(chunks_file_path):
    if not os.path.exists(chunks_file_path):
        return f"Error: chunks.json not found at {chunks_file_path}"

    with open(chunks_file_path) as f:
        chunks = json.load(f)

    analyzer = PowerLogAnalyzer(parameter_definitions)

    output_txt = os.path.join(os.path.dirname(chunks_file_path), "powerchunk_analysis_summary.txt")
    
    analysis_results = []
    with open(output_txt, "w", encoding='utf-8') as f:
        for chunk in chunks:
            summary = analyzer.analyze_chunk(chunk)
            analysis_results.append(f"🧩 ChunkID: {chunk['ChunkID']}\n\n")
            analysis_results.append(summary.strip() + "\n\n")
            analysis_results.append("-" * 60 + "\n\n")
            
            f.write(f"🧩 ChunkID: {chunk['ChunkID']}\n\n")
            f.write(summary.strip() + "\n\n")
            f.write("-" * 60 + "\n\n")

    return "\n".join(analysis_results)

# Remove the direct execution block
# if __name__ == '__main__':
#     # This block will no longer be executed when imported as a module
#     # You can add test code here if needed, but it won't run when imported.
#     pass
