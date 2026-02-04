import { useEffect, useRef, useState, useCallback } from 'react'
import type { ChatMessage, WSMessage } from '../types'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [statusUpdates, setStatusUpdates] = useState<WSMessage[]>([])
  const [latestStatus, setLatestStatus] = useState<Record<string, any>>({})
  const reconnectTimeout = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/chat`)

    ws.onopen = () => {
      setConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)

        switch (msg.type) {
          case 'chat_response':
            setChatMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: msg.payload.content,
                timestamp: msg.timestamp,
              },
            ])
            break

          case 'status_update':
            setStatusUpdates((prev) => [...prev.slice(-50), msg])
            setLatestStatus((prev) => ({
              ...prev,
              [msg.payload.status_type]: msg.payload,
            }))
            break

          case 'jobs_scored':
          case 'application_update':
          case 'error':
            setStatusUpdates((prev) => [...prev.slice(-50), msg])
            setLatestStatus((prev) => ({ ...prev, [msg.type]: msg.payload }))
            break

          case 'pong':
            break

          default:
            setStatusUpdates((prev) => [...prev.slice(-50), msg])
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      console.log('WebSocket disconnected, reconnecting...')
      reconnectTimeout.current = setTimeout(connect, 3000)
    }

    ws.onerror = (e) => {
      console.error('WebSocket error:', e)
      ws.close()
    }

    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setChatMessages((prev) => [
        ...prev,
        { role: 'user', content, timestamp: new Date().toISOString() },
      ])
      wsRef.current.send(
        JSON.stringify({
          type: 'chat_message',
          payload: { content },
        })
      )
    }
  }, [])

  const clearChat = useCallback(() => {
    setChatMessages([])
  }, [])

  return {
    connected,
    chatMessages,
    statusUpdates,
    latestStatus,
    sendMessage,
    clearChat,
  }
}
