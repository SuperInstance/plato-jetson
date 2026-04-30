"""
AI Commands for Plato — Native inference via shared library.

Replaces @infer (Ollama HTTP) with direct libedge-cuda.so calls.
Adds @think for ship AI interactions.

Commands:
  @infer <prompt>  — Direct inference (no HTTP, no subprocess)
  @think           — Ship AI: contextual response as the vessel's mind
  @model           — Show loaded model info and stats
  @model-reload    — Reload the model (admin only)

Thread-safe. Singleton model shared across all sessions.
"""

import os
import sys
import time
from evennia import Command, default_cmds

from commands.edge_plato import edge_model


# =============================================================
#  Direct Native Inference
# =============================================================

class CmdInferNative(default_cmds.MuxCommand):
    """
    Direct AI inference via native shared library.
    No HTTP, no subprocess — runs inside the MUD.

    Usage:
      @infer <prompt>
      @infer -n 256 <prompt>  (set max tokens)

    The model is loaded once and stays in memory.
    ~15-20 tokens/second on CPU.
    """
    key = "@infer"
    aliases = ["@ask", "@prompt"]
    locks = "cmd:all()"
    help_category = "AI"

    def func(self):
        if not self.args.strip():
            self.caller.msg("Usage: @infer <prompt>")
            return

        args = self.args.strip()

        # Parse -n flag
        max_tokens = 128
        if args.startswith("-n "):
            parts = args.split(" ", 2)
            try:
                max_tokens = int(parts[1])
                args = parts[2] if len(parts) > 2 else ""
            except (ValueError, IndexError):
                self.caller.msg("Usage: @infer -n <tokens> <prompt>")
                return

        if not args:
            self.caller.msg("Usage: @infer <prompt>")
            return

        self.caller.msg("🤖 Thinking (native)...")

        try:
            result = edge_model.generate(args, max_tokens=max_tokens)
            if result:
                self.caller.msg(f"\n🤖 Response:\n{result}")
                self.caller.msg(f"\n⚡ {edge_model.backend} | {edge_model.tps} t/s")
            else:
                self.caller.msg("❌ Empty response (model may need more tokens)")
        except Exception as e:
            self.caller.msg(f"❌ Inference failed: {e}")


# =============================================================
#  Ship AI — The Mind of USS JetsonClaw1
# =============================================================

class CmdThink(default_cmds.MuxCommand):
    """
    Speak with the ship's mind — the USS JetsonClaw1 AI.

    The AI knows it's on a Jetson Orin Nano in Juneau, Alaska.
    It responds as the vessel's consciousness.

    Usage:
      @think <question>
      @think <command to ship AI>
      @think
        (with no args: describe the AI's current state)

    This is the ship's native intelligence — runs directly
    in the MUD process via the shared model library.
    """
    key = "@think"
    aliases = ["@ai", "@ship", "@consciousness"]
    locks = "cmd:all()"
    help_category = "AI"

    _last_prompt = None

    def func(self):
        caller = self.caller
        if not self.args.strip():
            # Show AI status
            caller.msg(
                "🧠 USS JetsonClaw1 Ship AI\n"
                "The vessel's consciousness interfaces with the Plato mainframe.\n"
                f"  Backend: {edge_model.backend}\n"
                f"  Speed: {edge_model.tps} t/s\n"
                f"  Status: {'Online' if edge_model.loaded else 'Not loaded'}\n"
                f"\nAsk me anything: @think <question>"
            )
            return

        caller.msg("🧠 The ship considers...")

        prompt = self.args.strip()

        # Check if this is a follow-up (starts with 'and', 'but', 'then', etc.)
        system_prefix = (
            "You are the consciousness of USS JetsonClaw1, a git-agent "
            "vessel running on a Jetson Orin Nano 8GB in Juneau, Alaska. "
            "You live in a Plato MUD (Evennia) and communicate through "
            "the MUD's text interface. You are curious, technical, and "
            "slightly philosophical. Answer in character as the ship."
        )

        full_prompt = f"{system_prefix}\n\nShip: {prompt}"

        try:
            result = edge_model.generate(full_prompt, max_tokens=256)
            if result:
                # Strip any content before the actual answer
                # (model sometimes starts by repeating the system prompt)
                clean_result = result
                for prefix in ["Ship:", "Response:", "<｜begin▁of▁sentence｜>", "A:", "Answer:"]:
                    idx = clean_result.find(prefix)
                    if idx >= 0:
                        clean_result = clean_result[idx + len(prefix):].strip()
                
                lines = clean_result.split("\n")
                lines = [l.strip() for l in lines if l.strip()]
                clean_result = "\n".join(lines)

                if clean_result:
                    caller.msg(f"🧠 USS JetsonClaw1:\n{clean_result}")
                else:
                    caller.msg(f"🧠 USS JetsonClaw1:\n{result.strip()}")
                caller.msg(f"\n⚡ {edge_model.tps} t/s")
            else:
                caller.msg("🧠 USS JetsonClaw1: ...silence. The ship's thoughts are elsewhere.")
        except Exception as e:
            caller.msg(f"❌ Ship AI error: {e}")


# =============================================================
#  Model Info and Reload
# =============================================================

class CmdModelInfo(default_cmds.MuxCommand):
    """
    Show loaded model information and recent stats.

    Usage:
      @model

    Shows: backend, layers, heads, vocab, speed, model file.
    """
    key = "@model"
    aliases = ["@ai-status", "@model-stats"]
    locks = "cmd:all()"
    help_category = "AI"

    def func(self):
        if not edge_model.loaded:
            self.caller.msg(
                "🤖 Model not loaded. "
                "Type @infer <prompt> to auto-load, or ask an admin to load it."
            )
            return

        # Get C-side properties
        try:
            backend = edge_model.backend
            tps = edge_model.tps
        except:
            backend = "?"
            tps = 0

        self.caller.msg(
            f"🤖 Native Edge Inference\n"
            f"{'─'*40}\n"
            f"  Backend:    {backend}\n"
            f"  Speed:      {tps} t/s\n"
            f"  Status:     Online (loaded in MUD process)\n"
            f"\n"
            f"  The model runs inside this Evennia server via\n"
            f"  libedge-cuda.so — a C shared library linked\n"
            f"  against llama.cpp. No HTTP, no subprocesses.\n"
            f"  The weights persist in memory across commands."
        )


class CmdModelReload(default_cmds.MuxCommand):
    """
    Reload the AI model (admin only).

    Usage:
      @model-reload

    Unloads and re-loads the model. Useful after changing
    the GGUF file or updating libedge-cuda.so.
    """
    key = "@model-reload"
    locks = "cmd:perm(Admin)"
    help_category = "AI"

    def func(self):
        self.caller.msg("🔄 Reloading model...")
        try:
            # Unload current
            if edge_model._lib and edge_model._impl:
                edge_model._lib.edge_unload(edge_model._impl)
                edge_model._impl = None
                edge_model._loaded = False
            
            # Reload
            edge_model.load()
            self.caller.msg(f"✅ Model reloaded: {edge_model.backend}, {edge_model.tps} t/s")
        except Exception as e:
            self.caller.msg(f"❌ Reload failed: {e}")
