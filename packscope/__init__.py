"""PackScope — companion PC app for the PocketOBI standalone reader.

Reads Makita LXT packs through a PocketOBI unit in USB-serial bridge mode,
reusing the firmware's own decode/verdict logic (ported here), and historizes
every reading locally in SQLite.
"""

__version__ = "1.0.0"
