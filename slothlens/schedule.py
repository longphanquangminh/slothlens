"""Print how to run slothlens every night on this OS. We print instead of
installing: a tool that edits your crontab silently is not a lazy tool, it's
a rude one."""
from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path


def instructions() -> str:
    exe = shutil.which("slothlens") or f"{sys.executable} -m slothlens"
    system = platform.system()
    if system == "Darwin":
        plist = Path.home() / "Library/LaunchAgents/dev.slothlens.nap.plist"
        args = "".join(f"\n      <string>{a}</string>" for a in exe.split() + ["nap"])
        return f"""# macOS: save this as {plist}
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>dev.slothlens.nap</string>
  <key>ProgramArguments</key><array>{args}
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>45</integer></dict>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>19</integer>
  <key>StandardOutPath</key><string>{Path.home()}/.slothlens/nap.log</string>
</dict></plist>

# then:
launchctl load {plist}
# (macOS also wakes the job up after sleep if it missed 00:45)"""
    if system == "Windows":
        return (f'schtasks /Create /SC DAILY /ST 00:45 /TN "slothlens nap" '
                f'/TR "{exe} nap" /RL LIMITED\n'
                "# In Task Scheduler, tick 'Start only if on AC power' and 'Start only if idle'.")
    return ("# Linux: crontab -e, then add\n"
            f"45 0 * * *  {exe} nap >> ~/.slothlens/nap.log 2>&1\n"
            "# morning digest at 7:30, straight to a file you'll actually open:\n"
            f"30 7 * * *  {exe} digest --html ~/slothlens-digest.html > /dev/null")
