'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DropzoneProps {
  onFileSelect: (file: File) => void;
  className?: string;
  value?: File | null;
}

export function Dropzone({ onFileSelect, className, value }: DropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1,
    multiple: false,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  });

  return (
    <div 
      {...getRootProps()} 
      className={cn(
        "relative rounded-lg border-2 border-dashed transition-colors duration-200 ease-in-out",
        isDragActive ? "border-primary bg-primary/5" : "border-gray-200 hover:border-primary/50",
        className
      )}
    >
      <input {...getInputProps()} />
      
      <div className="flex flex-col items-center justify-center p-6 text-center">
        {value ? (
          <div className="flex items-center gap-2 text-sm">
            <File className="h-8 w-8 text-primary" />
            <div className="flex-1">
              <p className="font-medium">{value.name}</p>
              <p className="text-xs text-gray-500">
                {(value.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>
        ) : (
          <>
            <UploadCloud 
              className={cn(
                "h-10 w-10 mb-2 transition-colors duration-200",
                isDragActive ? "text-primary" : "text-gray-400"
              )} 
            />
            <p className="text-sm font-medium">
              {isDragActive ? "放開以上傳文件" : "拖放或點擊上傳 Excel 文件"}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              支持 .xlsx 和 .xls 文件
            </p>
          </>
        )}
      </div>
    </div>
  );
}
