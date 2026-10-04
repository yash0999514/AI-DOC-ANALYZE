#!/usr/bin/env python3
import sys, os
if "/home/spark/pylib" not in sys.path:
    sys.path.insert(0, "/home/spark/pylib")

import importlib.util
spec = importlib.util.spec_from_file_location("pytest_core", "/home/spark/pylib/pytest/__init__.py")
_core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_core)

fixture = _core.fixture
raises = _core.raises
MonkeyPatch = _core.MonkeyPatch
run = _core.run
main = _core.main

if __name__ == '__main__':
    sys.exit(main())
