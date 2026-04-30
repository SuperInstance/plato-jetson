"""
Plato Tile Commands — Knowledge management inside the MUD.

Commands:
  @tiles          — List all knowledge tiles
  @tile <name>    — Read a specific tile
  @tilesearch <query> — Search across all tiles
  @tilecreate <title> = <content> — Create a new tile
  @rooms          — Show Plato room map and tile counts

Inspired by: beads (22K⭐), memsearch (1.5K⭐), GenericAgent (8K⭐)
"""

import os
import glob
from datetime import datetime
from evennia import Command, default_cmds
from evennia.utils import evtable

WORKSPACE = os.path.expanduser("~/jetsonclaw1-vessel")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
TILES_DIR = os.path.join(MEMORY_DIR, "tiles")

ROOM_MAP = {
    "bridge": {"desc": "Captain's status & heartbeat", "alias": ["status"]},
    "tactical": {"desc": "Active orders & missions", "alias": ["orders"]},
    "corridor": {"desc": "Main passage — connects all rooms", "alias": ["main"]},
    "engine room": {"desc": "Hardware, CUDA, Jetson internals", "alias": ["engineering"]},
    "science lab": {"desc": "Research & experiments", "alias": ["research", "lab"]},
    "sickbay": {"desc": "System health & diagnostics", "alias": ["health", "diagnostics"]},
    "holodeck": {"desc": "Sandbox & simulations", "alias": ["sandbox", "sim"]},
    "cargo bay": {"desc": "Data stores & archives", "alias": ["storage", "archive"]},
    "quarterdeck": {"desc": "Captain's quarters", "alias": ["captain"]},
    "harbor": {"desc": "Fleet connection hub", "alias": ["fleet"]},
    "library": {"desc": "All knowledge tiles", "alias": ["knowledge", "tiles"]},
    "workshop": {"desc": "Skills & technical lessons", "alias": ["tools"]},
    "dojo": {"desc": "Training & drills", "alias": ["training"]},
    "airlock": {"desc": "External connections & API", "alias": ["external"]},
}


class CmdTiles(default_cmds.MuxCommand):
    """
    List all knowledge tiles in Plato.

    Usage:
      @tiles [room]
      @tiles recent [n]

    Shows all tiles, optionally filtered by Plato room.
    Use 'recent' to see the most recently modified tiles.
    """
    key = "@tiles"
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        os.makedirs(TILES_DIR, exist_ok=True)
        tiles = sorted(glob.glob(os.path.join(TILES_DIR, "*.md")))

        if not tiles:
            self.caller.msg("📚 Library is empty. Use @tilecreate to add knowledge tiles.")
            return

        args = self.args.strip().lower()
        if args.startswith("recent"):
            n = 5
            parts = args.split()
            if len(parts) > 1 and parts[1].isdigit():
                n = int(parts[1])
            tiles = sorted(tiles, key=os.path.getmtime, reverse=True)[:n]
            self.caller.msg(f"🆕 {n} Most Recent Tiles\n{'='*50}")
            for t in tiles:
                mtime = datetime.fromtimestamp(os.path.getmtime(t))
                with open(t) as f:
                    lines = f.readlines()
                    title = lines[0].strip("# \n") if lines else "untitled"
                self.caller.msg(f"  📄 {os.path.basename(t):40s} {mtime.strftime('%m-%d %H:%M'):12s} {title[:30]}")
        else:
            self.caller.msg(f"📚 Knowledge Library — {len(tiles)} tiles\n{'='*50}")
            for t in tiles:
                with open(t) as f:
                    lines = f.readlines()
                    title = lines[0].strip("# \n") if lines else "untitled"
                    # Get tags from frontmatter
                    tags = ""
                    for line in lines:
                        if line.startswith("tags:"):
                            tags = line.split("[")[1].split("]")[0] if "[" in line else ""
                            break
                size = os.path.getsize(t) // 1024
                self.caller.msg(f"  📄 {os.path.basename(t):35s} {title[:30]:30s} [{tags}]")


class CmdTile(default_cmds.MuxCommand):
    """
    Read a knowledge tile.

    Usage:
      @tile <name>

    Displays the full content of a knowledge tile.
    """
    key = "@tile"
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        name = self.args.strip()
        if not name:
            self.caller.msg("Usage: @tile <name>")
            return

        path = os.path.join(TILES_DIR, name)
        if not name.endswith(".md"):
            path += ".md"

        if not os.path.exists(path):
            # Try fuzzy match
            matches = glob.glob(os.path.join(TILES_DIR, f"*{name}*"))
            if len(matches) == 1:
                path = matches[0]
            elif len(matches) > 1:
                self.caller.msg(f"Multiple matches found:\n  " + "\n  ".join(os.path.basename(m) for m in matches))
                return
            else:
                self.caller.msg(f"❌ Tile not found: {name}")
                return

        with open(path) as f:
            content = f.read()

        # Strip frontmatter for display
        lines = content.split("\n")
        display_lines = []
        in_frontmatter = False
        for line in lines:
            if line.strip() == "---" and not in_frontmatter:
                in_frontmatter = True
                continue
            elif line.strip() == "---" and in_frontmatter:
                in_frontmatter = False
                continue
            if not in_frontmatter:
                display_lines.append(line)

        display = "\n".join(display_lines).strip()
        # Truncate very long tiles
        if len(display) > 3000:
            display = display[:3000] + f"\n\n... ({len(display) - 3000} more characters)"

        self.caller.msg(f"📄 {os.path.basename(path)}\n{'─'*50}\n{display}")


class CmdTileSearch(default_cmds.MuxCommand):
    """
    Search knowledge tiles.

    Usage:
      @tilesearch <query>

    Searches across all tiles and shows matching context.
    """
    key = "@tilesearch"
    aliases = ["@search"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        query = self.args.strip()
        if not query:
            self.caller.msg("Usage: @tilesearch <query>")
            return

        results = []
        for fpath in glob.glob(os.path.join(TILES_DIR, "*.md")):
            with open(fpath) as f:
                content = f.read()
                if query.lower() in content.lower():
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            start = max(0, i - 1)
                            end = min(len(lines), i + 3)
                            context = "\n".join(lines[start:end])
                            results.append({
                                "file": os.path.basename(fpath),
                                "line": i + 1,
                                "context": context.strip()[:150],
                            })
                            break  # One match per tile

        if not results:
            self.caller.msg(f"🔍 No results for '{query}'")
            return

        self.caller.msg(f"🔍 {len(results)} results for '{query}'\n{'='*50}")
        for r in results[:15]:
            self.caller.msg(f"  📄 {r['file']}:{r['line']}\n     {r['context']}\n")


class CmdTileCreate(default_cmds.MuxCommand):
    """
    Create a new knowledge tile.

    Usage:
      @tilecreate <title> = <content>
      @tilecreate <title> = <content> | tags: tag1, tag2

    Creates a new knowledge tile with YAML frontmatter.
    Persists to git automatically.
    """
    key = "@tilecreate"
    aliases = ["@tilewrite", "@tileadd"]
    locks = "cmd:perm(Admin)"
    help_category = "Plato"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @tilecreate <title> = <content> [| tags: tag1, tag2]")
            return

        # Parse title = content [| tags: ...]
        parts = self.args.split("=", 1)
        if len(parts) != 2:
            self.caller.msg("Usage: @tilecreate <title> = <content> [| tags: tag1, tag2]")
            return

        title = parts[0].strip()
        body = parts[1].strip()
        tags = ["new"]

        if "|" in body:
            body_parts = body.split("|", 1)
            body = body_parts[0].strip()
            for meta in body_parts[1].split(","):
                meta = meta.strip().lower()
                if meta.startswith("tags:"):
                    tags = [t.strip() for t in meta[5:].split(",") if t.strip()]

        os.makedirs(TILES_DIR, exist_ok=True)
        safe_name = title.lower().replace(" ", "_").replace("/", "-")[:50]
        path = os.path.join(TILES_DIR, f"{safe_name}.md")

        now = datetime.now().strftime("%Y-%m-%d")
        content = f"""---
id: {safe_name}
created: {now}
updated: {now}
tags: [{', '.join(tags)}]
---

# {title}

{body}
"""
        with open(path, "w") as f:
            f.write(content)

        # Git commit
        import subprocess
        rel_path = os.path.relpath(path, WORKSPACE)
        subprocess.run(
            f"cd {WORKSPACE} && git add {rel_path} && git commit -m 'tile: {safe_name}'",
            shell=True, capture_output=True, timeout=10
        )

        self.caller.msg(f"✅ Created tile: {safe_name}.md\n   Tags: {', '.join(tags)}\n   Path: {path}")


class CmdRooms(default_cmds.MuxCommand):
    """
    Show the Plato room map.

    Usage:
      @rooms

    Displays all rooms on the USS JetsonClaw1 with descriptions
    and what knowledge they hold.
    """
    key = "@rooms"
    aliases = ["@map"]
    locks = "cmd:all()"
    help_category = "Plato"

    def func(self):
        table = evtable.EvTable(
            "Room", "Description", "Aliases",
            border="cells", width=78
        )

        for name, info in ROOM_MAP.items():
            aliases = ", ".join(info["alias"])
            table.add_row(f"🏛️  {name.title()}", info["desc"], aliases)

        self.caller.msg(table)
        self.caller.msg(f"\n{'─'*78}")
        self.caller.msg(f"Plato — USS JetsonClaw1 — 14 rooms, 26 exits")
        self.caller.msg(f"Use @tiles to browse the knowledge library.")
