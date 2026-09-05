# PyInstaller spec for PackScope — one-file, windowed GUI build.
# Bundles the UI assets, the generated locale catalogs, and CustomTkinter's own
# theme/data files (without them the app crashes at startup). Built per-OS by the
# GitHub Actions release workflow; `sys.frozen` drives portable mode (see config.py).

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ("packscope/assets", "packscope/assets"),
    ("packscope/locales", "packscope/locales"),
]
datas += collect_data_files("customtkinter")

hiddenimports = collect_submodules("customtkinter")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PackScope",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # windowed GUI app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
