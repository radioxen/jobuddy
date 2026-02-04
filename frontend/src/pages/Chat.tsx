import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Zap } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'

export default function Chat() {
  const { connected, chatMessages, statusUpdates, sendMessage } = useWebSocket()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, statusUpdates])

  const handleSend = () => {
    if (!input.trim()) return
    sendMessage(input.trim())
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Merge chat and status messages into a timeline
  const timeline = [
    ...chatMessages.map((m, i) => ({
      type: 'chat' as const,
      data: m,
      time: m.timestamp || new Date().toISOString(),
      key: `chat-${i}`,
    })),
    ...statusUpdates.map((s, i) => ({
      type: 'status' as const,
      data: s,
      time: s.timestamp,
      key: `status-${i}`,
    })),
  ].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

  const quickActions = [
    'Start searching for jobs',
    'Show my top matches',
    'Approve all jobs scoring above 75',
    'Prepare documents for all approved jobs',
    'What is my application status?',
    'Open LinkedIn login',
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Chat</h1>
        <div
          style={{
            fontSize: 12,
            color: connected ? '#4CAF50' : '#f44336',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: connected ? '#4CAF50' : '#f44336',
            }}
          />
          {connected ? 'Connected' : 'Reconnecting...'}
        </div>
      </div>

      {/* Messages area */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          background: '#fff',
          borderRadius: 12,
          padding: 16,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          marginBottom: 16,
        }}
      >
        {timeline.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <Bot size={48} style={{ color: '#ccc', marginBottom: 16 }} />
            <h3 style={{ color: '#666', marginBottom: 8 }}>Welcome to JobBuddy Chat</h3>
            <p style={{ color: '#999', fontSize: 14, marginBottom: 24 }}>
              I can help you search for jobs, approve applications, prepare documents, and more.
              Try one of the quick actions below or type your own message.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {quickActions.map((action) => (
                <button
                  key={action}
                  onClick={() => sendMessage(action)}
                  style={{
                    padding: '8px 14px',
                    background: '#f5f5f5',
                    border: '1px solid #e0e0e0',
                    borderRadius: 20,
                    cursor: 'pointer',
                    fontSize: 13,
                    color: '#333',
                    transition: 'all 0.2s',
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = '#e3f2fd'
                    e.currentTarget.style.borderColor = '#90caf9'
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = '#f5f5f5'
                    e.currentTarget.style.borderColor = '#e0e0e0'
                  }}
                >
                  {action}
                </button>
              ))}
            </div>
          </div>
        ) : (
          timeline.map((item) => {
            if (item.type === 'chat') {
              const msg = item.data
              const isUser = msg.role === 'user'
              return (
                <div
                  key={item.key}
                  style={{
                    display: 'flex',
                    justifyContent: isUser ? 'flex-end' : 'flex-start',
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      maxWidth: '70%',
                      display: 'flex',
                      gap: 10,
                      flexDirection: isUser ? 'row-reverse' : 'row',
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: '50%',
                        background: isUser ? '#1a1a2e' : '#4CAF50',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {isUser ? (
                        <User size={16} color="#fff" />
                      ) : (
                        <Bot size={16} color="#fff" />
                      )}
                    </div>
                    <div
                      style={{
                        background: isUser ? '#1a1a2e' : '#f5f5f5',
                        color: isUser ? '#fff' : '#333',
                        padding: '10px 14px',
                        borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                        fontSize: 14,
                        lineHeight: 1.5,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {msg.content}
                    </div>
                  </div>
                </div>
              )
            } else {
              // Status update
              const status = item.data
              return (
                <div
                  key={item.key}
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      background: '#e3f2fd',
                      padding: '6px 12px',
                      borderRadius: 20,
                      fontSize: 12,
                      color: '#1565c0',
                    }}
                  >
                    <Zap size={12} />
                    {status.payload?.message || status.payload?.status_type || status.type}
                  </div>
                </div>
              )
            }
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        style={{
          display: 'flex',
          gap: 10,
          background: '#fff',
          padding: 12,
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message or command..."
          disabled={!connected}
          style={{
            flex: 1,
            padding: '12px 16px',
            border: '1px solid #e0e0e0',
            borderRadius: 8,
            fontSize: 14,
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!connected || !input.trim()}
          style={{
            padding: '12px 20px',
            background: !connected || !input.trim() ? '#ccc' : '#1a1a2e',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: !connected || !input.trim() ? 'default' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontWeight: 600,
          }}
        >
          <Send size={16} /> Send
        </button>
      </div>
    </div>
  )
}
