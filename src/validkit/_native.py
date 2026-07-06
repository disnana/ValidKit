import os
from typing import Any, Optional


class NativeRuntime:
    def __init__(self) -> None:
        self.module: Optional[Any] = None
        self.available = False
        self.disabled = False
        self.error: Optional[BaseException] = None

        if os.environ.get("VALIDKIT_DISABLE_NATIVE", "").lower() in {"1", "true", "yes", "on"}:
            self.disabled = True
            return

        try:
            import validkit_core as module
        except ImportError as exc:
            self.error = exc
            return

        self.module = module
        self.available = True

    def compile(self, schema: Any) -> Optional[Any]:
        if self.module is None:
            return None

        compile_schema = getattr(self.module, "compile_schema", None)
        if compile_schema is None:
            return None

        try:
            return compile_schema(schema)
        except TypeError:
            return None


NATIVE_RUNTIME = NativeRuntime()
