/**
 * バックエンドAPI クライアント
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface UploadResponse {
  job_id: string
  status: string
  message: string
}

export interface JobStatus {
  job: {
    id: string
    original_filename: string
    pdf_url: string
    page_count: number | null
    japanese_markdown_url: string | null
    layout_metadata: any
    ocr_status: 'pending' | 'processing' | 'completed' | 'failed'
    ocr_error: string | null
    created_at: string
    updated_at: string
  }
  translations: Translation[]
}

export interface Translation {
  id: string
  job_id: string
  target_language: string
  translator_engine: 'gemini' | 'claude'
  translated_markdown_url: string | null
  html_url: string | null
  pdf_url: string | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  created_at: string
}

export interface TranslateRequest {
  job_id: string
  target_language: string
  translator_engine?: 'gemini' | 'claude'
}

export interface TranslateResponse {
  output_id: string
  status: string
  message: string
}

/**
 * PDFファイルをアップロード
 */
export async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

/**
 * ジョブのステータスを取得
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch job status')
  }

  return response.json()
}

/**
 * 翻訳を開始
 */
export async function startTranslation(
  request: TranslateRequest
): Promise<TranslateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start translation')
  }

  return response.json()
}

/**
 * 翻訳出力のステータスを取得
 */
export async function getOutputStatus(outputId: string): Promise<Translation> {
  const response = await fetch(`${API_BASE_URL}/api/outputs/${outputId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch output status')
  }

  return response.json()
}

/**
 * マークダウンファイルをダウンロード
 */
export async function downloadMarkdown(outputId: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/download/${outputId}/markdown`
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to download markdown')
  }

  return response.blob()
}

/**
 * HTMLファイルをダウンロード
 */
export async function downloadHTML(outputId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/download/${outputId}/html`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to download HTML')
  }

  return response.blob()
}

/**
 * PDFファイルをダウンロード
 */
export async function downloadPDF(outputId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/download/${outputId}/pdf`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to download PDF')
  }

  return response.blob()
}

/**
 * Docxファイルをダウンロード
 */
export async function downloadDocx(outputId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/download/${outputId}/docx`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to download Docx')
  }

  return response.blob()
}
