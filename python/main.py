from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from pydantic import BaseModel, validator
from pydantic_ai import Agent, RunContext
import RestrictedPython
from RestrictedPython import safe_builtins, compile_restricted
from RestrictedPython.Guards import safe_globals, guarded_iter_unpack_sequence
import json
import re
import pprint

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CodeGenerationResult(BaseModel):
    """代碼生成結果模型"""
    code: str

    @validator('code')
    def clean_code(cls, value):
        """清理生成的代碼"""
        # 如果是 RunResult 對象，提取其中的代碼內容
        if hasattr(value, 'data'):
            value = value.data
        
        # 將字符串轉換為原始字符串以處理轉義字符
        value = str(value)
        
        # 移除所有非代碼內容
        value = re.sub(r"RunResult\(.*?\)", "", value, flags=re.DOTALL)
        value = re.sub(r"ModelResponse\(.*?\)", "", value, flags=re.DOTALL)
        value = re.sub(r"TextPart\(.*?\)", "", value, flags=re.DOTALL)

        # 移除 Markdown 代碼塊標記
        value = re.sub(r"```(?:python)?\s*", "", value)
        value = re.sub(r"```", "", value)
        
        # 移除多餘的反斜線和引號轉義
        value = value.replace('\\\\', '\\')
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')
        
        # 移除非代碼的提示文字
        value = re.sub(r"2\..*?result.*?最終結果。.*?\n", "", value, flags=re.DOTALL)
        
        # 移除多餘的空行和空格，但保持代碼縮進
        lines = [line.rstrip() for line in value.splitlines()]
        value = '\n'.join(line for line in lines if line.strip())
        
        return value.strip()

class AgentDependencies(BaseModel):
    file_path: Optional[str] = None

class AnalysisResult(BaseModel):
    content: str

class UploadResponse(BaseModel):
    path: str
    rows: int
    columns: int

class ErrorResponse(BaseModel):
    error: str
def get_safe_globals():
    """Get restricted globals for safe Python execution"""
    safe_builtins = {
        # 基本運算和類型
        'abs': abs, 'len': len, 'max': max, 'min': min,
        'sum': sum, 'round': round, 'sorted': sorted,
        'list': list, 'dict': dict, 'set': set,
        'str': str, 'int': int, 'float': float,
        'bool': bool, 'enumerate': enumerate,
        'zip': zip, 'map': map, 'filter': filter,
        'print': print,
        'isinstance': isinstance,
        # RestrictedPython 所需的特殊函數
        '_getiter_': iter,
        '_getattr_': getattr,
        '_getitem_': lambda obj, key: obj[key],
        '_write_': lambda x: x,  # 允許打印輸出
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        # 其他必要的內建函數
        'getattr': getattr,
        'hasattr': hasattr,
        'range': range,
        'any': any, 'all': all,
        'Exception': Exception,
        '__import__': __import__
    }

    # 創建一個受限制的 pandas 對象
    safe_pd = pd
    safe_pd_funcs = [
        # 文件操作
        'read_excel', 'ExcelFile',
        # 數據結構
        'DataFrame', 'Series', 'Index',
        # 數據操作
        'concat', 'merge', 'to_datetime', 'to_json', 'json_normalize',
        # 數據查詢
        'isnull', 'notnull', 'isna', 'notna',
        # 數據分組和聚合
        'groupby', 'agg', 'sum', 'mean', 'count', 'value_counts',
        # 數據排序和選擇
        'sort_values', 'head', 'tail', 'loc', 'iloc',
        # 數據清理
        'fillna', 'dropna', 'replace',
        # 索引操作
        'reset_index', 'set_index',
        # 類型轉換
        'astype', 'convert_dtypes',
        # 時間序列
        'date_range', 'to_datetime',
        # 字符串操作
        'str',
    ]
    
    restricted_pd = type('RestrictedPandas', (), {
        attr: getattr(pd, attr) 
        for attr in safe_pd_funcs 
        if hasattr(pd, attr)
    })()

    return {
        '__builtins__': safe_builtins,
        'pd': restricted_pd,
        'json': json,
        # 添加常用的數據處理函數
        'isinstance': isinstance,
        'getattr': getattr,
        'hasattr': hasattr,
        'print': print,
    }

def generate_code_prompt(file_path: str, sheet_names: list, total_rows: int, 
                         columns: list, dtypes: dict, query: str) -> str:
    """生成代碼生成提示"""
    return f"""基於以下 Excel 文件信息生成 Python 代碼：
文件信息：
- 路徑: {file_path}
- 工作表: {sheet_names}
- 總行數: {total_rows}
- 可用列: {columns}
- 數據類型: {dtypes}

查詢問題: {query}

請生成符合以下要求的 Python 代碼：

1. 使用以下基本結構：
import pandas as pd

try:
    df = pd.read_excel(FILE_PATH)
    # 數據處理邏輯
    result = df.to_json(orient='records', force_ascii=False)

except Exception as e:
    result = f"處理數據時發生錯誤：{{str(e)}}"

2. 確保 result 變量包含最終結果。
3. 請直接返回可執行的 Python 代碼，不要包含任何額外的標記或註釋。"""

excel_agent = Agent(
    'openai:gpt-4o-mini-2024-07-18',
    deps_type=AgentDependencies,
    system_prompt=("""你是一個 Excel 文件分析助手，可以幫助用戶分析和理解 Excel 文件的內容。
    當需要生成 Python 代碼時，請遵循以下規則：
    1. 代碼應該簡潔明瞭
    2. 使用 pandas 進行數據處理
    3. 只使用允許的函數和方法
    4. 確保代碼安全可靠
    5. 處理可能的錯誤情況
    6. 不要包含任何額外的標記或註釋
    7. 在進行條件篩選時，若需要查詢包含特定字串的內容，請使用 `.str.contains()` 
    8. 確保在處理字符串匹配時考慮到空值（`na=False`）
    9. 確保結果放回result變量中
    10. 只返回可執行的 Python 代碼，不要包含任何額外的標記或註釋
    """)
)

@excel_agent.tool
async def analyze_excel(ctx: RunContext[AgentDependencies], query: str) -> AnalysisResult:
    """
    使用安全的 Python 沙盒環境分析 Excel 文件。
    LLM 可以生成並執行 Python 代碼來回答關於 Excel 數據的問題。
    """
    if not ctx.deps or not ctx.deps.file_path:
        return AnalysisResult(content="Excel文件路徑未提供。")

    # 規範化文件路徑
    file_path = os.path.normpath(ctx.deps.file_path)

    # 檢查文件是否存在和格式
    if not os.path.exists(file_path):
        return AnalysisResult(content=f"Excel文件不存在：{file_path}")
    
    if not file_path.lower().endswith(('.xlsx', '.xls', '.xlsm')):
        return AnalysisResult(content=f"不支持的文件格式。請上傳 Excel 文件 (.xlsx, .xls, .xlsm)")

    try:
        # 讀取 Excel 文件的基本信息
        with pd.ExcelFile(file_path) as xls:
            sheet_names = xls.sheet_names
            logger.info("\n\nSheet 0 name: %s\n", sheet_names[0])
            # 預讀第一個工作表的前 5 行以獲取列名和數據類型
            df_preview = pd.read_excel(xls, sheet_name=0, nrows=5)
            
            # 獲取總行數（使用 openpyxl 引擎可以快速獲取）
            if file_path.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                sheet = wb[sheet_names[0]]
                total_rows = sheet.max_row
                wb.close()
            else:
                # 對於其他格式，使用傳統方式計算
                df_info = pd.read_excel(xls, sheet_name=0)
                total_rows = len(df_info)

        # 生成代碼提示
        code_prompt = generate_code_prompt(
            file_path=file_path,
            sheet_names=sheet_names,
            total_rows=total_rows,
            columns=list(df_preview.columns),
            dtypes=df_preview.dtypes.to_dict(),
            query=query
        )

        # 獲取 LLM 生成的代碼
        #logger.info("Generating code with prompt: %s", code_prompt)
        code_response = await excel_agent.run(code_prompt)
        
        python_code = ""
        try:
            python_code = code_response.data
            logger.debug("\n\n")
            logger.debug("Raw code response.data: \n\n%s", python_code)
            logger.debug("\n\n")
        except Exception as e:
            logger.error("Error extracting Python code: %s", str(e))
            python_code = "Error: Unable to retrieve code"

        logger.info("Code content before cleaning: %s", python_code)
        # 清理生成的代碼 - 去除多餘的代碼 看pydantic_ai 的response.data夠不夠力，不夠的話可以用下面的
        python_code = CodeGenerationResult(code=python_code).code
        logger.info("Code content after cleaning: %s", python_code)

        # 準備安全的執行環境
        globals_dict = get_safe_globals()
        globals_dict['FILE_PATH'] = file_path

        # 編譯並執行生成的代碼

        # 執行編譯並美化輸出結果
        logger.info("\n\nExecuting compiled code in sandbox...\n")
        try:
            byte_code = compile_restricted(python_code, '<inline>', 'exec')
            exec(byte_code, globals_dict)
            logger.info("\n\nExecution complete, checking 'result' variable...\n")
            logger.info("Sandbox result: %s", globals_dict.get('result'))

            # 檢查沙盒中的 result 變數
            # 美化打印 result 變量
            result = globals_dict.get('result', None)
            if result is not None:
                logger.info("\n\nSandbox result:\n%s\n", pprint.pformat(result, indent=4, width=100))
            else:
                logger.warning("\n\nResult variable not found in the sandbox execution.\n")
            if result is None:
                return AnalysisResult(content="代碼執行完成，但未生成結果。請確保代碼將結果存儲在 'result' 變數中。")

            # 格式化輸出結果
            if isinstance(result, (pd.DataFrame, pd.Series)):
                result = result.to_json(orient='records', date_format='iso', force_ascii=False)
            elif not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)

            return AnalysisResult(content=f"""分析結果：

執行的代碼：
```python
{python_code}
```

結果：
{result}
""")
        except Exception as e:
            logger.exception("\n\nError executing generated code\n")
            return AnalysisResult(content=f"""代碼執行失敗：

錯誤信息：
{str(e)}

生成的代碼：
```python
{python_code}
```

請檢查代碼並確保：
1. 所有使用的列名都存在於數據中
2. 數據類型轉換正確
3. 沒有使用未授權的函數或操作
""")
            
    except pd.errors.EmptyDataError:
        return AnalysisResult(content=f"Excel文件是空的：{file_path}")
    except pd.errors.ParserError as e:
        return AnalysisResult(content=f"無法解析Excel文件：{str(e)}")
    except Exception as e:
        logger.exception("Error in analyze_excel")
        return AnalysisResult(content=f"處理Excel文件時發生錯誤：{str(e)}")

app = FastAPI()

# CORS設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat(message: Dict[str, Any]) -> StreamingResponse:
    try:
        logger.info("Received request: %s", message)
        
        async def generate_response():
            content = message.get("content", "")
            messages = message.get("messages", [])
            
            file_path = None
            for msg in messages:
                logger.debug("Processing message: %s", msg)
                if msg.get("role") == "system" and msg.get("id") == "file-info":
                    file_info = msg.get("content", "")
                    logger.info("Found file info: %s", file_info)
                    if "路徑：" in file_info:
                        file_path = file_info.split("路徑：")[1].split("\n")[0].strip()
                        # 使用絕對路徑
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(file_path)
                        file_path = os.path.normpath(file_path)
                        logger.info("Extracted and normalized file path: %s", file_path)
                    break
            
            if not file_path:
                logger.warning("No file path found in messages")
                yield "看起來您還沒有上傳任何 Excel 檔案，因此我無法進行分析。請上傳檔案後重試。"
                return
                
            if not os.path.exists(file_path):
                logger.warning("File does not exist: %s", file_path)
                yield f"找不到檔案：{file_path}"
                return
            
            logger.info("Creating dependencies with file path: %s", file_path)
            deps = AgentDependencies(file_path=file_path)
            try:
                logger.info("Running excel agent with content: %s", content)
                result = await excel_agent.run(content, deps=deps)
                logger.info("Got result: %s", result)
                
                if hasattr(result, 'data'):
                    if isinstance(result.data, AnalysisResult):
                        logger.info("Yielding analysis result content")
                        yield result.data.content
                    else:
                        logger.info("Yielding string representation of result data")
                        yield str(result.data)
                else:
                    logger.warning("Result has no data attribute: %s", result)
                    yield str(result)
            except Exception as e:
                logger.exception("Error during analysis")
                yield f"處理過程中發生錯誤：{str(e)}"

        return StreamingResponse(generate_response(), media_type="text/plain")
    except Exception as e:
        logger.exception("Error in chat endpoint")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error=str(e)).dict()
        )

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        df = pd.read_excel(file_path)
        rows, columns = df.shape
        
        return UploadResponse(
            path=os.path.normpath(file_path),
            rows=rows,
            columns=columns
        ).model_dump()  # 使用 model_dump 替代 dict
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)