"""
pytest設定とフィクスチャ

テスト全体で共有されるフィクスチャや設定を定義
"""
import pytest
import asyncio
from pathlib import Path
import sys

# アプリケーションのルートをパスに追加
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session")
def event_loop():
    """イベントループのフィクスチャ（セッションスコープ）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_markdown():
    """サンプルMarkdownテキスト"""
    return """# 第1章 はじめに

これは教科書のサンプルテキストです。

## 1.1 概要

本章では、基本的な概念について説明します。

![図1](figures/fig1.png)

### ポイント
- ポイント1
- ポイント2
- ポイント3
"""


@pytest.fixture
def sample_ocr_result():
    """サンプルOCR結果"""
    return {
        "page_number": 1,
        "markdown_text": "# テストページ\n\nこれはテストです。",
        "detected_writing_mode": "horizontal",
        "figures": [
            {
                "id": 1,
                "position": {"x": 100, "y": 200, "width": 400, "height": 300},
                "type": "illustration",
                "description": "テスト図"
            }
        ],
        "layout_info": {
            "columns": 1,
            "writing_mode": "horizontal"
        }
    }


@pytest.fixture
def mock_gemini_api_key():
    """モックGemini APIキー"""
    return "test_gemini_api_key_12345"


@pytest.fixture
def mock_claude_api_key():
    """モックClaude APIキー"""
    return "test_claude_api_key_12345"
