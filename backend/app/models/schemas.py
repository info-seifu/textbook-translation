"""
Pydantic データモデル
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


# ============================================================================
# OCR関連モデル
# ============================================================================

class FigurePosition(BaseModel):
    """図解の位置情報"""
    x: int
    y: int
    width: int
    height: int


class FigureData(BaseModel):
    """図解データ"""
    id: int
    position: FigurePosition
    type: Literal["photo", "illustration", "diagram", "table", "graph"]
    description: str
    extracted_text: Optional[str] = None


class LayoutInfo(BaseModel):
    """レイアウト情報"""
    primary_direction: Literal["vertical", "horizontal"]
    columns: int = 1
    has_ruby: bool = False
    special_elements: List[str] = Field(default_factory=list)
    mixed_regions: List[dict] = Field(default_factory=list)


class OCRResult(BaseModel):
    """OCR結果"""
    page_number: int
    markdown_text: str
    figures: List[FigureData] = Field(default_factory=list)
    layout_info: LayoutInfo
    detected_writing_mode: Literal["vertical", "horizontal", "mixed"]


# ============================================================================
# 翻訳関連モデル
# ============================================================================

TranslatorEngine = Literal["claude", "gemini"]
TargetLanguage = Literal["en", "zh", "zh-TW", "ko", "vi", "th", "es", "fr"]


class TranslateRequest(BaseModel):
    """翻訳リクエスト"""
    job_id: str
    target_language: TargetLanguage
    translator_engine: TranslatorEngine = "claude"


# ============================================================================
# ジョブ管理モデル
# ============================================================================

OCRStatus = Literal["pending", "processing", "completed", "failed"]
TranslationStatus = Literal["pending", "processing", "completed", "failed"]


class TranslationJob(BaseModel):
    """翻訳ジョブ"""
    id: UUID
    user_id: Optional[UUID] = None
    original_filename: str
    pdf_url: str
    page_count: Optional[int] = None
    japanese_markdown_url: Optional[str] = None
    layout_metadata: Optional[dict] = None
    figures_data: Optional[dict] = None
    ocr_status: OCRStatus
    ocr_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TranslationOutput(BaseModel):
    """翻訳出力"""
    id: UUID
    job_id: UUID
    target_language: TargetLanguage
    translator_engine: TranslatorEngine
    translated_markdown_url: Optional[str] = None
    html_url: Optional[str] = None
    pdf_url: Optional[str] = None
    status: TranslationStatus
    error_message: Optional[str] = None
    translation_duration_seconds: Optional[float] = None
    token_count: Optional[int] = None
    cost_estimate: Optional[float] = None
    created_at: datetime


class Figure(BaseModel):
    """図解"""
    id: UUID
    job_id: UUID
    page_number: int
    figure_number: int
    image_url: str
    bounding_box: FigurePosition
    description: Optional[str] = None
    extracted_text: Optional[str] = None
    created_at: datetime


# ============================================================================
# APIレスポンスモデル
# ============================================================================

class UploadResponse(BaseModel):
    """アップロードレスポンス"""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """ジョブステータスレスポンス"""
    job: TranslationJob
    translations: List[TranslationOutput] = Field(default_factory=list)


class TranslationStartResponse(BaseModel):
    """翻訳開始レスポンス"""
    output_id: str
    status: str
    message: str


class HealthCheckResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    gemini_api_configured: bool
    claude_api_configured: bool
    supabase_configured: bool
