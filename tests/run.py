#!/usr/bin/env python3
"""Isolated behavior tests; does not install anything into the actual home."""
import os
from pathlib import Path
import shutil
import sys
import unittest

root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'scripts'),str(root/'tests')]
if not os.environ.get('DOTBOT_BIN'):
    binary=shutil.which('dotbot')
    if not binary: sys.exit('Install Dotbot or set DOTBOT_BIN to its bin/dotbot executable.')
    os.environ['DOTBOT_BIN']=binary
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(root/'tests')))
sys.exit(not result.wasSuccessful())
