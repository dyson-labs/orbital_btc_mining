# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 19:31:45 2025

@author: elder
"""

import os
import datetime
import subprocess

FILENAME = "power_model.py"  # 🔁 Change to your target file

# 🔁 Paste Codex code here (full file)
CODEX_CODE = """
def power_model(asic_count):
    return 10 * asic_count  # Example Codex update
"""

def codex_merge(filename, new_code, run_after=False):
    # Write file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(new_code.strip())

    # Git commit
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.system(f"git add {filename}")
    os.system(f'git commit -m "Codex: update to {filename} @ {timestamp}"')

    # Optional run
    if run_after:
        print(f"\n--- Running your app.py ---\n")
        subprocess.run(["python", "app.py"])

if __name__ == "__main__":
    codex_merge(FILENAME, CODEX_CODE, run_after=True)
