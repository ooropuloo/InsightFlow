import OpenAI from 'openai';
import { StreamingTextResponse, OpenAIStream } from 'ai';

export const runtime = 'edge';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

// 緩存工具列表
let cachedTools: any = null;

async function getTools() {
  if (cachedTools) {
    return cachedTools;
  }
  
  try {
    const response = await fetch('http://127.0.0.1:8000/api/tools');
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    cachedTools = await response.json();
    return cachedTools;
  } catch (error) {
    console.error('Error fetching tools:', error);
    return null;
  }
}

export async function POST(req: Request) {
  try {
    const { messages, filePath } = await req.json();
    const tools = await getTools();

    // 先讓 OpenAI 判斷是否需要使用工具
    const response = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini-2024-07-18',
      messages: messages.map((message: any) => ({
        content: message.content,
        role: message.role,
      })),
      tools: tools,
      tool_choice: 'auto',
      stream: false,
    });

    const choice = response.choices[0];
    //console.log('OpenAI response:', JSON.stringify(choice, null, 2));
    
    // 如果 OpenAI 選擇使用工具
    if (choice.message?.tool_calls?.length > 0) {
      const toolNames = choice.message.tool_calls.map(call => call.function.name).join(', ');
      const systemMessage = `[系統] 使用工具: ${toolNames} 來處理您的請求...\n\n`;
      
      // 呼叫後端的 chat API
      const backendResponse = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: messages[messages.length - 1].content,
          file_path: filePath,
        }),
      });

      // 創建一個新的 ReadableStream，在開頭添加系統消息
      const stream = new ReadableStream({
        async start(controller) {
          // 首先發送系統消息
          controller.enqueue(new TextEncoder().encode(systemMessage));
          
          // 然後轉發後端的響應
          const reader = backendResponse.body!.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            controller.enqueue(value);
          }
          controller.close();
        },
      });

      return new Response(stream);
    } else {
      // 如果不需要使用工具，直接使用 OpenAI 的回應
      const systemMessage = `[系統] 直接回答您的問題...\n\n`;
      const streamResponse = await openai.chat.completions.create({
        model: process.env.OPENAI_MODEL || 'gpt-4o-mini-2024-07-18',
        stream: true,
        messages: [
          ...messages.map((message: any) => ({
            content: message.content,
            role: message.role,
          })),
        ],
      });

      // 創建一個新的 ReadableStream，在開頭添加系統消息
      const stream = new ReadableStream({
        async start(controller) {
          // 首先發送系統消息
          controller.enqueue(new TextEncoder().encode(systemMessage));
          
          // 然後轉發 OpenAI 的響應
          const reader = OpenAIStream(streamResponse).getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            controller.enqueue(value);
          }
          controller.close();
        },
      });

      return new Response(stream);
    }
  } catch (error) {
    console.error('Chat error:', error);
    if (error instanceof OpenAI.APIError) {
      const { name, status, message } = error;
      return new Response(message, { status });
    } else {
      return new Response('An error occurred', { status: 500 });
    }
  }
}