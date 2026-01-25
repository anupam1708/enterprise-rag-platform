'use client'

import { useState } from 'react'
import axios from 'axios'

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setMessage(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Please select a file first' })
      return
    }

    setUploading(true)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(`${API_URL}/api/ingest`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setMessage({
        type: 'success',
        text: `Document uploaded successfully! Processed ${response.data.chunks || 'multiple'} chunks.`,
      })
      setFile(null)
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (error: any) {
      console.error('Error uploading document:', error)
      setMessage({
        type: 'error',
        text: error.response?.data?.message || 'Failed to upload document. Please try again.',
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">Upload Documents</h2>
        <p className="text-gray-400">
          Upload PDF documents to add them to your knowledge base
        </p>
      </div>

      <div className="bg-gray-700 rounded-lg p-8">
        {/* File Upload Area */}
        <div className="border-2 border-dashed border-gray-500 rounded-lg p-8 text-center mb-6">
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          <label
            htmlFor="file-input"
            className="cursor-pointer flex flex-col items-center"
          >
            <svg
              className="w-16 h-16 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-white font-semibold mb-2">
              {file ? file.name : 'Click to select a PDF file'}
            </p>
            <p className="text-gray-400 text-sm">
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'or drag and drop'}
            </p>
          </label>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-3 rounded-lg font-semibold transition-colors"
        >
          {uploading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Uploading...
            </span>
          ) : (
            '📤 Upload Document'
          )}
        </button>

        {/* Status Message */}
        {message && (
          <div
            className={`mt-4 p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-900/50 text-green-300'
                : 'bg-red-900/50 text-red-300'
            }`}
          >
            {message.text}
          </div>
        )}
      </div>

      {/* Info Section */}
      <div className="mt-8 bg-gray-700/50 rounded-lg p-6">
        <h3 className="text-white font-semibold mb-3">ℹ️ How it works:</h3>
        <ul className="text-gray-300 space-y-2 text-sm">
          <li>• Upload PDF documents to build your knowledge base</li>
          <li>• Documents are automatically processed and embedded</li>
          <li>• Use the Chat tab to ask questions about your documents</li>
          <li>• The AI will provide answers based on the uploaded content</li>
        </ul>
      </div>
    </div>
  )
}
