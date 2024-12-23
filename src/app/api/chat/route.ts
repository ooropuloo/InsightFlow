import { NextResponse } from 'next/server'

// 定義工具
const tools = [
  {
    name: 'analyzeExcel',
    description: '分析Excel文件數據',
    parameters: {
      type: 'object',
      properties: {
        filePath: {
          type: 'string',
          description: 'Excel文件路徑'
        },
        query: {
          type: 'string',
          description: '分析查詢'
        }
      },
      required: ['filePath', 'query']
    }
  },
  {
    name: 'queryDatabase',
    description: '執行數據庫查詢',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'SQL查詢語句'
        }
      },
      required: ['query']
    }
  }
]

export async function POST(req: Request) {
  try {
    const { messages, content } = await req.json()
    
    console.log('API Route received:', { messages, content });

    const apiUrl = process.env.PYTHON_API_URL
    if (!apiUrl) {
      throw new Error('PYTHON_API_URL environment variable is not set')
    }

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages, content }),
    })

    // 檢查響應是否成功
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 創建一個 TransformStream 來處理流式響應
    const stream = new TransformStream()
    const writer = stream.writable.getWriter()
    const reader = response.body?.getReader()

    // 如果有響應體
    if (reader) {
      // 開始讀取流
      const pump = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) {
              await writer.close()
              break
            }
            await writer.write(value)
          }
        } catch (e) {
          console.error('Streaming error:', e)
          await writer.abort(e)
        }
      }

      // 開始泵送數據
      pump()
    }

    // 返回流式響應
    return new Response(stream.readable, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
      },
    })
  } catch (error) {
    console.error('API Route error:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
