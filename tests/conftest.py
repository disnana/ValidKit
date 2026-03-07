import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")


if SRC_DIR in sys.path:
    sys.path.remove(SRC_DIR)
sys.path.insert(0, SRC_DIR)


loaded_validkit = sys.modules.get("validkit")
if loaded_validkit is not None:
    loaded_from = getattr(loaded_validkit, "__file__", "") or ""
    expected_prefix = os.path.join(SRC_DIR, "validkit")
    if not os.path.abspath(loaded_from).startswith(os.path.abspath(expected_prefix)):
        for module_name in list(sys.modules):
            if module_name == "validkit" or module_name.startswith("validkit."):
                sys.modules.pop(module_name, None)

