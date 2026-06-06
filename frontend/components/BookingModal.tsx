'use client'

import { useState, useEffect, useRef } from 'react'
import { X, CheckCircle, AlertCircle, Loader2, Mail, User, MessageSquare, Clock } from 'lucide-react'

interface BookingModalProps {
  isOpen: boolean
  onClose: () => void
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

// Slots fetched live from /slots endpoint
type FormState = 'idle' | 'loading' | 'success' | 'error'

export default function BookingModal({ isOpen, onClose }: BookingModalProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [note, setNote] = useState('')
  const [selectedSlot, setSelectedSlot] = useState<string>('')
  const [availableSlots, setAvailableSlots] = useState<string[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [formState, setFormState] = useState<FormState>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [meetingUrl, setMeetingUrl] = useState<string>('')
  const overlayRef = useRef<HTMLDivElement>(null)

  // Fetch available slots when modal opens
  useEffect(() => {
    if (!isOpen) return
    setSlotsLoading(true)
    fetch(`${BACKEND_URL}/slots`)
      .then(r => r.json())
      .then(data => {
        setAvailableSlots(data.slots || [])
      })
      .catch(() => setAvailableSlots([]))
      .finally(() => setSlotsLoading(false))
  }, [isOpen])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    if (isOpen) document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [isOpen, onClose])

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  const resetForm = () => {
    setName(''); setEmail(''); setNote(''); setSelectedSlot('')
    setFormState('idle'); setErrorMsg(''); setMeetingUrl('')
  }

  const handleClose = () => { if (formState === 'success') resetForm(); onClose() }

  // Format ISO slot for display
  const formatSlot = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString([], {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
      })
    } catch { return iso }
  }

  const handleSubmit = async () => {
    if (!name.trim() || !email.trim()) { setErrorMsg('Name and email are required.'); return }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setErrorMsg('Please enter a valid email.'); return }
    if (!selectedSlot) { setErrorMsg('Please select a time slot.'); return }
    setErrorMsg(''); setFormState('loading')

    try {
      const res = await fetch(`${BACKEND_URL}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // matches your BookRequest schema exactly
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          note: note.trim(),
          start_time: selectedSlot,   // ISO 8601 from Cal.com /slots
        }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d?.detail || `Error ${res.status}`)
      }
      const data = await res.json()
      setMeetingUrl(data.meeting_url || '')
      setFormState('success')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong.')
      setFormState('error')
    }
  }

  if (!isOpen) return null

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 16px', borderRadius: '12px',
    background: '#0d1a16', border: '1px solid rgba(61,107,88,0.25)',
    color: '#e8f0eb', fontSize: '14px', fontFamily: 'var(--font-sans)',
    caretColor: '#e8607a', transition: 'border-color 0.2s',
  }
  const focusBorder = (e: React.FocusEvent<any>) =>
    (e.target.style.borderColor = 'rgba(232,96,122,0.4)')
  const blurBorder = (e: React.FocusEvent<any>) =>
    (e.target.style.borderColor = 'rgba(61,107,88,0.25)')

  return (
    <div ref={overlayRef} className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={e => { if (e.target === overlayRef.current) handleClose() }}>
      <div className="absolute inset-0 backdrop-blur-sm animate-fade-in"
        style={{ background: 'rgba(13,26,22,0.85)' }} />

      <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="gradient-border rounded-2xl" style={{ background: '#111f1a' }}>
          <div className="p-6 sm:p-8">

            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <svg width="12" height="14" viewBox="0 0 16 20" fill="none">
                    <line x1="8" y1="20" x2="8" y2="11" stroke="#3d6b58" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M8 11 Q5 6 8 2 Q11 6 8 11Z" fill="#e8607a"/>
                    <path d="M8 10 Q4 7 4 3 Q7 6 8 10Z" fill="#c94468" opacity="0.8"/>
                    <path d="M8 10 Q12 7 12 3 Q9 6 8 10Z" fill="#c94468" opacity="0.8"/>
                  </svg>
                  <span className="text-[10px] font-mono tracking-widest uppercase" style={{ color: '#e8607a' }}>Schedule</span>
                </div>
                <h2 style={{ fontFamily: 'var(--font-display)', color: '#e8f0eb', fontSize: '1.4rem', fontWeight: 600 }}>
                  Book a Call
                </h2>
                <p className="text-sm mt-0.5" style={{ color: '#8aaa94' }}>
                  Pick a slot — a calendar invite goes out immediately.
                </p>
              </div>
              <button onClick={handleClose} className="p-2 rounded-lg transition-colors"
                style={{ color: '#4a6055' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#e8f0eb'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = '#4a6055'}>
                <X size={17} />
              </button>
            </div>

            {/* Success */}
            {formState === 'success' ? (
              <div className="text-center py-8 animate-fade-in">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                  style={{ background: 'rgba(232,96,122,0.1)', border: '1px solid rgba(232,96,122,0.3)' }}>
                  <CheckCircle size={26} style={{ color: '#e8607a' }} />
                </div>
                <h3 style={{ fontFamily: 'var(--font-display)', color: '#e8f0eb', fontSize: '1.2rem', fontWeight: 600 }} className="mb-2">
                  Booking Confirmed 🌷
                </h3>
                <p className="text-sm leading-relaxed mb-4" style={{ color: '#8aaa94' }}>
                  A calendar invite is on its way to{' '}
                  <span style={{ color: '#e8f0eb' }}>{email}</span>.
                </p>
                {meetingUrl && (
                  <a href={meetingUrl} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium mb-4 transition-all"
                    style={{ background: 'rgba(61,107,88,0.15)', border: '1px solid rgba(61,107,88,0.3)', color: '#8aaa94' }}>
                    Join Meeting Link →
                  </a>
                )}
                <br />
                <button onClick={handleClose}
                  className="px-5 py-2.5 rounded-xl text-sm font-medium transition-all mt-2"
                  style={{ background: 'rgba(232,96,122,0.1)', border: '1px solid rgba(232,96,122,0.3)', color: '#f2a0b0' }}>
                  Done
                </button>
              </div>
            ) : (
              <div className="space-y-5">

                {/* Name */}
                <div>
                  <label className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest mb-2" style={{ color: '#8aaa94' }}>
                    <User size={10} /> Name
                  </label>
                  <input type="text" value={name} onChange={e => setName(e.target.value)}
                    placeholder="Your full name" style={inputStyle}
                    onFocus={focusBorder} onBlur={blurBorder} />
                </div>

                {/* Email */}
                <div>
                  <label className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest mb-2" style={{ color: '#8aaa94' }}>
                    <Mail size={10} /> Email
                  </label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="your@email.com" style={inputStyle}
                    onFocus={focusBorder} onBlur={blurBorder} />
                </div>

                {/* Note */}
                <div>
                  <label className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest mb-2" style={{ color: '#8aaa94' }}>
                    <MessageSquare size={10} /> Note <span className="normal-case font-sans tracking-normal" style={{ color: '#4a6055', fontSize: '11px' }}>(optional)</span>
                  </label>
                  <textarea value={note} onChange={e => setNote(e.target.value)}
                    placeholder="What would you like to discuss?"
                    rows={2} style={{ ...inputStyle, resize: 'none' }}
                    onFocus={focusBorder} onBlur={blurBorder} />
                </div>

                {/* Time slots from Cal.com */}
                <div>
                  <label className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest mb-3" style={{ color: '#8aaa94' }}>
                    <Clock size={10} /> Available Slots
                    <span className="normal-case font-sans tracking-normal ml-1" style={{ color: '#4a6055', fontSize: '11px' }}>(next 7 days)</span>
                  </label>

                  {slotsLoading ? (
                    <div className="flex items-center gap-2 py-4" style={{ color: '#4a6055' }}>
                      <Loader2 size={14} className="animate-spin" />
                      <span className="text-xs font-mono">Fetching available slots…</span>
                    </div>
                  ) : availableSlots.length === 0 ? (
                    <p className="text-xs py-3 px-4 rounded-xl" style={{ color: '#4a6055', background: '#0d1a16', border: '1px solid rgba(61,107,88,0.15)' }}>
                      No slots available right now. Try again later or drop a note anyway.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1">
                      {availableSlots.map(slot => {
                        const active = selectedSlot === slot
                        return (
                          <button key={slot} type="button" onClick={() => setSelectedSlot(slot)}
                            className="flex items-center px-4 py-2.5 rounded-xl text-xs text-left transition-all"
                            style={{
                              background: active ? 'rgba(232,96,122,0.1)' : '#0d1a16',
                              border: `1px solid ${active ? 'rgba(232,96,122,0.4)' : 'rgba(61,107,88,0.2)'}`,
                              color: active ? '#f2a0b0' : '#8aaa94',
                            }}>
                            {formatSlot(slot)}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Error */}
                {errorMsg && (
                  <div className="flex items-start gap-2.5 p-3 rounded-lg"
                    style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.18)' }}>
                    <AlertCircle size={14} className="shrink-0 mt-0.5" style={{ color: '#f87171' }} />
                    <p className="text-xs leading-relaxed" style={{ color: '#f87171' }}>{errorMsg}</p>
                  </div>
                )}

                {/* Submit */}
                <button onClick={handleSubmit} disabled={formState === 'loading'}
                  className="w-full py-3.5 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2"
                  style={{
                    background: 'linear-gradient(135deg, #e8607a, #c94468)',
                    color: '#fff',
                    opacity: formState === 'loading' ? 0.6 : 1,
                    cursor: formState === 'loading' ? 'not-allowed' : 'pointer',
                  }}>
                  {formState === 'loading'
                    ? <><Loader2 size={14} className="animate-spin" /> Booking…</>
                    : 'Confirm Booking 🌷'}
                </button>

              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
