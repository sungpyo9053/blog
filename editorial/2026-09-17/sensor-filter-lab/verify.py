"""Write actual subprocess outputs without personal absolute paths."""
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
records = []
for args in (["sensor_filter.py"], ["-m", "unittest", "-v"],
             ["sensor_filter.py", "--invalid-window", "0"]):
    result = subprocess.run([sys.executable, *args], cwd=ROOT,
                            text=True, capture_output=True)
    records.append({"command": "python3 " + " ".join(args),
                    "stdout": result.stdout, "stderr": result.stderr,
                    "exit_code": result.returncode})
payload = {"date": "2026-09-17", "python": platform.python_version(),
           "os": platform.system(), "os_version": platform.mac_ver()[0],
           "machine": platform.machine(), "records": records,
           "normalization": "Python executable absolute path shown as python3; output unchanged"}
(ROOT / "verification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
assert [item["exit_code"] for item in records] == [0, 0, 2]
print(json.dumps(payload, ensure_ascii=False, indent=2))
