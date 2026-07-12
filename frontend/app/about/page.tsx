'use client'

import Link from 'next/link'
import ThemeToggle from '../ThemeToggle'
import { useState } from 'react'

function CopyEmail({ email }: { email: string }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(email)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button onClick={copy} className="nav-btn" style={{ fontSize: '0.9rem', padding: '0.35rem 0.75rem' }}>
      {copied ? 'Copied!' : email}
    </button>
  )
}

export default function AboutPage() {
  return (
    <main className="page-main">
      <header className="site-header">
        <div className="site-title">
          <a href="/"><h1>Internet State</h1></a>
          <ThemeToggle />
        </div>
        <div className="header-meta">
          <Link href="/" className="nav-btn" style={{ marginLeft: 'auto' }}>Home</Link>
        </div>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>

        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 0.6rem' }}>
            What is Internet State?
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: '1.8', margin: 0, textIndent: '2rem' }}>
            The internet produces an overwhelming amount of information every day. Internet State exists to make sense of it —
            pulling in articles from sources across the web, using modern AI to summarize and cluster them into coherent stories,
            and presenting a clean, real-time picture of what the world is actually talking about. No algorithm optimizing for
            engagement, no ads, no noise. Just the news.
          </p>
        </div>

        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 0.6rem' }}>
            How it works
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: '1.8', margin: '0 0 0.75rem', textIndent: '2rem' }}>
            A scheduled worker continuously ingests articles from RSS feeds across the web. Each article is summarized and
            converted into a vector embedding using AI. A clustering step then groups articles covering the same event by
            semantic similarity and generates a unified headline and summary for each story.
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: '1.8', margin: 0, textIndent: '2rem' }}>
            Built on a modern serverless stack — cloud functions, a vector-capable database, and a server-rendered
            frontend — the whole system runs automatically and stays up to date without manual intervention.
          </p>
        </div>

        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 0.6rem' }}>
            About me
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: '1.8', margin: 0, textIndent: '2rem' }}>
            I&apos;m Sam, a software engineering student at Renton Technical College. I built Internet State because I wanted
            to do something meaningful with the flood of information the internet produces every day — and because the best
            way to learn modern infrastructure and AI is to build something real with it. I&apos;m interested in the intersection
            of software engineering and the way information moves through the world, and this project sits right at the center of that.
          </p>
        </div>

        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 0.75rem' }}>
            Get in touch
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-start' }}>
            <CopyEmail email="samn10.nelson@gmail.com" />
            <a href="https://github.com/Reid910" target="_blank" rel="noopener noreferrer"
              className="nav-btn" style={{ fontSize: '0.9rem', padding: '0.35rem 0.75rem' }}>
              github.com/Reid910
            </a>
          </div>
        </div>

      </div>
    </main>
  )
}
