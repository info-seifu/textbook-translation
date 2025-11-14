import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '教科書翻訳アプリ',
  description: 'Google Gemini APIを活用した日本語教科書の多言語翻訳システム',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  )
}
