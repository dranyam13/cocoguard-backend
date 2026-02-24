"""
Simple script to ensure clean server restart.
Run this if you encounter module import cache issues.
"""
import sys
import importlib

# Clear any cached modules
modules_to_clear = [m for m in sys.modules.keys() if m.startswith('app.')]
for mod in modules_to_clear:
    del sys.modules[mod]

print("✓ Cleared cached app modules")
print("Now run: uvicorn app.main:app --reload")
