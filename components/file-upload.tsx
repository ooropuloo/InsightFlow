'use client';

import { useState, useEffect, createContext, useContext } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/components/ui/use-toast';
import { Card } from '@/components/ui/card';
import { Dropzone } from '@/components/ui/dropzone';
import { FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface UploadedFile {
  path: string;
  rows: number;
  columns: number;
}

// 使用 React Context 來管理上傳的文件路徑
export const FilePathContext = createContext<{
  filePath: string | null;
  setFilePath: (path: string | null) => void;
}>({
  filePath: null,
  setFilePath: () => {},
});

export function useFilePath() {
  return useContext(FilePathContext);
}

export function FileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const { toast } = useToast();
  const { setFilePath } = useFilePath();

  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  const fetchUploadedFiles = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/files');
      if (response.ok) {
        const files = await response.json();
        setUploadedFiles(files);
        // 如果有文件，設置最後一個文件的路徑
        if (files.length > 0) {
          setFilePath(files[files.length - 1].path);
        }
      }
    } catch (error) {
      console.error('Failed to fetch files:', error);
      toast({
        title: "無法獲取文件列表",
        description: "請檢查後端服務是否正常運行",
        variant: "destructive",
      });
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploading(true);
      setProgress(0);
      
      const formData = new FormData();
      formData.append('file', file);

      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentage = (event.loaded / event.total) * 100;
            setProgress(Math.round(percentage));
          }
        };

        xhr.onload = async () => {
          if (xhr.status === 200) {
            try {
              const data = JSON.parse(xhr.responseText);
              setUploadedFiles(prev => [...prev, data]);
              // 保存最新上傳的文件路徑
              setFilePath(data.path);
              toast({
                title: "上傳成功",
                description: `文件 ${file.name} 已成功上傳`,
              });
              resolve(data);
            } catch (error) {
              reject(new Error('無法解析伺服器回應'));
            }
          } else {
            reject(new Error(`上傳失敗: ${xhr.statusText}`));
          }
        };

        xhr.onerror = () => {
          reject(new Error('網絡錯誤，請檢查後端服務是否正常運行'));
        };

        xhr.open('POST', 'http://127.0.0.1:8000/api/upload');
        xhr.send(formData);
      }).catch((error: Error) => {
        toast({
          title: "上傳失敗",
          description: error.message,
          variant: "destructive",
        });
      }).finally(() => {
        setUploading(false);
        setFile(null);
        setProgress(0);
      });
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: "上傳失敗",
        description: error instanceof Error ? error.message : "未知錯誤",
        variant: "destructive",
      });
      setUploading(false);
      setFile(null);
      setProgress(0);
    }
  };

  return (
    <FilePathContext.Provider value={{
      filePath: null,
      setFilePath,
    }}>
      <Card className="p-6 space-y-6">
        <div className="space-y-4">
          <div className="flex flex-col gap-4">
            <Dropzone
              value={file}
              onFileSelect={setFile}
              className="min-h-[160px]"
            />
            
            <Button 
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full"
            >
              {uploading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  上傳中...
                </div>
              ) : (
                '開始上傳'
              )}
            </Button>
          </div>

          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-500">
                <span>上傳進度</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-1" />
            </div>
          )}
        </div>

        {uploadedFiles.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">已上傳文件</h3>
              <span className="text-sm text-gray-500">
                共 {uploadedFiles.length} 個文件
              </span>
            </div>
            
            <div className="space-y-2">
              {uploadedFiles.map((uploadedFile, index) => (
                <div 
                  key={index}
                  className={cn(
                    "p-3 rounded-lg border transition-colors duration-200",
                    "hover:bg-gray-50",
                    useFilePath().filePath === uploadedFile.path && "border-primary"
                  )}
                >
                  <div className="flex items-start gap-3">
                    <FileText className="h-5 w-5 text-primary mt-1" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {uploadedFile.path.split('/').pop()}
                      </p>
                      <div className="flex gap-2 text-sm text-gray-500">
                        <span>{uploadedFile.rows} 行</span>
                        <span>•</span>
                        <span>{uploadedFile.columns} 列</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </FilePathContext.Provider>
  );
}
