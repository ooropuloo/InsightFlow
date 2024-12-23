"use client"

import { Send, Loader2, ChevronDown, ChevronUp, FileSpreadsheet, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'
import { useEffect, useRef, useState } from 'react'

interface ChatProps {
  uploadedFile?: {
    path: string;
    rows: number;
    columns: number;
  };
  onFileUpload?: (file: File) => Promise<void>;
}

interface Message {
  role: string;
  content: string;
  id: string;
  isCollapsed?: boolean;
}

export function Chat({ uploadedFile, onFileUpload }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [currentResponse, setCurrentResponse] = useState<string>('')
  const containerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse])

  const toggleMessageCollapse = (messageId: string) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, isCollapsed: !msg.isCollapsed }
        : msg
    ))
  }

  const handleFileUpload = async (file: File) => {
    if (!onFileUpload) return
    
    try {
      setStatus('正在上傳文件...')
      await onFileUpload(file)
      setStatus('文件上傳成功！')
      setTimeout(() => setStatus(''), 2000)
    } catch (err: any) {
      setError(err?.message || '文件上傳失敗')
      setTimeout(() => setError(null), 3000)
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input.trim()) return

    setError(null)
    setStatus('正在處理您的請求...')
    setCurrentResponse('')
    setIsLoading(true)

    const userMessage = { role: 'user', content: input, id: Date.now().toString() }
    setMessages(prev => [...prev, userMessage])

    try {
      const requestBody = {
        messages: [
          ...(uploadedFile ? [{
            role: 'system',
            content: `已上傳的 Excel 文件信息：\n路徑：${uploadedFile.path}\n行數：${uploadedFile.rows}\n列數：${uploadedFile.columns}`,
            id: 'file-info'
          }] : []),
          ...messages,
          userMessage
        ],
        content: input
      };

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error('伺服器響應錯誤')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const text = decoder.decode(value)
          fullResponse += text
          setCurrentResponse(prev => prev + text)
        }
      }

      setMessages(prev => [
        ...prev,
        { 
          role: 'assistant', 
          content: fullResponse, 
          id: Date.now().toString(),
          isCollapsed: false 
        }
      ])
      setCurrentResponse('')
      setInput('')
    } catch (err: any) {
      console.error('Chat error:', err)
      setError(err?.message || '抱歉，發生了錯誤。請稍後再試。')
    } finally {
      setStatus('')
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full relative" ref={containerRef}>
      

      {/* File Info Banner */}
      {uploadedFile && (
        <div className="bg-blue-50 px-4 py-3 flex items-center gap-3 border-b">
          <FileSpreadsheet className="w-5 h-5 text-blue-500 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {uploadedFile.path.split('/').pop()}
            </p>
            <p className="text-xs text-gray-500">
              {uploadedFile.rows.toLocaleString()} 行 × {uploadedFile.columns} 列
            </p>
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-1 text-sm text-blue-500 hover:text-blue-600 hover:bg-blue-100 rounded"
          >
            更換文件
          </button>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".xlsx,.xls"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file && onFileUpload) {
                handleFileUpload(file)
              }
            }}
          />
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex w-max max-w-[80%] flex-col gap-2 rounded-lg px-4 py-3 text-sm',
              message.role === 'user'
                ? 'ml-auto bg-blue-500 text-white'
                : 'bg-gray-100'
            )}
          >
            {message.role === 'assistant' && message.content.length > 300 && (
              <button
                onClick={() => toggleMessageCollapse(message.id)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
              >
                {message.isCollapsed ? (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    <span>展開回應</span>
                  </>
                ) : (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    <span>收起回應</span>
                  </>
                )}
              </button>
            )}
            <div className={cn(
              'transition-all duration-200',
              message.isCollapsed ? 'max-h-20 overflow-hidden' : 'max-h-none'
            )}>
              <ReactMarkdown 
                className={cn(
                  'prose max-w-none',
                  message.role === 'user' && 'prose-invert'
                )}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        
        {currentResponse && (
          <div className="flex w-max max-w-[80%] flex-col gap-2 rounded-lg px-4 py-3 text-sm bg-gray-100">
            <ReactMarkdown className="prose max-w-none">
              {currentResponse}
            </ReactMarkdown>
          </div>
        )}
        
        {error && (
          <div className="flex w-max max-w-[80%] items-center gap-2 rounded-lg px-4 py-3 text-sm bg-red-50 text-red-600">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}
        
        {status && (
          <div className="flex w-max max-w-[80%] items-center gap-2 rounded-lg px-4 py-3 text-sm bg-blue-50 text-blue-600">
            <Loader2 className="animate-spin w-4 h-4 flex-shrink-0" />
            {status}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 shadow-lg">
        <form onSubmit={handleSubmit} className="container mx-auto max-w-4xl">
          <div className="flex gap-3">
            <input
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={input}
              placeholder={uploadedFile ? "輸入您的問題..." : "請先上傳 Excel 文件"}
              onChange={(e) => setInput(e.target.value)}
              disabled={!uploadedFile || isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim() || !uploadedFile}
              className={cn(
                'px-4 py-2 rounded-lg bg-blue-500 text-white',
                'hover:bg-blue-600 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
