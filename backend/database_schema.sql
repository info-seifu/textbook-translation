-- ============================================================================
-- 教科書翻訳アプリ Supabase スキーマ定義
-- ============================================================================

-- UUIDエクステンションの有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- テーブル定義
-- ============================================================================

-- 翻訳ジョブテーブル
CREATE TABLE IF NOT EXISTS translation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),

    -- ファイル情報
    original_filename TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    page_count INTEGER,

    -- OCR結果
    japanese_markdown_url TEXT,  -- マスターファイル
    layout_metadata JSONB,        -- レイアウト情報
    figures_data JSONB,            -- 図解データ

    -- ステータス
    ocr_status TEXT CHECK (ocr_status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    ocr_error TEXT,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_translation_jobs_user_id ON translation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_ocr_status ON translation_jobs(ocr_status);
CREATE INDEX IF NOT EXISTS idx_translation_jobs_created_at ON translation_jobs(created_at DESC);

-- 翻訳出力テーブル
CREATE TABLE IF NOT EXISTS translation_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES translation_jobs(id) ON DELETE CASCADE,

    -- 翻訳設定
    target_language TEXT NOT NULL,  -- 'en', 'zh', 'ko', etc.
    translator_engine TEXT CHECK (translator_engine IN ('gemini', 'claude')) DEFAULT 'claude',

    -- 翻訳結果
    translated_markdown_url TEXT,
    html_url TEXT,
    pdf_url TEXT,

    -- ステータス
    status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    error_message TEXT,

    -- メタデータ
    translation_duration_seconds REAL,
    token_count INTEGER,
    cost_estimate REAL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_translation_outputs_job_id ON translation_outputs(job_id);
CREATE INDEX IF NOT EXISTS idx_translation_outputs_status ON translation_outputs(status);
CREATE INDEX IF NOT EXISTS idx_translation_outputs_created_at ON translation_outputs(created_at DESC);

-- 図解テーブル
CREATE TABLE IF NOT EXISTS figures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES translation_jobs(id) ON DELETE CASCADE,

    -- 図解情報
    page_number INTEGER NOT NULL,
    figure_number INTEGER NOT NULL,
    image_url TEXT NOT NULL,

    -- 位置情報
    bounding_box JSONB,  -- {x, y, width, height}

    -- メタデータ
    description TEXT,    -- Geminiが生成した説明
    extracted_text TEXT, -- 図解内のテキスト

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_figures_job_id ON figures(job_id);
CREATE INDEX IF NOT EXISTS idx_figures_page_number ON figures(page_number);

-- ============================================================================
-- 更新トリガー（updated_atの自動更新）
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_translation_jobs_updated_at
    BEFORE UPDATE ON translation_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Row Level Security (RLS) 設定
-- ============================================================================

-- RLSを有効化
ALTER TABLE translation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE translation_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE figures ENABLE ROW LEVEL SECURITY;

-- ポリシー: ユーザーは自分のジョブのみ参照可能
CREATE POLICY "Users can view their own jobs"
    ON translation_jobs
    FOR SELECT
    USING (auth.uid() = user_id);

-- ポリシー: ユーザーは自分のジョブのみ作成可能
CREATE POLICY "Users can create their own jobs"
    ON translation_jobs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ポリシー: ユーザーは自分のジョブのみ更新可能
CREATE POLICY "Users can update their own jobs"
    ON translation_jobs
    FOR UPDATE
    USING (auth.uid() = user_id);

-- ポリシー: ユーザーは自分のジョブに関連する翻訳出力を参照可能
CREATE POLICY "Users can view their own translation outputs"
    ON translation_outputs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM translation_jobs
            WHERE translation_jobs.id = translation_outputs.job_id
            AND translation_jobs.user_id = auth.uid()
        )
    );

-- ポリシー: ユーザーは自分のジョブに対する翻訳出力を作成可能
CREATE POLICY "Users can create translation outputs for their jobs"
    ON translation_outputs
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM translation_jobs
            WHERE translation_jobs.id = translation_outputs.job_id
            AND translation_jobs.user_id = auth.uid()
        )
    );

-- ポリシー: ユーザーは自分のジョブに関連する図解を参照可能
CREATE POLICY "Users can view figures from their jobs"
    ON figures
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM translation_jobs
            WHERE translation_jobs.id = figures.job_id
            AND translation_jobs.user_id = auth.uid()
        )
    );

-- ============================================================================
-- Supabase Storage バケット設定
-- ============================================================================

-- ストレージバケット作成
INSERT INTO storage.buckets (id, name, public)
VALUES
    ('pdfs', 'pdfs', false),
    ('documents', 'documents', false),
    ('figures', 'figures', false)
ON CONFLICT (id) DO NOTHING;

-- ストレージポリシー: ユーザーは自分のファイルをアップロード可能
CREATE POLICY "Users can upload their own PDFs"
    ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'pdfs' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can upload their own documents"
    ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'documents' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can upload their own figures"
    ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'figures' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- ストレージポリシー: ユーザーは自分のファイルを参照可能
CREATE POLICY "Users can view their own PDFs"
    ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'pdfs' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can view their own documents"
    ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'documents' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can view their own figures"
    ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'figures' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- ============================================================================
-- インデックス最適化
-- ============================================================================

-- 複合インデックス
CREATE INDEX IF NOT EXISTS idx_translation_jobs_user_status
    ON translation_jobs(user_id, ocr_status);

CREATE INDEX IF NOT EXISTS idx_translation_outputs_job_status
    ON translation_outputs(job_id, status);

-- ============================================================================
-- ビュー（オプション）
-- ============================================================================

-- ジョブの詳細ビュー
CREATE OR REPLACE VIEW job_details AS
SELECT
    j.id,
    j.user_id,
    j.original_filename,
    j.pdf_url,
    j.page_count,
    j.japanese_markdown_url,
    j.ocr_status,
    j.ocr_error,
    j.created_at,
    j.updated_at,
    COUNT(DISTINCT o.id) AS translation_count,
    COUNT(DISTINCT f.id) AS figure_count
FROM translation_jobs j
LEFT JOIN translation_outputs o ON j.id = o.job_id
LEFT JOIN figures f ON j.id = f.job_id
GROUP BY j.id;

-- ============================================================================
-- コメント
-- ============================================================================

COMMENT ON TABLE translation_jobs IS '翻訳ジョブテーブル。PDFのアップロードとOCR処理を管理';
COMMENT ON TABLE translation_outputs IS '翻訳出力テーブル。各言語への翻訳結果を管理';
COMMENT ON TABLE figures IS '図解テーブル。抽出された図解を管理';

COMMENT ON COLUMN translation_jobs.japanese_markdown_url IS 'マスターマークダウンファイルのURL';
COMMENT ON COLUMN translation_jobs.layout_metadata IS 'レイアウト情報（書字方向、段組み等）';
COMMENT ON COLUMN translation_jobs.figures_data IS '図解の位置情報とメタデータ';

COMMENT ON COLUMN translation_outputs.translator_engine IS '使用した翻訳エンジン（claude or gemini）';
COMMENT ON COLUMN translation_outputs.cost_estimate IS '推定コスト（USD）';
