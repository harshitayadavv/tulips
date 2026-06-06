'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, AlertTriangle, ChevronRight } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  warning?: string
  timestamp: Date
}

interface ChatWindowProps {
  onOpenBooking: () => void
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

const SUGGESTED_QUESTIONS = [
  "What's your technical stack?",
  "Tell me about your experience",
  "What kind of roles are you open to?",
  "Describe a project you're proud of",
]

function TulipAvatar() {
  return (
    <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
      style={{ background: 'linear-gradient(135deg, #1f2e25, #1a2820)', border: '1px solid rgba(232,96,122,0.25)' }}>
      <svg width="16" height="18" viewBox="0 0 16 20" fill="none">
        <line x1="8" y1="20" x2="8" y2="11" stroke="#3d6b58" strokeWidth="1.2" strokeLinecap="round"/>
        <path d="M8 11 Q5 6 8 2 Q11 6 8 11Z" fill="#e8607a"/>
        <path d="M8 10 Q4 7 4 3 Q7 6 8 10Z" fill="#c94468" opacity="0.8"/>
        <path d="M8 10 Q12 7 12 3 Q9 6 8 10Z" fill="#c94468" opacity="0.8"/>
      </svg>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 message-enter">
      <TulipAvatar />
      <div className="px-4 py-3.5 rounded-2xl rounded-bl-sm"
        style={{ background: '#1a2820', border: '1px solid rgba(61,107,88,0.25)' }}>
        <div className="flex items-center gap-1.5 h-4">
          {[0, 1, 2].map(i => (
            <div key={i}
              className="w-1.5 h-1.5 rounded-full animate-pulse-dot"
              style={{ background: '#e8607a', opacity: 0.7, animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function WarningBanner({ warning }: { warning: string }) {
  return (
    <div className="warning-banner rounded-lg px-3.5 py-2.5 mt-2 flex items-start gap-2.5">
      <AlertTriangle size={13} className="shrink-0 mt-0.5" style={{ color: '#d4a853' }} />
      <p className="text-xs leading-relaxed" style={{ color: 'rgba(212,168,83,0.85)' }}>{warning}</p>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex items-end gap-3 message-enter ${isUser ? 'flex-row-reverse' : ''}`}>
      {!isUser && <TulipAvatar />}
      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`px-4 py-3 text-sm leading-relaxed ${isUser ? 'rounded-2xl rounded-br-sm' : 'rounded-2xl rounded-bl-sm'}`}
          style={isUser
            ? { background: 'linear-gradient(135deg, rgba(232,96,122,0.15), rgba(201,68,104,0.08))', border: '1px solid rgba(232,96,122,0.22)', color: '#e8f0eb' }
            : { background: '#1a2820', border: '1px solid rgba(61,107,88,0.2)', color: '#d4e8da' }
          }
        >
          <p className="whitespace-pre-wrap">
            {message.content}
            {/* blinking cursor while streaming */}
            {message.role === 'assistant' && (message as any).streaming && (
              <span className="cursor-blink inline-block w-0.5 h-3.5 bg-current ml-0.5 align-middle" />
            )}
          </p>
        </div>
        {message.warning && <WarningBanner warning={message.warning} />}
        {!(message as any).streaming && (
          <span className="text-[10px] px-1" style={{ color: '#4a6055', fontFamily: 'var(--font-mono)' }}>
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

function CalendarIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  )
}

export default function ChatWindow({ onOpenBooking }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [hasStarted, setHasStarted] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isTyping || isStreaming) return
    if (!hasStarted) setHasStarted(true)
    setInput('')

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsTyping(true)

    // Create a placeholder assistant message for streaming
    const assistantId = `a-${Date.now()}`

    try {
      abortRef.current = new AbortController()

      const res = await fetch(`${BACKEND_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
        signal: abortRef.current.signal,
      })

      if (!res.ok) {
        // fallback to non-streaming endpoint
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.detail || `Server ${res.status}`)
      }

      if (!res.body) throw new Error('No response body')

      setIsTyping(false)
      setIsStreaming(true)

      // Add empty streaming message
      setMessages(prev => [...prev, {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        streaming: true,
      } as any])

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })

        // Parse SSE lines: "data: <text>\n\n"
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const piece = line.slice(6)
            if (piece === '[DONE]') break
            accumulated += piece
            setMessages(prev =>
              prev.map(m => m.id === assistantId
                ? { ...m, content: accumulated, streaming: true } as any
                : m
              )
            )
          }
        }
      }

      // Finalise — remove streaming flag
      setMessages(prev =>
        prev.map(m => m.id === assistantId
          ? { ...m, content: accumulated, streaming: false } as any
          : m
        )
      )

    } catch (err: any) {
      if (err?.name === 'AbortError') return

      // Try falling back to non-streaming /chat
      try {
        const res2 = await fetch(`${BACKEND_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: trimmed }),
        })
        const data = await res2.json()
        const content = data.response || data.message || data.content || JSON.stringify(data)
        setMessages(prev => {
          // Remove empty streaming placeholder if it exists
          const filtered = prev.filter(m => m.id !== assistantId)
          return [...filtered, { id: assistantId, role: 'assistant', content, timestamp: new Date() }]
        })
      } catch {
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== assistantId)
          return [...filtered, {
            id: `e-${Date.now()}`,
            role: 'assistant',
            content: "I'm having trouble connecting right now. Please try again in a moment.",
            timestamp: new Date(),
          }]
        })
      }
    } finally {
      setIsTyping(false)
      setIsStreaming(false)
    }
  }, [isTyping, isStreaming, hasStarted])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input) }
  }

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  const busy = isTyping || isStreaming

  return (
    <div className="flex flex-col h-full">

      {/* Empty / intro state */}
      {!hasStarted && messages.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 animate-fade-in">
          <div className="relative mb-6 animate-petal">
            <svg width="64" height="72" viewBox="0 0 32 36" fill="none">
              <line x1="16" y1="36" x2="16" y2="18" stroke="#3d6b58" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M16 28 Q10 24 11 18 Q15 22 16 28Z" fill="#3d6b58" opacity="0.7"/>
              <path d="M16 18 Q13 10 16 4 Q19 10 16 18Z" fill="#e8607a"/>
              <path d="M16 16 Q9 11 9 5 Q14 9 16 16Z" fill="#c94468" opacity="0.85"/>
              <path d="M16 16 Q23 11 23 5 Q18 9 16 16Z" fill="#c94468" opacity="0.85"/>
            </svg>
            <div className="absolute top-1 right-0 w-1.5 h-1.5 rounded-full animate-pollen" style={{ background: '#d4a853', animationDelay: '0.5s' }} />
            <div className="absolute top-3 left-0 w-1 h-1 rounded-full animate-pollen" style={{ background: '#d4a853', animationDelay: '1.2s' }} />
          </div>

          <div className="flex items-center gap-2 mb-5 px-3 py-1.5 rounded-full"
            style={{ background: 'rgba(61,107,88,0.12)', border: '1px solid rgba(61,107,88,0.25)' }}>
            <div className="w-1.5 h-1.5 rounded-full animate-pollen" style={{ background: '#3d6b58' }} />
            <span className="text-xs font-mono" style={{ color: '#8aaa94' }}>blooming · ready to chat</span>
          </div>

          <h1 className="text-2xl sm:text-[2rem] font-semibold text-center leading-tight mb-2"
            style={{ fontFamily: 'var(--font-display)', color: '#e8f0eb', letterSpacing: '0.02em' }}>
            Hi, I'm&nbsp;
            <span style={{ color: '#f2a0b0', fontStyle: 'italic' }}>Harshita's</span>
            <br />AI Representative
          </h1>
          <p className="text-center text-sm leading-relaxed max-w-sm mb-8" style={{ color: '#8aaa94' }}>
            Ask me anything about experience, skills, and projects. Or book a call to connect directly.
          </p>

          <div className="w-full max-w-sm space-y-2">
            <p className="text-[10px] font-mono text-center uppercase tracking-widest mb-3" style={{ color: '#4a6055' }}>
              ✦ try asking
            </p>
            {SUGGESTED_QUESTIONS.map(q => (
              <button key={q} onClick={() => sendMessage(q)}
                className="w-full flex items-center justify-between px-4 py-3 text-left text-sm transition-all rounded-xl"
                style={{ background: '#1a2820', border: '1px solid rgba(61,107,88,0.18)', color: '#8aaa94' }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(232,96,122,0.3)'
                  ;(e.currentTarget as HTMLElement).style.color = '#e8f0eb'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(61,107,88,0.18)'
                  ;(e.currentTarget as HTMLElement).style.color = '#8aaa94'
                }}
              >
                <span>{q}</span>
                <ChevronRight size={13} style={{ color: '#4a6055', flexShrink: 0, marginLeft: 8 }} />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      {(hasStarted || messages.length > 0) && (
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-5">
          {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 px-4 sm:px-6 pb-6 pt-3">
        {messages.some(m => m.role === 'assistant') && (
          <div className="flex justify-center mb-3 animate-fade-in">
            <button onClick={onOpenBooking}
              className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all"
              style={{ border: '1px solid rgba(232,96,122,0.25)', color: '#f2a0b0', background: 'rgba(232,96,122,0.06)' }}
              onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(232,96,122,0.12)'}
              onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'rgba(232,96,122,0.06)'}
            >
              <CalendarIcon size={11} />
              Book a Call
            </button>
          </div>
        )}

        <div className="gradient-border rounded-2xl">
          <div className="flex items-end gap-3 px-4 py-3 rounded-2xl" style={{ background: '#111f1a' }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything…"
              rows={1}
              disabled={busy}
              className="flex-1 bg-transparent text-sm resize-none leading-relaxed max-h-[120px] py-1 disabled:opacity-50"
              style={{ color: '#e8f0eb', caretColor: '#e8607a', fontFamily: 'var(--font-sans)' }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || busy}
              className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all"
              style={{
                background: input.trim() && !busy ? 'linear-gradient(135deg, #e8607a, #c94468)' : 'rgba(255,255,255,0.06)',
                color: input.trim() && !busy ? '#fff' : '#4a6055',
                cursor: !input.trim() || busy ? 'not-allowed' : 'pointer',
              }}
            >
              <Send size={13} />
            </button>
          </div>
        </div>
        <p className="text-center mt-2" style={{ fontSize: '10px', color: '#4a6055', fontFamily: 'var(--font-mono)' }}>
          Enter to send · Shift+Enter for new line
        </p>
      </div>

    </div>
  )
}
