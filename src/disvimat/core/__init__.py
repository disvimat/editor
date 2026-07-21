"""DisvimatEditor core.

This package must not import anything from the interface layers (wx,
fastapi...): all editor logic lives here and the desktop and web
adapters consume it. ``tests/test_architecture.py`` enforces that rule.
"""
