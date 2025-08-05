import os, csv
import uuid
import json
from datetime import datetime

# --- Config ---

COLUMNS = [
    #confidential
]

class PowerLogChunker:
    def __init__(self, powerlog_file, device_name, columns):
        self.powerlog_file = powerlog_file
        self.device_name = device_name
        self.columns = columns

    def is_valid_data_line(self, line):
        parts = line.strip().split(",")
        if len(parts) < 10:
            return False
        try:
            datetime.strptime(parts[0], "%m/%d/%Y %H:%M:%S")
            return True
        except:
            return False

    def parse_line(self, line):
        parts = line.strip().split(",")
        dt = datetime.strptime(parts[0], "%m/%d/%Y %H:%M:%S")
        values = parts[1:] + [""] * (len(self.columns) - len(parts[2:]))
        data = dict(zip(self.columns, values))
        data["datetime"] = dt
        data["BattPres"] = data.get("BattPresent", "")
        data["PowerSrc"] = data.get("PowerSrc", "")
        return data

    def simplify_chunk_fields(self, chunk):
        simplified = {}
        for key, value in chunk.items():
            if isinstance(value, list):
                if key == "Perc_Time_Series": # Do not simplify Perc_Time_Series
                    simplified[key] = value
                else:
                    unique_values = set(value)
                    simplified[key] = value[0] if len(unique_values) == 1 else value
            else:
                simplified[key] = value
        return simplified

    def serialize_chunks(self, chunks):
        def serialize_chunk(chunk):
            new_chunk = {}
            for k, v in chunk.items():
                if isinstance(v, datetime):
                    new_chunk[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(v, list):
                    if k == "Perc_Time_Series":
                        new_chunk[k] = [
                            {"value": item["value"], "time": item["time"].strftime("%Y-%m-%d %H:%M:%S")}
                            for item in v
                        ]
                    else:
                        new_chunk[k] = [
                            x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, datetime) else x
                            for x in v
                        ]
                else:
                    new_chunk[k] = v
            return new_chunk
        return [serialize_chunk(chunk) for chunk in chunks]

    def chunk_logs(self, lines):
        chunks = []
        current_chunk = None
        start_time = None
        prev_battpres = None
        prev_powersrc = None

        for line in lines:
            if not self.is_valid_data_line(line):
                if current_chunk:
                    end_time = current_chunk["_last_time"]
                    current_chunk["EndDate"] = end_time.strftime("%m/%d/%Y")
                    current_chunk["EndTime"] = end_time.strftime("%H:%M:%S")
                    current_chunk["TotalTime"] = str(end_time - start_time)
                    del current_chunk["_last_time"]
                    chunks.append(self.simplify_chunk_fields(current_chunk))
                    current_chunk = None
                    prev_battpres = None
                    prev_powersrc = None
                continue

            record = self.parse_line(line)
            batt_pres = record["BattPres"]
            power_src = record["PowerSrc"]

            if current_chunk is None:
                start_time = record["datetime"]
                current_chunk = {
                    "ChunkID": str(uuid.uuid4()),
                    "StartDate": start_time.strftime("%m/%d/%Y"),
                    "StartTime": start_time.strftime("%H:%M:%S"),
                    "BattPres": batt_pres,
                    "PowerSrc": power_src,
                    "_last_time": record["datetime"],
                    "Perc_Time_Series": [] # Always initialize Perc_Time_Series
                }
                for col in self.columns:
                    if col not in ["PowerSrc", "BattPres"]:
                        current_chunk[col] = [record.get(col, "")]
                # Store Perc with its timestamp
                if "Perc" in self.columns:
                    current_chunk["Perc_Time_Series"].append({"value": record.get("Perc", ""), "time": record["datetime"]})
                prev_battpres = batt_pres
                prev_powersrc = power_src
                continue

            state_changed = (
                (batt_pres != prev_battpres) or
                (power_src != prev_powersrc) or
                (record["datetime"].date() != start_time.date())
            )

            if state_changed:
                end_time = current_chunk["_last_time"]
                current_chunk["EndDate"] = end_time.strftime("%m/%d/%Y")
                current_chunk["EndTime"] = end_time.strftime("%H:%M:%S")
                current_chunk["TotalTime"] = str(end_time - start_time)
                del current_chunk["_last_time"]
                chunks.append(self.simplify_chunk_fields(current_chunk))

                start_time = record["datetime"]
                current_chunk = {
                    "ChunkID": str(uuid.uuid4()),
                    "StartDate": start_time.strftime("%m/%d/%Y"),
                    "StartTime": start_time.strftime("%H:%M:%S"),
                    "BattPres": batt_pres,
                    "PowerSrc": power_src,
                    "_last_time": record["datetime"],
                }
                for col in self.columns:
                    if col not in ["PowerSrc", "BattPres"]:
                        current_chunk[col] = [record.get(col, "")]
                prev_battpres = batt_pres
                prev_powersrc = power_src
            else:
                for col in self.columns:
                    if col not in ["PowerSrc", "BattPres"]:
                        current_chunk[col].append(record.get(col, ""))
                # Ensure Perc_Time_Series exists before appending
                current_chunk.setdefault("Perc_Time_Series", [])
                # Store Perc with its timestamp
                if "Perc" in self.columns:
                    current_chunk["Perc_Time_Series"].append({"value": record.get("Perc", ""), "time": record["datetime"]})
                current_chunk["_last_time"] = record["datetime"]

        if current_chunk:
            end_time = current_chunk["_last_time"]
            current_chunk["EndDate"] = end_time.strftime("%m/%d/%Y")
            current_chunk["EndTime"] = end_time.strftime("%H:%M:%S")
            current_chunk["TotalTime"] = str(end_time - start_time)
            del current_chunk["_last_time"]
            chunks.append(self.simplify_chunk_fields(current_chunk))

        return chunks

    def save_chunk_summary_table(self, chunks, output_dir):
        summary_file = os.path.join(output_dir, f"chunk_summary_{self.device_name}.csv")
        with open(summary_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ChunkID", "StartDate", "StartTime", "EndDate", "EndTime", 
                "TotalTime", "BattPres", "PowerSrc"
            ])
            for chunk in chunks:
                writer.writerow([
                    chunk.get("ChunkID"),
                    chunk.get("StartDate"),
                    chunk.get("StartTime"),
                    chunk.get("EndDate"),
                    chunk.get("EndTime"),
                    chunk.get("TotalTime"),
                    chunk.get("BattPres"),
                    chunk.get("PowerSrc"),
                ])
        print(f" Summary table saved to {summary_file}")


    def save_chunks_to_json(self, chunks, output_dir):
        filename = os.path.join(output_dir, f"chunks_{self.device_name}.json")
        serializable_chunks = self.serialize_chunks(chunks)
        with open(filename, "w") as f:
            json.dump(serializable_chunks, f, indent=2)
        print(f"{len(chunks)} chunks saved to {filename}")
        return filename

def generate_chunks(powerlog_file_path, output_dir, device_name):
    if not os.path.exists(powerlog_file_path):
        print(f"File '{powerlog_file_path}' not found.")
        return None

    chunker = PowerLogChunker(powerlog_file_path, device_name, COLUMNS)

    with open(powerlog_file_path, "r") as f:
        lines = f.readlines()

    chunks = chunker.chunk_logs(lines)
    json_file_path = chunker.save_chunks_to_json(chunks, output_dir)
    chunker.save_chunk_summary_table(chunks, output_dir)
    
    return json_file_path