'use client'

/**
 * ============================================================
 * 🔐 HUMAN-IN-THE-LOOP (HITL) CHAT
 * ============================================================
 *
 * Routes through /api/graph with enable_hitl=true.
 * When the agent wants to execute a high-risk tool
 * (buy_stock, send_email, delete_database_records), the graph
 * pauses at the interrupt point and renders an approval card
 * inline in the chat — user must Approve or Reject before
 * execution continues.
 *
 * Flow:
 *   1. POST /api/graph  { query, thread_id, enable_hitl: true }
 *      → pending_approval: true  → fetch /api/graph/pending
 *      → pending_approval: false → show answer normally
 *   2. User clicks Approve / Reject
 *      → POST /api/graph/approve { thread_id, approved }
 *      → show result message
 * ============================================================
 */

import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Loader2,
  Bot,
  User,
  ShieldAlert,
  Shield,
  CheckCircle,
  XCircle,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  // Approval card (before decision)
  isPendingApproval?: boolean
  toolName?: string
  toolInput?: Record<string, unknown>
  // Status badge (after decision)
  isApprovalBadge?: boolean
  approvalStatus?: 'approved' | 'rejected'
}

interface PendingApproval {
  tool_name: string
  tool_input: Record<string, unknown>
  is_high_risk: boolean
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, string> = {
  buy_stock: 'Purchase Stock',
  send_email: 'Send Email',
  delete_database_records: 'Delete Database Records',
}

function getPythonAgentUrl(): string {
  if (process.env.NEXT_PUBLIC_PYTHON_AGENT_URL) {
    return process.env.NEXT_PUBLIC_PYTHON_AGENT_URL
  }
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
  if (!apiUrl.includes('localhost')) {
    try {
      const url = new URL(apiUrl)
      return `${url.protocol}//${url.host}/python-api`
    } catch {
      return 'http://localhost:8000'
    }
  }
  return 'http://localhost:8000'
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function HITLChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [approving, setApproving] = useState(false)
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)

  // One stable thread_id for the lifetime of this component
  const [threadId] = useState(
    () => `hitl-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  )

  const PYTHON_AGENT_URL = getPythonAgentUrl()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Send message ─────────────────────────────────────────────────────────────

  const sendMessage = async () => {
    if (!input.trim() || loading || pendingApproval) return

    const query = input.trim()
    setInput('')
    setLoading(true)

    setMessages(prev => [
      ...prev,
      { role: 'user', content: query, timestamp: new Date() },
    ])

    try {
      const res = await fetch(`${PYTHON_AGENT_URL}/api/graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, thread_id: threadId, enable_hitl: true }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      if (data.pending_approval) {
        // Fetch full tool details for the approval card
        const pendingRes = await fetch(`${PYTHON_AGENT_URL}/api/graph/pending`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thread_id: threadId }),
        })
        const pending: PendingApproval = await pendingRes.json()
        setPendingApproval(pending)

        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isPendingApproval: true,
            toolName: pending.tool_name,
            toolInput: pending.tool_input,
          },
        ])
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.answer, timestamp: new Date() },
        ])
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${msg}`, timestamp: new Date() },
      ])
    } finally {
      setLoading(false)
    }
  }

  // ── Approve / Reject ─────────────────────────────────────────────────────────

  const handleApproval = async (approved: boolean) => {
    if (!pendingApproval || approving) return
    setApproving(true)

    const toolName = pendingApproval.tool_name

    // Swap the approval card for a status badge immediately
    setMessages(prev =>
      prev.map(msg =>
        msg.isPendingApproval
          ? {
              ...msg,
              isPendingApproval: false,
              isApprovalBadge: true,
              approvalStatus: approved ? 'approved' : 'rejected',
            }
          : msg
      )
    )
    setPendingApproval(null)

    try {
      const res = await fetch(`${PYTHON_AGENT_URL}/api/graph/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, approved }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      const resultText = approved
        ? data.result?.result ?? data.result?.message ?? 'Action executed successfully.'
        : data.result?.message ?? 'Action was cancelled.'

      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: resultText, timestamp: new Date() },
      ])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Error processing ${approved ? 'approval' : 'rejection'}: ${msg}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setApproving(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[700px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-700">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          HITL Agent
          <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-normal">
            Human-in-the-Loop
          </span>
        </h2>
        <span className="text-xs text-gray-600 font-mono hidden sm:block">
          thread: {threadId}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-12">
            <div className="flex justify-center mb-4">
              <div className="bg-amber-500/20 p-4 rounded-full">
                <ShieldAlert className="w-8 h-8 text-amber-400" />
              </div>
            </div>
            <p className="text-xl mb-2 text-white">Human-in-the-Loop Agent</p>
            <p className="text-gray-500 mb-6 text-sm max-w-sm mx-auto">
              High-risk actions pause and wait for your approval before executing.
            </p>
            <div className="flex flex-col items-center gap-2 max-w-sm mx-auto">
              {[
                "Buy 50 shares of AAPL at $195",
                "Send email to john@example.com with subject \"Q4 Report\" and body \"Please review.\"",
                "Delete test records from users table where username = 'demo'",
              ].map((s, i) => (
                <button
                  key={i}
                  onClick={() => setInput(s)}
                  className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-lg transition-colors text-left"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => {
            // ── Approval card ────────────────────────────────────────────────
            if (msg.isPendingApproval) {
              return (
                <div key={i} className="flex justify-start">
                  <div className="max-w-[85%] w-full bg-amber-950/50 border border-amber-500/40 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
                      <span className="text-amber-300 font-semibold">Approval Required</span>
                      <span className="ml-auto text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full">
                        High Risk
                      </span>
                    </div>

                    <p className="text-gray-400 text-sm mb-3">
                      The agent wants to execute:
                    </p>

                    {/* Tool details */}
                    <div className="bg-gray-900/60 rounded-lg p-3 mb-4 space-y-1">
                      <p className="text-amber-300 font-mono font-semibold text-sm mb-2">
                        {TOOL_LABELS[msg.toolName!] ?? msg.toolName}
                      </p>
                      {Object.entries(msg.toolInput ?? {}).map(([key, val]) => (
                        <div key={key} className="flex gap-3 text-sm">
                          <span className="text-gray-500 font-mono w-24 shrink-0">{key}</span>
                          <span className="text-gray-200 font-mono">{String(val)}</span>
                        </div>
                      ))}
                    </div>

                    {/* Approve / Reject */}
                    <div className="flex gap-3">
                      <button
                        onClick={() => handleApproval(true)}
                        disabled={approving}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors text-sm"
                      >
                        {approving ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => handleApproval(false)}
                        disabled={approving}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors text-sm"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              )
            }

            // ── Post-approval badge ──────────────────────────────────────────
            if (msg.isApprovalBadge) {
              const isApproved = msg.approvalStatus === 'approved'
              return (
                <div key={i} className="flex justify-start">
                  <div
                    className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 border ${
                      isApproved
                        ? 'bg-green-900/30 border-green-500/30 text-green-300'
                        : 'bg-red-900/30 border-red-500/30 text-red-300'
                    }`}
                  >
                    {isApproved ? (
                      <CheckCircle className="w-4 h-4 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 shrink-0" />
                    )}
                    {isApproved ? 'Approved' : 'Rejected'}:{' '}
                    {TOOL_LABELS[msg.toolName!] ?? msg.toolName}
                  </div>
                </div>
              )
            }

            // ── Regular message bubble ───────────────────────────────────────
            return (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg p-4 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {msg.role === 'user' ? (
                      <User className="w-4 h-4" />
                    ) : (
                      <Bot className="w-4 h-4 text-amber-400" />
                    )}
                    <span className="text-xs opacity-60">
                      {msg.role === 'user' ? 'You' : 'HITL Agent'}
                    </span>
                    <span className="text-xs opacity-40">
                      {msg.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            )
          })
        )}

        {/* Loading spinner */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg p-4 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
              <span className="text-sm text-gray-400">Agent thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={
            pendingApproval
              ? 'Waiting for your approval above...'
              : 'Type a command (buy stock, send email, delete records)...'
          }
          disabled={loading || !!pendingApproval}
          className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          rows={2}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || loading || !!pendingApproval}
          className="bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </div>
    </div>
  )
}
