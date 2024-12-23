import { PydanticTool } from 'pydantic-ai'
import * as XLSX from 'xlsx'
import sql from 'mssql'

export const tools = {
  excelAnalyzer: new PydanticTool({
    name: 'excelAnalyzer',
    description: '分析Excel文件並執行數據處理',
    inputSchema: {
      filePath: 'string',
      query: 'string',
      operation: 'string'
    },
    async handler({ filePath, query, operation }) {
      try {
        const workbook = XLSX.readFile(filePath)
        const sheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[sheetName]
        const data = XLSX.utils.sheet_to_json(worksheet)
        
        // 根據操作類型處理數據
        switch (operation) {
          case 'summary':
            return {
              rowCount: data.length,
              columns: Object.keys(data[0]),
              sample: data.slice(0, 5)
            }
          case 'analyze':
            // 實現自定義分析邏輯
            return { result: '分析結果' }
          default:
            return { error: '不支持的操作' }
        }
      } catch (error) {
        return { error: error.message }
      }
    }
  }),

  databaseQuery: new PydanticTool({
    name: 'databaseQuery',
    description: '執行MS SQL數據庫查詢',
    inputSchema: {
      query: 'string',
      parameters: 'object'
    },
    async handler({ query, parameters }) {
      try {
        await sql.connect({
          server: process.env.DB_SERVER,
          database: process.env.DB_NAME,
          user: process.env.DB_USER,
          password: process.env.DB_PASSWORD,
          options: {
            encrypt: true
          }
        })

        const result = await sql.query(query, parameters)
        return { data: result.recordset }
      } catch (error) {
        return { error: error.message }
      } finally {
        await sql.close()
      }
    }
  }),

  dataVisualizer: new PydanticTool({
    name: 'dataVisualizer',
    description: '生成數據可視化圖表',
    inputSchema: {
      data: 'array',
      chartType: 'string',
      options: 'object'
    },
    async handler({ data, chartType, options }) {
      // 這裡可以整合前端圖表庫（如 Chart.js）
      return {
        chartConfig: {
          type: chartType,
          data,
          options
        }
      }
    }
  })
}
