'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              教科書翻訳アプリ
            </h1>
            <p className="text-xl text-gray-600">
              Google Gemini APIを活用した日本語教科書の多言語翻訳システム
            </p>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-3xl mb-3">📖</div>
              <h3 className="text-lg font-semibold mb-2">自動書字方向判定</h3>
              <p className="text-gray-600 text-sm">
                縦書き・横書きを自動認識
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-3xl mb-3">🎯</div>
              <h3 className="text-lg font-semibold mb-2">高精度OCR</h3>
              <p className="text-gray-600 text-sm">
                Gemini 2.5 Proによる高品質抽出
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-3xl mb-3">🌍</div>
              <h3 className="text-lg font-semibold mb-2">多言語対応</h3>
              <p className="text-gray-600 text-sm">
                英語、中国語、韓国語など
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center">
            <Link
              href="/upload"
              className="inline-block bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              翻訳を開始する
            </Link>
          </div>

          {/* How it works */}
          <div className="mt-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
              使い方
            </h2>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="bg-blue-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-blue-600 font-bold">
                  1
                </div>
                <p className="text-sm text-gray-700">PDFアップロード</p>
              </div>
              <div className="text-center">
                <div className="bg-blue-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-blue-600 font-bold">
                  2
                </div>
                <p className="text-sm text-gray-700">OCR処理</p>
              </div>
              <div className="text-center">
                <div className="bg-blue-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-blue-600 font-bold">
                  3
                </div>
                <p className="text-sm text-gray-700">言語選択</p>
              </div>
              <div className="text-center">
                <div className="bg-blue-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-blue-600 font-bold">
                  4
                </div>
                <p className="text-sm text-gray-700">ダウンロード</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
