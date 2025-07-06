import os
import datetime
import subprocess
import sys

# Usage: python codex_merge.py target_filename.py
def codex_merge(filename, code_file="code.txt", run_after=False):
    # Read the new code from code.txt
    if not os.path.exists(code_file):
        print(f"❌ ERROR: '{code_file}' not found.")
        return

    with open(code_file, "r", encoding="utf-8") as f:
        new_code = f.read()

    # Write to the target file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(new_code.strip())

    # Commit changes
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.system(f"git add {filename}")
    os.system(f'git commit -m "Codex update to {filename} @ {timestamp}"')

    # Optionally run the app
    if run_after:
        print("\n--- Running your app.py ---\n")
        subprocess.run(["python", "app.py"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python codex_merge.py <target_filename.py> [--run]")
    else:
        filename = sys.argv[1]
        run_flag = "--run" in sys.argv
        codex_merge(filename, run_after=run_flag)
