"use client"

import { useState } from 'react'
import { Upload, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

interface ToolPanelProps {
  onFileUpload: (fileInfo: {
    path: string;
    rows: number;
    columns: number;
  }) => void;
}

export function ToolPanel({ onFileUpload }: ToolPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setFile(files[0])
      setUploadStatus('uploading')
      setError(null)

      const formData = new FormData()
      formData.append('file', files[0])

      try {
        const response = await fetch('http://127.0.0.1:8000/api/upload', {
          method: 'POST',
          mode: 'cors',
          credentials: 'omit',
          body: formData,
          headers: {
            'Accept': 'application/json',
          },
        })

        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.error || 'Upload failed')
        }

        setUploadStatus('success')
        onFileUpload({
          path: data.path,
          rows: data.rows,
          columns: data.columns
        })
      } catch (error: any) {
        console.error('Upload failed:', error)
        setError(error.message || '上傳失敗，請稍後再試')
        setUploadStatus('error')
      }
    }
  }

  return (
    <div className="border-l p-4 w-80">
      <div className="space-y-4">
        <div>
          <h3 className="font-medium mb-2">上傳 Excel</h3>
          <label 
            className={cn(
              'flex flex-col items-center p-4 border-2 border-dashed rounded-lg cursor-pointer transition-colors',
              uploadStatus === 'uploading' && 'opacity-50 cursor-not-allowed',
              uploadStatus === 'success' && 'border-green-500 bg-green-50',
              uploadStatus === 'error' && 'border-red-500 bg-red-50',
              !['uploading', 'success', 'error'].includes(uploadStatus) && 'hover:bg-gray-50'
            )}
          >
            {uploadStatus === 'uploading' ? (
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            ) : (
              <Upload className={cn(
                "w-8 h-8",
                uploadStatus === 'success' && 'text-green-500',
                uploadStatus === 'error' && 'text-red-500',
                uploadStatus === 'idle' && 'text-gray-400'
              )} />
            )}
            <span className={cn(
              'mt-2 text-sm',
              uploadStatus === 'success' && 'text-green-600',
              uploadStatus === 'error' && 'text-red-600',
              !['success', 'error'].includes(uploadStatus) && 'text-gray-500'
            )}>
              {uploadStatus === 'uploading' ? '上傳中...' :
               uploadStatus === 'success' ? '上傳成功！' :
               uploadStatus === 'error' ? '上傳失敗' :
               file ? file.name : '選擇文件'}
            </span>
            <input
              type="file"
              className="hidden"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              disabled={uploadStatus === 'uploading'}
            />
          </label>
          {error && (
            <div className="mt-2 text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        <div>
          <h3 className="font-medium mb-2">可用工具</h3>
          <div className="space-y-2">
            <div className="w-full px-4 py-2 border rounded-lg">
              <h4 className="font-medium">Excel 分析</h4>
              <p className="text-sm text-gray-500">分析 Excel 文件數據</p>
            </div>
            <div className="w-full px-4 py-2 border rounded-lg">
              <h4 className="font-medium">數據庫查詢</h4>
              <p className="text-sm text-gray-500">執行 SQL 查詢</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
