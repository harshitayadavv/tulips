'use client'

import { useState } from 'react'
import ChatWindow from '@/components/ChatWindow'
import BookingModal from '@/components/BookingModal'
import { Calendar, Github, Linkedin, Globe } from 'lucide-react'

// Inline tulip SVG mark
function TulipMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* stem */}
      <line x1="16" y1="36" x2="16" y2="18" stroke="#3d6b58" strokeWidth="1.5" strokeLinecap="round"/>
      {/* leaf */}
      <path d="M16 28 Q10 24 11 18 Q15 22 16 28Z" fill="#3d6b58" opacity="0.7"/>
      {/* center petal */}
      <path d="M16 18 Q13 10 16 4 Q19 10 16 18Z" fill="#e8607a"/>
      {/* left petal */}
      <path d="M16 16 Q9 11 9 5 Q14 9 16 16Z" fill="#c94468" opacity="0.85"/>
      {/* right petal */}
      <path d="M16 16 Q23 11 23 5 Q18 9 16 16Z" fill="#c94468" opacity="0.85"/>
    </svg>
  )
}

export default function HomePage() {
  const [bookingOpen, setBookingOpen] = useState(false)

  return (
    <div className="min-h-screen petal-bg flex flex-col" style={{ position: 'relative', zIndex: 1 }}>

      {/* Ambient botanical glow orbs */}
      <div className="fixed top-0 right-1/3 w-[500px] h-[500px] rounded-full pointer-events-none" style={{
        background: 'radial-gradient(circle, rgba(232,96,122,0.05) 0%, transparent 65%)',
        transform: 'translateY(-40%)',
        zIndex: 0,
      }} />
      <div className="fixed bottom-0 left-1/4 w-[400px] h-[400px] rounded-full pointer-events-none" style={{
        background: 'radial-gradient(circle, rgba(61,107,88,0.07) 0%, transparent 65%)',
        transform: 'translateY(30%)',
        zIndex: 0,
      }} />

      <div className="relative z-10 flex flex-col min-h-screen max-w-3xl mx-auto w-full">

        {/* Header */}
        <header className="flex items-center justify-between px-5 sm:px-7 py-4">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="animate-petal">
              <TulipMark size={30} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)' }}
                className="text-xl font-semibold tracking-wide leading-none"
                style2={{ color: '#e8f0eb', fontFamily: 'var(--font-display)' }}>
                <span className="text-[#e8f0eb]" style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600, letterSpacing: '0.05em' }}>
                  tulips
                </span>
              </div>
              <div className="text-[10px] font-mono text-[#4a6055] tracking-widest uppercase mt-0.5">
                AI · Representative
              </div>
            </div>
          </div>

          {/* Nav */}
          <div className="flex items-center gap-1.5">
            <a href="https://github.com/harshitayadavv" target="_blank" rel="noopener noreferrer"
              className="p-2 rounded-lg text-[#4a6055] hover:text-[#e8f0eb] hover:bg-white/4 transition-colors" aria-label="GitHub">
              <Github size={14} />
            </a>
            <a href="https://www.linkedin.com/in/harshitayadav504/" target="_blank" rel="noopener noreferrer"
              className="p-2 rounded-lg text-[#4a6055] hover:text-[#e8f0eb] hover:bg-white/4 transition-colors" aria-label="LinkedIn">
              <Linkedin size={14} />
            </a>
            <a href="https://harshitayadav-portfolio.vercel.app/" target="_blank" rel="noopener noreferrer"
              className="p-2 rounded-lg text-[#4a6055] hover:text-[#e8f0eb] hover:bg-white/4 transition-colors" aria-label="Portfolio">
              <Globe size={14} />
            </a>
            <div className="w-px h-4 bg-white/6 mx-1" />
            <button
              onClick={() => setBookingOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg border border-[#e8607a]/30 text-[#f2a0b0] bg-[#e8607a]/8 hover:bg-[#e8607a]/15 hover:border-[#e8607a]/50 transition-all"
            >
              <Calendar size={11} />
              Book a Call
            </button>
          </div>
        </header>

        {/* Stem divider */}
        <div className="stem-line mx-5 sm:mx-7" />

        {/* Chat */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow onOpenBooking={() => setBookingOpen(true)} />
        </main>

        {/* Footer */}
        <div className="stem-line mx-5 sm:mx-7" />
        <footer className="px-6 py-3 flex items-center justify-between">
          <p className="text-[10px] font-mono text-[#4a6055]">
            tulips · AI-powered · not always perfect
          </p>
          <div className="flex items-center gap-1.5">
            <div className="w-1 h-1 rounded-full bg-[#3d6b58] animate-pollen" />
            <p className="text-[10px] font-mono text-[#4a6055]">online</p>
          </div>
        </footer>

      </div>

      <BookingModal isOpen={bookingOpen} onClose={() => setBookingOpen(false)} />
    </div>
  )
}
