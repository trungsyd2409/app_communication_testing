# PyInstaller build recipe.  Run:  pyinstaller --noconfirm --clean SpeakDaily.spec
# Output: dist/SpeakDaily.exe (one file, no console window)
from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("speakdaily/assets", "speakdaily/assets"),
    ("speakdaily/data", "speakdaily/data"),
]
datas += collect_data_files("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["google_auth_oauthlib.flow", "google.oauth2.credentials",
                   "google.auth.transport.requests"],
    excludes=["numpy", "pandas", "matplotlib", "scipy", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SpeakDaily",
    icon="speakdaily/assets/app.ico",
    console=False,
    upx=False,
    runtime_tmpdir=None,
)
