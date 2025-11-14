'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { uploadPDF } from '@/lib/api'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string>('')
  const router = useRouter()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]

      // ファイルタイプチェック
      if (!selectedFile.name.endsWith('.pdf')) {
        setError('PDFファイルのみアップロード可能です')
        return
      }

      // ファイルサイズチェック（50MB）
      const maxSize = 50 * 1024 * 1024
      if (selectedFile.size > maxSize) {
        setError('ファイルサイズは50MB以下にしてください')
        return
      }

      setFile(selectedFile)
      setError('')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('ファイルを選択してください')
      return
    }

    setUploading(true)
    setError('')

    try {
      const response = await uploadPDF(file)
      console.log('Upload response:', response)

      // ジョブ詳細ページへリダイレクト
      router.push(`/jobs/${response.job_id}`)
    } catch (err: any) {
      console.error('Upload error:', err)
      setError(err.response?.data?.detail || 'アップロードに失敗しました')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              PDFアップロード
            </h1>
            <p className="text-gray-600">
              翻訳したい日本語教科書のPDFファイルをアップロードしてください
            </p>
          </div>

          {/* Upload Area */}
          <div className="bg-white rounded-lg shadow-md p-8">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-400 transition-colors">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
                disabled={uploading}
              />
              <label
                htmlFor="file-upload"
                className={`cursor-pointer ${uploading ? 'opacity-50' : ''}`}
              >
                <div className="text-6xl mb-4">📄</div>
                <p className="text-lg font-semibold text-gray-700 mb-2">
                  クリックしてファイルを選択
                </p>
                <p className="text-sm text-gray-500">
                  または、ここにドラッグ&ドロップ
                </p>
                <p className="text-xs text-gray-400 mt-4">
                  PDF形式、最大50MB
                </p>
              </label>
            </div>

            {/* Selected File */}
            {file && (
              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">📄</span>
                    <div>
                      <p className="font-semibold text-gray-900">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setFile(null)}
                    className="text-red-600 hover:text-red-700 font-semibold"
                    disabled={uploading}
                  >
                    削除
                  </button>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700">{error}</p>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className={`mt-6 w-full py-4 rounded-lg font-semibold text-white transition-colors ${
                !file || uploading
                  ? 'bg-gray-300 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {uploading ? 'アップロード中...' : 'アップロード開始'}
            </button>

            {/* Info */}
            <div className="mt-8 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">📝 注意事項</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 縦書き・横書きは自動判定されます</li>
                <li>• OCR処理には数分かかる場合があります</li>
                <li>• アップロード後、自動的にOCR処理が開始されます</li>
              </ul>
            </div>
          </div>

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
