import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: "Tulips · AI Representative",
  description: "Chat with Tulips — an AI persona built to represent me for job applications.",
  openGraph: {
    title: "Tulips — AI Chat",
    description: "Ask me anything about my background, skills, and experience.",
    type: "website",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  )
}
