'use client'

/**
 * ============================================================
 * 🎨 GENERATIVE UI CHAT INTERFACE
 * ============================================================
 * 
 * This enhanced chat interface supports:
 * - Standard text messages
 * - Server-Sent Events (SSE) streaming
 * - Rich UI artifacts (charts, tables, cards)
 * - Real-time status updates
 * 
 * The interface intercepts JSON artifacts from the AI agent
 * and renders them as interactive Recharts components.
 */

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import ArtifactRenderer, { UIArtifact } from './artifacts/ArtifactComponents'
import { Send, Loader2, Bot, User, Sparkles, TrendingUp, MessageSquare } from 'lucide-react'

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface StreamEvent {
  type: 'status' | 'artifact' | 'done' | 'error'
  message?: string
  artifact?: UIArtifact
  agents_used?: string[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  artifacts?: UIArtifact[]
  agentsUsed?: string[]
  isStreaming?: boolean
  statusMessage?: string
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useGenerativeUI, setUseGenerativeUI] = useState(true)
  const { token } = useAuth()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Use Python agent URL directly for Generative UI, Java backend for regular chat
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
  
  // Derive Python agent URL - in production use the EC2 public IP on port 8000
  // In development, use localhost:8000
  const getPythonAgentUrl = () => {
    if (process.env.NEXT_PUBLIC_PYTHON_AGENT_URL) {
      return process.env.NEXT_PUBLIC_PYTHON_AGENT_URL
    }
    // If API_URL is set to production (not localhost), use the EC2 IP for Python agent
    if (API_URL && !API_URL.includes('localhost')) {
      // Extract host from API_URL and use port 8000 for Python agent
      try {
        const url = new URL(API_URL)
        // Use HTTP for Python agent (not HTTPS) since it's direct to EC2
        return `http://3.131.250.245:8000`
      } catch {
        return 'http://localhost:8000'
      }
    }
    return 'http://localhost:8000'
  }
  const PYTHON_AGENT_URL = getPythonAgentUrl()

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ============================================================
  // GENERATIVE UI - SSE STREAMING
  // ============================================================

  const sendWithGenerativeUI = async (query: string) => {
    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: query,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Add placeholder assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      artifacts: [],
      isStreaming: true,
      statusMessage: 'Connecting...'
    }
    setMessages((prev) => [...prev, assistantMessage])

    try {
      abortControllerRef.current = new AbortController()

      const response = await fetch(`${PYTHON_AGENT_URL}/api/generative-ui`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, stream: true }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      let collectedArtifacts: UIArtifact[] = []
      let textContent = ''
      let agentsUsed: string[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StreamEvent = JSON.parse(line.slice(6))

              switch (data.type) {
                case 'status':
                  // Update status message
                  setMessages((prev) => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'assistant') {
                      lastMsg.statusMessage = data.message
                    }
                    return newMessages
                  })
                  break

                case 'artifact':
                  if (data.artifact) {
                    if (data.artifact.type === 'text') {
                      textContent = (data.artifact as any).content || ''
                    } else {
                      collectedArtifacts.push(data.artifact)
                    }
                    // Update message with new artifact
                    setMessages((prev) => {
                      const newMessages = [...prev]
                      const lastMsg = newMessages[newMessages.length - 1]
                      if (lastMsg.role === 'assistant') {
                        lastMsg.artifacts = [...collectedArtifacts]
                        lastMsg.content = textContent
                      }
                      return newMessages
                    })
                  }
                  break

                case 'done':
                  agentsUsed = data.agents_used || []
                  setMessages((prev) => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'assistant') {
                      lastMsg.isStreaming = false
                      lastMsg.statusMessage = undefined
                      lastMsg.agentsUsed = agentsUsed
                      lastMsg.artifacts = collectedArtifacts
                      lastMsg.content = textContent
                    }
                    return newMessages
                  })
                  break

                case 'error':
                  throw new Error(data.message || 'Unknown error')
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError)
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted')
      } else {
        console.error('Generative UI error:', error)
        setMessages((prev) => {
          const newMessages = [...prev]
          const lastMsg = newMessages[newMessages.length - 1]
          if (lastMsg.role === 'assistant') {
            lastMsg.isStreaming = false
            lastMsg.statusMessage = undefined
            lastMsg.content = `Sorry, I encountered an error: ${error.message}`
          }
          return newMessages
        })
      }
    }
  }

  // ============================================================
  // STANDARD CHAT (Non-streaming fallback)
  // ============================================================

  const sendStandardMessage = async (query: string) => {
    const userMessage: Message = {
      role: 'user',
      content: query,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      const response = await fetch(`${API_URL}/api/chat?query=${encodeURIComponent(query)}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.text()
      const assistantMessage: Message = {
        role: 'assistant',
        content: data,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  // ============================================================
  // MAIN SEND FUNCTION
  // ============================================================

  const sendMessage = async () => {
    if (!input.trim()) return

    const query = input
    setInput('')
    setLoading(true)

    try {
      if (useGenerativeUI) {
        await sendWithGenerativeUI(query)
      } else {
        await sendStandardMessage(query)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const cancelRequest = () => {
    abortControllerRef.current?.abort()
    setLoading(false)
  }

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="flex flex-col h-[700px]">
      {/* Header with mode toggle */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-700">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-400" />
          AI Chat
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Generative UI</span>
          <button
            onClick={() => setUseGenerativeUI(!useGenerativeUI)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              useGenerativeUI ? 'bg-blue-600' : 'bg-gray-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                useGenerativeUI ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-16">
            <div className="flex justify-center mb-4">
              <div className="bg-blue-500/20 p-4 rounded-full">
                <TrendingUp className="w-8 h-8 text-blue-400" />
              </div>
            </div>
            <p className="text-xl mb-2">👋 Welcome to Enterprise RAG!</p>
            <p className="text-gray-500 mb-4">Ask me anything about stocks, finance, or general topics.</p>
            <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
              {[
                "What's Apple's stock price?",
                "Compare Google and Microsoft stock",
                "Tesla stock analysis"
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-full transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[85%] rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white p-4'
                    : 'bg-gray-800 text-gray-100 p-4'
                }`}
              >
                {/* User/Bot icon */}
                <div className="flex items-center gap-2 mb-2">
                  {message.role === 'user' ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4 text-blue-400" />
                  )}
                  <span className="text-xs opacity-60">
                    {message.role === 'user' ? 'You' : 'AI Assistant'}
                  </span>
                  <span className="text-xs opacity-40">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>

                {/* Status message while streaming */}
                {message.isStreaming && message.statusMessage && (
                  <div className="flex items-center gap-2 text-blue-400 text-sm mb-3">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {message.statusMessage}
                  </div>
                )}

                {/* Artifacts (charts, tables, cards) */}
                {message.artifacts && message.artifacts.length > 0 && (
                  <div className="space-y-3 mb-3">
                    {message.artifacts.map((artifact, artifactIndex) => (
                      <ArtifactRenderer key={artifactIndex} artifact={artifact} />
                    ))}
                  </div>
                )}

                {/* Text content */}
                {message.content && (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}

                {/* Agents used badge */}
                {message.agentsUsed && message.agentsUsed.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-gray-700">
                    <span className="text-xs text-gray-500">Agents:</span>
                    {message.agentsUsed.map((agent, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-xs rounded-full"
                      >
                        {agent}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {loading && messages.length > 0 && !messages[messages.length - 1]?.isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-gray-100 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                <span className="text-sm text-gray-400">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={useGenerativeUI 
              ? "Ask about stocks, compare companies, or analyze data..." 
              : "Ask a question..."
            }
            className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={2}
            disabled={loading}
          />
          {useGenerativeUI && (
            <div className="absolute right-3 top-3">
              <Sparkles className="w-4 h-4 text-blue-400 opacity-50" />
            </div>
          )}
        </div>
        {loading ? (
          <button
            onClick={cancelRequest}
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={sendMessage}
            disabled={!input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        )}
      </div>
    </div>
  )
}
