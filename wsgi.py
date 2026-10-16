"""Entry point for hosting MedRemind Care (gunicorn / waitress / any WSGI host).

Your desktop modules (login.py, manage_medicine.py ...) import tkinter. Web servers
usually do not have tkinter, so this file installs a harmless stand-in ONLY when
tkinter is missing. The website never opens a desktop window, so nothing is lost.
"""
import sys
import types

try:  # pragma: no cover - depends on the machine
    import tkinter  # noqa: F401
except ImportError:
    class _Meta(type):
        def __getattr__(cls, name):
            return _Dummy

    class _Dummy(metaclass=_Meta):
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return _Dummy

        def __call__(self, *args, **kwargs):
            return _Dummy()

    class _StubModule(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return _Dummy

    for _name in ("tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog", "tkinter.simpledialog"):
        sys.modules[_name] = _StubModule(_name)

from web_app import create_app  # noqa: E402

app = create_app()
