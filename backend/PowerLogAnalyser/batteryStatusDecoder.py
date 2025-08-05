import os, json, re
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL

class BatteryStatusSummarizer:
    def __init__(self, client: OpenAI, bitdef_path: str, cache_file: str = "RAG_DATA/battStatus_cache.json"):
        self.client = client
        self.bitdef_path = bitdef_path
        self.cache_file = cache_file
        self.status_cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.status_cache, f, indent=2)

    def load_bit_defs(self):
        namespace = {}
        with open(self.bitdef_path, "r") as f:
            exec(f.read(), {}, namespace)
        return namespace["bit_defs"]

    @staticmethod
    def decode_hex_status(hex_status: str, bit_defs: dict):
        """
        Decodes a hex status string. Handles multiple space-separated hex values.......
        Only shows bits that are set to 1 (active).
        """
        if not hex_status:
            return ["Empty value"]

        decoded = []
        hex_parts = hex_status.strip().split()

        for part in hex_parts:
            try:
                val = int(part, 16)
            except ValueError:
                decoded.append(f"Invalid hex: {part}")
                continue

            active_bits = []

            # Decode bits 15 to 4 (show only if set to 1)
            for bit in range(15, 4, -1):
                if ((val >> bit) & 1) == 1:
                    bit_info = bit_defs.get(bit)
                    if bit_info:
                        active_bits.append(f"Bit {bit} ({bit_info['name']}): {bit_info['description']}")

            # Always decode 4-bit error code (Bits 3-0)
            error_code_val = val & 0x0F
            error_desc = bit_defs.get("error_code", {}).get(error_code_val, "Unknown error code")
            active_bits.append(f"Bits 3-0 (Error Code): 0x{error_code_val:01X} → {error_desc}")

            if active_bits:
                decoded.append(f"{part} → " + " | ".join(active_bits))
            else:
                decoded.append(f"{part} → No active bits")

        return decoded

    

    def _explain_status_with_llm(self, decoded_status: str):
        prompt = f"""You are a battery status bitfield decoder for embedded medical devices.
Using the below information provided give a short operational conclusion.

hex_summary: {decoded_status}
"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528-qwen3-8b:free",  # new version needs eplacement with finetuned model Qwen,,,
                messages=[
                    {"role": "system", "content": "You are a technical expert in embedded systems, batteries, and register decoding. Always explain your reasoning clearly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def _remove_duplicates(self, items):
        seen = set()
        return [x for x in items if not (x in seen or seen.add(x))]

    def summarize_chunks(self, chunk_file: str, output_file: str = "PowerLogSummary.json"):
        with open(chunk_file) as f:
            chunks = json.load(f)

        bit_defs = self.load_bit_defs()
        batt_summary = {"battStatus_Summary": []}

        for chunk in chunks:
            chunk_id = chunk.get("ChunkID", "Unknown")
            raw_status = chunk.get("BattStatus", [])

            # Normalize input
            status_list = [raw_status] if isinstance(raw_status, str) else (raw_status or [])
            status_list = self._remove_duplicates(status_list)

            summary_texts = []

            for hex_val in status_list:
                if hex_val in self.status_cache:
                    explanation = self.status_cache[hex_val]
                else:
                    decoded = "\n".join(self.decode_hex_status(hex_val, bit_defs))
                    explanation = self._explain_status_with_llm(decoded)
                    self.status_cache[hex_val] = explanation
                    self._save_cache()
                summary_texts.append(explanation)

            # Final chunk-level summarization via LLM
            try:
                final_prompt = f"Summarize the battery status for the following time chunks in short:\n{summary_texts}"
                response = self.client.chat.completions.create(
                    model="deepseek/deepseek-r1-0528-qwen3-8b:free",
                    messages=[
                        {"role": "system", "content": "You are a technical expert in embedded systems, batteries, and register decoding."},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.5
                )
                chunk_summary = response.choices[0].message.content.strip()
            except Exception as e:
                chunk_summary = f"Summary LLM error: {str(e)}"

            batt_summary["battStatus_Summary"].append({
                "ChunkID": chunk_id,
                "BattStatus": status_list,
                "Summary": chunk_summary
            })
            print(f" Chunk {chunk_id} processed.")

        with open(output_file, "w") as f:
            json.dump(batt_summary, f, indent=2)
        print(f" {output_file} created successfully.")



if __name__ == "__main__":
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )

    summarizer = BatteryStatusSummarizer(
        client=client,
        bitdef_path="RAG_DATA/BitsDef/BatteryStatus.txt",
        cache_file="RAG_DATA_FOLDER/battStatus_cache.json"
    )

    # Uncomment to run directly:
    summarizer.summarize_chunks("chunks_Pump1.json")
