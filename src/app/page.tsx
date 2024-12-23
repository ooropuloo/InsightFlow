"use client"

import { Chat } from '@/components/Chat'
import { ToolPanel } from '@/components/ToolPanel'
import { useState, useEffect } from 'react'

interface UploadedFile {
  path: string;
  rows: number;
  columns: number;
}

export default function Home() {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | undefined>()

  useEffect(() => {
    if (uploadedFile) {
      console.log('File info updated:', uploadedFile);
    }
  }, [uploadedFile]);

  const handleFileUpload = (fileInfo: UploadedFile) => {
    console.log('Received file info:', fileInfo);
    setUploadedFile(fileInfo);
  };

  return (
    <main className="flex min-h-screen">
      <div className="flex-1">
        <Chat uploadedFile={uploadedFile} />
      </div>
      <ToolPanel onFileUpload={handleFileUpload} />
    </main>
  )
}
