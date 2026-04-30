"""
Server startstop hooks — with native AI model pre-loading.

Loads libedge-cuda.so into the MUD process at server start.
The model stays resident in memory across all player sessions.

Hooks:
  at_server_init()        — Load native AI model
  at_server_cold_start()  — Log model info
  at_server_stop()        — Unload model
"""

import os
import sys


def at_server_init():
    """
    Called first as the server starts, regardless of how.
    This is where we pre-load the native AI model into the MUD process.
    """
    # Set env to avoid CUDA crashes due to depleted CMA pool
    if "CUDA_VISIBLE_DEVICES" not in os.environ:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    try:
        from commands.edge_plato import edge_model
        edge_model.load()
        print(f"\n{'='*60}")
        print(f"🤖 NATIVE AI ENGINE LOADED")
        print(f"   Backend: {edge_model.backend}")
        print(f"   Speed:   {edge_model.tps} t/s")
        print(f"   Model:   {edge_model._model_path}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n⚠️  Native AI model not loaded: {e}")
        print("   @infer and @think commands will auto-load on first use.\n")


def at_server_start():
    """
    Called every time the server starts up.
    """
    pass


def at_server_stop():
    """
    Called just before the server shuts down.
    Unload the native model to free memory cleanly.
    """
    try:
        from commands.edge_plato import edge_model
        if edge_model.loaded:
            edge_model._lib.edge_unload(edge_model._impl)
            print("🧠 Native AI model unloaded.")
    except:
        pass


def at_server_reload_start():
    """
    Called when server starts back up after a reload.
    The model is typically still loaded in shared memory,
    but we re-attach to be safe.
    """
    at_server_init()


def at_server_reload_stop():
    """
    Called when the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    Called only when the server starts "cold" (after shutdown/reset).
    The model was fully unloaded — reload it.
    """
    at_server_init()


def at_server_cold_stop():
    """
    Called only when the server goes down due to shutdown or reset.
    """
    try:
        from commands.edge_plato import edge_model
        if edge_model.loaded:
            edge_model._lib.edge_unload(edge_model._impl)
            print("🧠 Native AI model unloaded (cold stop).")
    except:
        pass
