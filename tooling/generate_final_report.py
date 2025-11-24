"""Simple helper to prepare a final aggregated report.
This script copies TEST_REPORT.md into reports/final_aggregated_report.md and adds a timestamp.
Run: python3 tooling/generate_final_report.py
"""

from datetime import datetime
from pathlib import Path

root = Path("/root/personal/STRling")
src = root / "TEST_REPORT.md"
dst_dir = root / "reports"
dst_dir.mkdir(parents=True, exist_ok=True)
dst = dst_dir / "final_aggregated_report.md"

if not src.exists():
    print("Source TEST_REPORT.md not found")
    raise SystemExit(1)

content = src.read_text()
header = f"# Final aggregated STRling report\nGenerated: {datetime.utcnow().isoformat()}Z\n\n"

# Write the aggregated report
with dst.open("w") as fh:
    fh.write(header)
    fh.write(content)

print("Final aggregated report prepared at", dst)
