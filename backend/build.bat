@echo off
REM ============================================
REM 教科書翻訳システム - Windows .exe ビルドスクリプト
REM ============================================

echo ============================================
echo 教科書翻訳システム - ビルド開始
echo ============================================
echo.

REM 1. Python環境のチェック
echo [1/5] Python環境をチェック中...
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonがインストールされていません
    echo Python 3.9以上をインストールしてください
    pause
    exit /b 1
)
echo   OK: Python が見つかりました
echo.

REM 2. 依存パッケージのインストール
echo [2/5] 依存パッケージをインストール中...
pip install -r requirements.txt
if errorlevel 1 (
    echo エラー: パッケージのインストールに失敗しました
    pause
    exit /b 1
)
echo   OK: 依存パッケージをインストールしました
echo.

REM 3. PyInstallerでビルド
echo [3/5] PyInstallerでビルド中...
pyinstaller textbook-translation.spec --clean
if errorlevel 1 (
    echo エラー: ビルドに失敗しました
    pause
    exit /b 1
)
echo   OK: ビルドが完了しました
echo.

REM 4. .envファイルをコピー（存在する場合）
echo [4/5] 環境設定ファイルをコピー中...
if exist .env (
    copy .env dist\textbook-translation\.env >nul
    echo   OK: .env ファイルをコピーしました
) else (
    echo   警告: .env ファイルが見つかりません
    echo   .env.example を参考に .env ファイルを作成してください
)
echo.

REM 5. README作成
echo [5/5] README.txtを作成中...
(
echo ============================================
echo 教科書翻訳システム
echo ============================================
echo.
echo 使い方:
echo   1. textbook-translation.exe をダブルクリック
echo   2. 自動的にブラウザが開きます
echo   3. PDFファイルをアップロードして翻訳を開始
echo.
echo 終了方法:
echo   コンソールウィンドウで Ctrl+C を押す
echo.
echo 必要なファイル:
echo   - .env : API キーなどの環境変数設定
echo     GEMINI_API_KEY=your_key_here
echo     CLAUDE_API_KEY=your_key_here
echo.
echo トラブルシューティング:
echo   - ブラウザが開かない場合:
echo     手動で http://localhost:8000 にアクセス
echo.
echo   - ポートエラーが出る場合:
echo     他のプログラムがポート8000を使用していないか確認
echo.
echo サポート:
echo   https://github.com/info-seifu/textbook-translation
echo.
) > dist\textbook-translation\README.txt
echo   OK: README.txt を作成しました
echo.

REM 完了メッセージ
echo ============================================
echo ビルド完了！
echo ============================================
echo.
echo 出力ディレクトリ: dist\textbook-translation\
echo.
echo 次のステップ:
echo   1. .env ファイルを dist\textbook-translation\ にコピー
echo   2. APIキーを設定
echo   3. textbook-translation.exe を実行
echo.
echo ============================================
pause
