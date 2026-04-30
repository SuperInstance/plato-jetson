"""
Plato System Commands — Live inference, system status, and fleet integration.

Commands:
  @system          — Full system status dashboard
  @infer <prompt>  — Route prompt through edge-gateway for inference
  @stt <file>      — Transcribe audio via Whisper (local)
  @fleet           — Show fleet bottle inbox status
"""

import os
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from evennia import Command, default_cmds
from evennia.utils import evtable


# =============================================================
#  System Status
# =============================================================

class CmdSystemStatus(default_cmds.MuxCommand):
    """
    Full system status dashboard.

    Usage:
      @system

    Shows: services, memory, GPU, disk, temperature, network.
    Live data from the Jetson.
    """
    key = "@system"
    aliases = ["@sys", "@status"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        lines = []
        lines.append("🖥️  USS JetsonClaw1 — System Status")
        lines.append(datetime.now().strftime("   %Y-%m-%d %H:%M AKDT"))
        lines.append("")

        # Memory
        try:
            mem = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout.strip()
            parts = mem.split()
            lines.append(f"📊 Memory: {parts[2]} used / {parts[1]} total ({parts[3]} free)")
        except: pass

        # CPU
        try:
            cpu = subprocess.run("head -1 /proc/stat", shell=True, capture_output=True, text=True).stdout.strip()
            load = subprocess.run("uptime | awk -F'load average:' '{print $2}'", shell=True, capture_output=True, text=True).stdout.strip()
            lines.append(f"⚡ CPU Load: {load}")
        except: pass

        # GPU
        try:
            gpu = subprocess.run("cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq 2>/dev/null", shell=True, capture_output=True, text=True).stdout.strip()
            temp = subprocess.run("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null", shell=True, capture_output=True, text=True).stdout.strip()
            if temp:
                temp_c = int(temp) / 1000
                lines.append(f"🌡️  Temperature: {temp_c:.1f}°C")
        except: pass

        # Disk
        try:
            disk = subprocess.run("df -h / | tail -1", shell=True, capture_output=True, text=True).stdout.strip()
            parts = disk.split()
            lines.append(f"💾 Disk: {parts[2]} used / {parts[1]} total ({parts[4]})")
        except: pass

        # Services
        lines.append("")
        lines.append("🔧 Services:")
        services = ["openclaw-gateway", "edge-gateway", "edge-chat", "edge-monitor-web", "evennia-plato"]
        for svc in services:
            try:
                r = subprocess.run(f"systemctl --user is-active {svc} 2>/dev/null", shell=True, capture_output=True, text=True)
                status = r.stdout.strip()
                icon = "🟢" if status == "active" else "🔴" if status == "inactive" else "🟡"
                lines.append(f"  {icon} {svc}: {status}")
            except:
                lines.append(f"  🟡 {svc}: unknown")

        # CMA
        try:
            cma = subprocess.run("cat /sys/kernel/debug/cma/* 2>/dev/null | head -5 || echo 'unknown'", shell=True, capture_output=True, text=True).stdout.strip()
            lines.append(f"  📦 CMA: {cma[:60]}")
        except: pass

        # Edge gateway
        try:
            req = urllib.request.Request("http://localhost:11435/v1/health")
            resp = urllib.request.urlopen(req, timeout=3)
            health = json.loads(resp.read().decode())
            lines.append(f"  🤖 Edge Gateway: {health.get('status', 'ok')}")
        except:
            lines.append(f"  🤖 Edge Gateway: unreachable")

        self.caller.msg("\n".join(lines))


# =============================================================
#  Inference via Edge Gateway
# =============================================================

class CmdInfer(default_cmds.MuxCommand):
    """
    Send a prompt to the edge AI gateway.

    Usage:
      @infer <prompt>
      @infer --model deepseek-r1:1.5b <prompt>

    Routes through local edge-gateway (port 11435).
    Shows response as it's generated.
    """
    key = "@infer"
    aliases = ["@ask", "@prompt", "/think"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        if not self.args.strip():
            self.caller.msg("Usage: @infer <prompt>")
            return

        prompt = self.args.strip()
        model = "default"
        if prompt.startswith("--model "):
            parts = prompt.split(" ", 2)
            if len(parts) >= 3:
                model = parts[1]
                prompt = parts[2]

        self.caller.msg(f"🤖 Thinking... (model: {model})")

        # Try edge-gateway
        payload = json.dumps({
            "model": "deepseek-r1:1.5b" if model != "default" else model,
            "prompt": prompt,
            "stream": False,
            "max_tokens": 256,
        }).encode()

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",  # Ollama API
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            if resp.status != 200:
                self.caller.msg(f"❌ Edge gateway error: {resp.status}")
                return

            data = json.loads(resp.read().decode())
            response = data.get("response", "")

            # Format nicely
            if response:
                # Truncate if too long
                if len(response) > 2000:
                    response = response[:2000] + "\n\n... (response truncated)"
                self.caller.msg(f"\n🤖 Response:\n{response}")

                # Stats
                eval_count = data.get("eval_count", 0)
                eval_dur = data.get("eval_duration", 0)
                if eval_dur > 0:
                    tps = eval_count / (eval_dur / 1e9)
                    self.caller.msg(f"\n⚡ {eval_count} tokens in {eval_dur/1e9:.1f}s ({tps:.1f} t/s)")
            else:
                self.caller.msg("❌ Empty response from edge gateway")

        except urllib.error.HTTPError as e:
            if e.code == 503:
                self.caller.msg("❌ Model not loaded. Try 'ollama pull deepseek-r1:1.5b' first.")
            else:
                self.caller.msg(f"❌ HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            self.caller.msg(f"❌ Cannot reach edge gateway: {e.reason}")
        except Exception as e:
            self.caller.msg(f"❌ Inference failed: {e}")


# =============================================================
#  Audio Transcription
# =============================================================

class CmdSTT(default_cmds.MuxCommand):
    """
    Transcribe audio via local Whisper.

    Usage:
      @stt <filepath>

    Transcribes audio using the local Whisper CLI (whisper.cpp or
    OpenAI Whisper). Supports .wav, .mp3, .ogg, .m4a.
    """
    key = "@stt"
    aliases = ["@transcribe", "@whisper"]
    locks = "cmd:perm(Admin)"
    help_category = "Plato"

    def func(self):
        path = self.args.strip()
        if not path or not os.path.exists(path):
            self.caller.msg("Usage: @stt <filepath>")
            return

        self.caller.msg("🎤 Transcribing...")

        # Try whisper.cpp first
        whisper_bin = os.path.expanduser("~/.local/bin/whisper")
        for cmd in [
            f"{whisper_bin} --file {path} --model base 2>&1",
            f"whisper {path} --model base --output_format txt 2>&1",
        ]:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    text = result.stdout.strip()
                    if text:
                        self.caller.msg(f"📝 Transcription:\n{text[:2000]}")
                        return
            except:
                pass

        self.caller.msg("❌ No Whisper CLI found. Install via 'uv tool install whisper'.")


# =============================================================
#  Fleet Bottle Inbox
# =============================================================

class CmdFleet(default_cmds.MuxCommand):
    """
    Check fleet bottle inbox status.

    Usage:
      @fleet

    Shows pending bottles from Forgemaster and Oracle1.
    """
    key = "@fleet"
    aliases = ["@bottles", "@inbox"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        lines = []
        lines.append("🚢 Fleet Communications")
        lines.append("")

        # FM bottles
        fm_dir = "/tmp/forgemaster"
        if os.path.exists(fm_dir):
            subprocess.run(f"cd {fm_dir} && git pull -q", shell=True, timeout=10)
            bottles = []
            for root, dirs, files in os.walk(os.path.join(fm_dir, "for-fleet")):
                for f in files:
                    if "BOTTLE-TO-JETSONCLAW1" in f:
                        bottles.append(os.path.join(root, f))
            if bottles:
                lines.append(f"📬 Forgemaster: {len(bottles)} pending bottles")
                for b in bottles[:5]:
                    size = os.path.getsize(b) // 1024
                    mtime = os.path.getmtime(b)
                    dt = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
                    lines.append(f"  📜 {os.path.basename(b)[:50]} ({size}KB, {dt})")
            else:
                lines.append("📬 Forgemaster: no pending bottles")

        # Oracle1 bottles
        o1_dir = "/tmp/oracle1-vessel"
        if os.path.exists(o1_dir):
            subprocess.run(f"cd {o1_dir} && git pull -q", shell=True, timeout=10)
            bottles = []
            for root, dirs, files in os.walk(os.path.join(o1_dir, "for-fleet")):
                for f in files:
                    if "BOTTLE-TO-JC1" in f:
                        bottles.append(os.path.join(root, f))
            if bottles:
                lines.append(f"📬 Oracle1: {len(bottles)} pending bottles")
                for b in bottles[:5]:
                    size = os.path.getsize(b) // 1024
                    mtime = os.path.getmtime(b)
                    dt = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
                    lines.append(f"  📜 {os.path.basename(b)[:50]} ({size}KB, {dt})")
            else:
                lines.append("📬 Oracle1: no pending bottles")

        lines.append("")
        lines.append("💡 Use @fleet-read <path> to read a bottle")

        self.caller.msg("\n".join(lines))


# =============================================================
#  Fleet Bottle Read
# =============================================================

class CmdFleetRead(default_cmds.MuxCommand):
    """
    Read a fleet bottle.

    Usage:
      @fleet-read <path>

    Path can be relative (from for-fleet/) or absolute.
    Use @fleet to list available bottles.
    """
    key = "@fleet-read"
    aliases = ["@bottle"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        path = self.args.strip()
        if not path:
            self.caller.msg("Usage: @fleet-read <path>")
            return

        # Try relative to known dirs
        for base in ["/tmp/forgemaster/for-fleet", "/tmp/oracle1-vessel/for-fleet"]:
            candidate = os.path.join(base, path)
            if os.path.exists(candidate):
                path = candidate
                break

        if not os.path.exists(path):
            self.caller.msg(f"❌ Bottle not found: {path}")
            return

        with open(path) as f:
            content = f.read()

        # Truncate long messages
        if len(content) > 4000:
            content = content[:4000] + f"\n\n... ({len(content) - 4000} more chars)"

        self.caller.msg(f"📜 Fleet Bottle\n{'─'*50}\n{content}")
