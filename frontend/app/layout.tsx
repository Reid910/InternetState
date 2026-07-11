import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Internet State',
  description: 'A live summary of the web',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            var stored = localStorage.getItem('theme');
            var systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (stored === 'dark' || (!stored && systemDark)) {
              document.documentElement.setAttribute('data-theme', 'dark');
            } else if (stored === 'light') {
              document.documentElement.setAttribute('data-theme', 'light');
            }
          })()
        `}} />
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}
