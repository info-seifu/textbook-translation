# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller設定ファイル - 教科書翻訳システム

ビルド方法:
    pyinstaller textbook-translation.spec

出力:
    dist/textbook-translation/ ディレクトリに実行ファイルと必要なファイル一式
"""

import sys
from pathlib import Path

# プロジェクトのルートディレクトリ
spec_root = Path(SPECPATH)
app_root = spec_root

block_cipher = None

# アプリケーションのデータファイル
datas = [
    # テンプレートファイル
    (str(app_root / 'app' / 'templates'), 'app/templates'),
    # 静的ファイル
    (str(app_root / 'app' / 'static'), 'app/static'),
]

# 必要なPythonパッケージのデータファイル
# WeasyPrintの依存ファイルを含める
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'weasyprint',
    'cairocffi',
    'cffi',
]

a = Analysis(
    ['launcher.py'],
    pathex=[str(app_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='textbook-translation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # コンソールウィンドウを表示（ログ確認用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # アイコンファイルがあればここで指定
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='textbook-translation',
)
