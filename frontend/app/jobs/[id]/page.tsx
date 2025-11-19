'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getJobStatus, startTranslation, downloadMarkdown } from '@/lib/api'

interface Job {
  id: string
  original_filename: string
  pdf_url: string
  page_count: number | null
  japanese_markdown_url: string | null
  ocr_status: 'pending' | 'processing' | 'completed' | 'failed'
  ocr_error: string | null
  created_at: string
  updated_at: string
}

interface Translation {
  id: string
  job_id: string
  target_language: string
  translator_engine: 'claude' | 'gemini'
  translated_markdown_url: string | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  created_at: string
}

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null>(null)
  const [translations, setTranslations] = useState<Translation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [targetLanguage, setTargetLanguage] = useState('en')
  const [translatorEngine, setTranslatorEngine] = useState<'claude' | 'gemini'>('claude')
  const [startingTranslation, setStartingTranslation] = useState(false)

  const router = useRouter()

  const loadJobStatus = async () => {
    try {
      const data = await getJobStatus(params.id)
      setJob(data.job)
      setTranslations(data.translations || [])
      setError('')
    } catch (err: any) {
      console.error('Failed to load job status:', err)
      setError('ジョブ情報の取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobStatus()

    // 定期的にステータスを更新
    const interval = setInterval(() => {
      if (job?.ocr_status === 'processing' || translations.some(t => t.status === 'processing')) {
        loadJobStatus()
      }
    }, 3000) // 3秒ごと

    return () => clearInterval(interval)
  }, [params.id, job?.ocr_status])

  const handleStartTranslation = async () => {
    setStartingTranslation(true)
    setError('')

    try {
      await startTranslation({
        job_id: params.id,
        target_language: targetLanguage,
        translator_engine: translatorEngine
      })
      // ステータスを再読み込み
      await loadJobStatus()
    } catch (err: any) {
      console.error('Failed to start translation:', err)
      setError(err.response?.data?.detail || '翻訳開始に失敗しました')
    } finally {
      setStartingTranslation(false)
    }
  }

  const handleDownload = async (outputId: string, language: string) => {
    try {
      const blob = await downloadMarkdown(outputId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `translated_${language}.md`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
      alert('ダウンロードに失敗しました')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">⏳</div>
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">ジョブが見つかりません</p>
        </div>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; text: string; emoji: string }> = {
      pending: { color: 'bg-yellow-100 text-yellow-800', text: '待機中', emoji: '⏳' },
      processing: { color: 'bg-blue-100 text-blue-800', text: '処理中', emoji: '🔄' },
      completed: { color: 'bg-green-100 text-green-800', text: '完了', emoji: '✅' },
      failed: { color: 'bg-red-100 text-red-800', text: '失敗', emoji: '❌' },
    }

    const badge = badges[status] || badges.pending

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${badge.color}`}>
        <span className="mr-1">{badge.emoji}</span>
        {badge.text}
      </span>
    )
  }

  const languageNames: Record<string, string> = {
    en: '英語',
    zh: '中国語（簡体字）',
    'zh-TW': '中国語（繁体字）',
    ko: '韓国語',
    vi: 'ベトナム語',
    th: 'タイ語',
    es: 'スペイン語',
    fr: 'フランス語',
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">ジョブ詳細</h1>
            <p className="text-gray-600">Job ID: {job.id}</p>
          </div>

          {/* Job Info */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">ファイル情報</h2>
            <div className="space-y-2">
              <p><strong>ファイル名:</strong> {job.original_filename}</p>
              <p><strong>ページ数:</strong> {job.page_count || '計測中...'}</p>
              <p><strong>OCRステータス:</strong> {getStatusBadge(job.ocr_status)}</p>
              {job.ocr_error && (
                <p className="text-red-600"><strong>エラー:</strong> {job.ocr_error}</p>
              )}
            </div>
          </div>

          {/* OCR Progress */}
          {job.ocr_status === 'processing' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="flex items-center">
                <div className="text-4xl mr-4">🔄</div>
                <div>
                  <h3 className="font-bold text-gray-900">OCR処理中...</h3>
                  <p className="text-gray-600">テキスト抽出を行っています。しばらくお待ちください。</p>
                </div>
              </div>
            </div>
          )}

          {/* Translation Form */}
          {job.ocr_status === 'completed' && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">翻訳開始</h2>

              <div className="space-y-4">
                <div>
                  <label className="block font-semibold text-gray-700 mb-2">翻訳先言語</label>
                  <select
                    value={targetLanguage}
                    onChange={(e) => setTargetLanguage(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {Object.entries(languageNames).map(([code, name]) => (
                      <option key={code} value={code}>
                        {name} ({code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-2">翻訳エンジン</label>
                  <select
                    value={translatorEngine}
                    onChange={(e) => setTranslatorEngine(e.target.value as 'claude' | 'gemini')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="claude">Claude Sonnet（高品質・推奨）</option>
                    <option value="gemini">Gemini Flash（高速・低コスト）</option>
                  </select>
                </div>

                {error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-700">{error}</p>
                  </div>
                )}

                <button
                  onClick={handleStartTranslation}
                  disabled={startingTranslation}
                  className={`w-full py-3 rounded-lg font-semibold text-white transition-colors ${
                    startingTranslation
                      ? 'bg-gray-300 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {startingTranslation ? '翻訳を開始中...' : '翻訳を開始'}
                </button>
              </div>
            </div>
          )}

          {/* Translations List */}
          {translations.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">翻訳一覧</h2>
              <div className="space-y-4">
                {translations.map((translation) => (
                  <div
                    key={translation.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-semibold text-gray-900">
                          {languageNames[translation.target_language]} ({translation.target_language})
                        </p>
                        <p className="text-sm text-gray-500">
                          エンジン: {translation.translator_engine === 'claude' ? 'Claude Sonnet' : 'Gemini Flash'}
                        </p>
                      </div>
                      {getStatusBadge(translation.status)}
                    </div>

                    {translation.error_message && (
                      <p className="text-red-600 text-sm mb-2">{translation.error_message}</p>
                    )}

                    {translation.status === 'completed' && (
                      <button
                        onClick={() => handleDownload(translation.id, translation.target_language)}
                        className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                      >
                        ダウンロード
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Back Button */}
          <div className="mt-6 text-center">
            <button
              onClick={() => router.push('/')}
              className="text-blue-600 hover:text-blue-700 font-semibold"
            >
              ← トップページへ戻る
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
