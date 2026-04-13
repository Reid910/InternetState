import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Internet State',
  description: 'A live summary of the web',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: '#f5f5f5', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        {children}
      </body>
    </html>
  )
}
