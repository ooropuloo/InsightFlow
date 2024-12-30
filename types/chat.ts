export interface Message {
  id: string;
  content: string;
  role: 'system' | 'user' | 'assistant' | 'function' | 'tool' | 'data';
  createdAt?: Date;
}

export interface ChatRequest {
  messages: Message[];
  options?: {
    temperature?: number;
    top_p?: number;
    max_tokens?: number;
  };
}