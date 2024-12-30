'use client';

import { useChat } from 'ai/react';
import { FileUpload, useFilePath } from '@/components/file-upload';
import { ChatMessage } from '@/components/chat/chat-message';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, ChevronRight, ChevronLeft } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const { filePath } = useFilePath();
  const { toast } = useToast();
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
    body: {
      filePath,
    },
    onError: (error) => {
      toast({
        title: '錯誤',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const [isUploadPanelOpen, setIsUploadPanelOpen] = useState(true);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!filePath) {
      toast({
        title: '請先上傳檔案',
        description: '您需要先上傳一個 Excel 檔案才能進行分析。',
        variant: 'destructive',
      });
      return;
    }
    handleSubmit(e);
  };

  return (
    <div className="flex h-screen">
      {/* 上傳面板 */}
      <div
        className={cn(
          "fixed left-0 top-0 h-full bg-background transition-transform duration-300 ease-in-out z-30 border-r",
          isUploadPanelOpen ? "translate-x-0" : "-translate-x-full"
        )}
        style={{ width: '400px' }}
      >
        <FileUpload />
      </div>

      {/* 切換按鈕 */}
      <button
        onClick={() => setIsUploadPanelOpen(!isUploadPanelOpen)}
        className={cn(
          "fixed top-1/2 transform -translate-y-1/2 z-40 bg-primary text-primary-foreground p-2 rounded-r-lg transition-transform duration-300 ease-in-out",
          isUploadPanelOpen ? "left-[400px]" : "left-0"
        )}
      >
        {isUploadPanelOpen ? <ChevronLeft /> : <ChevronRight />}
      </button>

      {/* 主聊天區域 */}
      <div 
        className={cn(
          "flex-1 flex flex-col transition-all duration-300 ease-in-out",
          isUploadPanelOpen ? "ml-[400px]" : "ml-0"
        )}
      >
        <Card className="m-4 flex-1 flex flex-col">
          <ScrollArea ref={scrollRef} className="flex-1 p-4">
            <div className="space-y-4">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && (
                <div className="flex justify-center">
                  <span className="loading loading-dots">加載中...</span>
                </div>
              )}
            </div>
          </ScrollArea>

          <div className="p-4 border-t">
            <form onSubmit={onSubmit} className="flex gap-2">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="輸入你的問題..."
                disabled={!filePath || isLoading}
              />
              <Button type="submit" disabled={!filePath || isLoading}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
}