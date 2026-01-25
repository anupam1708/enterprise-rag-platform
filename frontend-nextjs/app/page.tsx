'use client'

import { useState } from 'react'
import ChatInterface from '@/components/ChatInterface'
import DocumentUpload from '@/components/DocumentUpload'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload'>('chat')

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🤖 Enterprise RAG Platform
          </h1>
          <p className="text-gray-300">
            AI-powered compliance and knowledge management
          </p>
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
  )
}
