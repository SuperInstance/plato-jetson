"""
edge_plato.py — Native AI inference inside the Evennia MUD process.

This module loads libedge-cuda.so directly into the Evennia server process.
No subprocess, no HTTP server — just a direct shared library call.
The model persists in memory and serves every @think command instantly.

Usage (after the MUD starts):
   from commands.edge_plato import edge_model
   text = edge_model.generate("Hello world", max_tokens=64)
   text = edge_model.generate_stream("Hello", callback=my_fn)  # streaming!

The shared model is a singleton: first load creates it, subsequent calls
use the existing instance. Thread-safe (mutex in C code).
"""

import ctypes
import os
import sys
import threading

_load_lock = threading.Lock()


def _find_lib():
    """Find libedge-cuda.so in known locations."""
    paths = [
        os.path.expanduser("~/edge-llama/build/libedge-cuda.so"),
        os.path.expanduser("~/edge-llama/build/libedge-cuda.so.1.0.0"),
    ]
    for p in paths:
        if os.path.exists(p):
            return str(os.path.realpath(p))
    raise FileNotFoundError(
        "libedge-cuda.so not found. Build it:\n"
        "  cd ~/edge-llama && mkdir -p build && cd build && cmake .. && make"
    )


class EdgePlatoModel:
    """
    Edge inference shared library loaded directly into the MUD process.
    
    Singleton pattern: one model instance shared by all MUD commands.
    Thread-safe by design (C code uses mutex on generate).
    """

    def __init__(self):
        self._lib = None
        self._impl = None
        self._model_path = None
        self._loaded = False

    def load(self, model_path: str = None):
        """Load the shared library and model. Idempotent."""
        with _load_lock:
            if self._loaded:
                return

            if model_path is None:
                home = os.path.expanduser("~")
                candidates = [
                    f"{home}/edge-llama/models/dsr1-1.5b-q4km.gguf",
                ]
                for c in candidates:
                    if os.path.exists(c):
                        model_path = os.path.realpath(c)
                        break
                if not model_path:
                    raise FileNotFoundError("No model GGUF found. Run 'ollama pull deepseek-r1:1.5b' and create symlink.")

            self._model_path = model_path
            lib_path = _find_lib()
            self._lib = ctypes.CDLL(lib_path)

            # ── Set up C function signatures ──

            # edge_load
            self._lib.edge_load.restype = ctypes.c_void_p
            self._lib.edge_load.argtypes = [ctypes.c_char_p]

            # edge_unload
            self._lib.edge_unload.restype = None
            self._lib.edge_unload.argtypes = [ctypes.c_void_p]

            # edge_generate (blocking)
            self._lib.edge_generate.restype = ctypes.POINTER(ctypes.c_char)
            self._lib.edge_generate.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_int32,
                ctypes.POINTER(ctypes.c_int32),
                ctypes.POINTER(ctypes.c_int32),
            ]

            # edge_generate_stream (with callback)
            STREAM_CB = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int32, ctypes.c_void_p)
            self._lib.edge_generate_stream.restype = ctypes.POINTER(ctypes.c_char)
            self._lib.edge_generate_stream.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_int32,
                ctypes.POINTER(ctypes.c_int32),
                ctypes.POINTER(ctypes.c_int32),
                STREAM_CB,
                ctypes.c_void_p,
            ]

            # edge_free_string
            self._lib.edge_free_string.restype = None
            self._lib.edge_free_string.argtypes = [ctypes.c_void_p]

            # Accessors
            self._lib.edge_backend.restype = ctypes.c_char_p
            self._lib.edge_backend.argtypes = [ctypes.c_void_p]
            self._lib.edge_tokens_per_second.restype = ctypes.c_int32
            self._lib.edge_tokens_per_second.argtypes = [ctypes.c_void_p]
            self._lib.edge_last_error.restype = ctypes.c_char_p
            self._lib.edge_last_error.argtypes = []
            self._lib.edge_n_layer.restype = ctypes.c_int32
            self._lib.edge_n_layer.argtypes = [ctypes.c_void_p]
            self._lib.edge_n_embd.restype = ctypes.c_int32
            self._lib.edge_n_embd.argtypes = [ctypes.c_void_p]
            self._lib.edge_n_head.restype = ctypes.c_int32
            self._lib.edge_n_head.argtypes = [ctypes.c_void_p]
            self._lib.edge_n_vocab.restype = ctypes.c_int32
            self._lib.edge_n_vocab.argtypes = [ctypes.c_void_p]

            # Load model (CUDA_VISIBLE_DEVICES="" if env not set)
            if "CUDA_VISIBLE_DEVICES" not in os.environ:
                os.environ["CUDA_VISIBLE_DEVICES"] = ""

            model_path_bytes = model_path.encode('utf-8')
            self._impl = self._lib.edge_load(model_path_bytes)
            if not self._impl:
                err = self._lib.edge_last_error()
                raise RuntimeError(f"edge_load failed: {err.decode() if err else 'unknown error'}")

            self._loaded = True

    @property
    def loaded(self) -> bool:
        return self._loaded and self._impl is not None

    # ── Blocking generate ──

    def generate(self, prompt: str, max_tokens: int = 128) -> str:
        """Generate text. Returns generated text only (not including prompt)."""
        if not self._loaded or not self._impl:
            self.load()
        out_len = ctypes.c_int32(0)
        new_tokens = ctypes.c_int32(0)
        result_ptr = self._lib.edge_generate(
            self._impl,
            prompt.encode('utf-8'),
            ctypes.c_int32(max_tokens),
            ctypes.byref(out_len),
            ctypes.byref(new_tokens)
        )
        if not result_ptr:
            return ""
        try:
            return ctypes.string_at(result_ptr, out_len.value).decode('utf-8', errors='replace')
        finally:
            self._lib.edge_free_string(result_ptr)

    # ── Streaming generate ──

    def generate_stream(self, prompt: str, max_tokens: int = 128,
                        callback=None) -> str:
        """
        Generate text with streaming callback per token piece.
        
        Args:
            prompt: Input text
            max_tokens: Maximum tokens to generate
            callback: Function(piece: str, length: int) called for each piece
            
        Returns:
            Full generated text (also available via callback)
        """
        if not self._loaded or not self._impl:
            self.load()

        STREAM_CB = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int32, ctypes.c_void_p)

        def _cb(piece_bytes, length, user_ctx):
            piece = ctypes.string_at(piece_bytes, length).decode('utf-8', errors='replace')
            if callback:
                callback(piece, length)

        c_callback = STREAM_CB(_cb)

        out_len = ctypes.c_int32(0)
        new_tokens = ctypes.c_int32(0)

        result_ptr = self._lib.edge_generate_stream(
            self._impl,
            prompt.encode('utf-8'),
            ctypes.c_int32(max_tokens),
            ctypes.byref(out_len),
            ctypes.byref(new_tokens),
            c_callback,
            None
        )

        full_text = ""
        if result_ptr:
            try:
                full_text = ctypes.string_at(result_ptr, out_len.value).decode('utf-8', errors='replace')
            finally:
                self._lib.edge_free_string(result_ptr)

        return full_text

    @property
    def backend(self) -> str:
        if not self._impl:
            return "none"
        return self._lib.edge_backend(self._impl).decode()

    @property
    def tps(self) -> int:
        if not self._impl:
            return 0
        return self._lib.edge_tokens_per_second(self._impl)


# ── Singleton instance ──
# Import this from MUD commands:
#   from commands.edge_plato import edge_model
#
# The first call to edge_model.generate() auto-loads the model.

edge_model = EdgePlatoModel()
