'use client'

import { useState } from 'react'
import ChatInterface from '@/components/ChatInterface'
import DocumentUpload from '@/components/DocumentUpload'
import ProtectedRoute from '@/components/ProtectedRoute'
import { useAuth } from '@/contexts/AuthContext'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload'>('chat')
  const { user, logout } = useAuth()

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          <header className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">
                🤖 Enterprise RAG Platform
              </h1>
              <p className="text-gray-300">
                AI-powered compliance and knowledge management
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-white font-medium">{user?.username}</p>
                <p className="text-gray-400 text-sm">{user?.role}</p>
              </div>
              <button
                onClick={logout}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Logout
              </button>
            </div>
          </header>

          {/* Tab Navigation */}
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                activeTab === 'chat'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              💬 Chat
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              📄 Upload Documents
            </button>
          </div>

          {/* Content */}
          <div className="bg-gray-800 rounded-xl shadow-2xl p-6">
            {activeTab === 'chat' ? <ChatInterface /> : <DocumentUpload />}
          </div>
        </div>
      </main>
    </ProtectedRoute>
  )
}
