from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from pydantic import BaseModel, validator, Field
from pydantic_ai import Agent, RunContext
import RestrictedPython
from RestrictedPython import safe_builtins, compile_restricted
from RestrictedPython.Guards import safe_globals, guarded_iter_unpack_sequence
import json
import re
import pprint
from pathlib import Path
from dotenv import load_dotenv
import black

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
ENV_PATH = ROOT_DIR / '.env.local'

# Load environment variables
load_dotenv(ENV_PATH)

# Debug print to verify environment variables
logger.info(f"Using AI Model: {os.getenv('AI_MODEL')}")

class ExcelQuery(BaseModel):
    query: str = Field(..., description="Natural language query for Excel data")
    file_path: Optional[str] = Field(None, description="Path to Excel file")

class ExcelQueryResult(BaseModel):
    result: Any
    explanation: str

def format_code_with_black(code: str) -> str:
    try:
        # 使用 Black 格式化代碼
        formatted_code = black.format_str(code, mode=black.Mode())
        return formatted_code
    except black.InvalidInput:
        # 如果代碼無效，返回原始代碼
        return code

class CleanCodeResult(BaseModel):
    """清理代碼的結果"""
    code: str = Field(description="清理後的代碼")
    
    def __init__(self, **data):
        if isinstance(data.get('code'), str):
            # 從代碼塊中提取代碼
            code = data['code']
            if '```python' in code:
                start = code.find('```python') + 9
                end = code.rfind('```')
                if end > start:
                    code = code[start:end].strip()
            data['code'] = code
        super().__init__(**data)

    @validator('code')
    def clean_code(cls, value):
        """清理生成的代碼"""
        # 如果有 data 屬性，提取其內容
        if hasattr(value, 'data'):
            value = value.data

        # 確保 value 是字符串類型
        value = str(value)

        # 正則清理不必要的內容
        patterns_to_remove = [
            r"RunResult\(.*?\)",        # 移除 RunResult
            r"ModelResponse\(.*?\)",   # 移除 ModelResponse
            r"TextPart\(.*?\)",        # 移除 TextPart
            r"2\..*?result.*?最終結果。.*?\n"  # 特定結果信息的模式
        ]

        for pattern in patterns_to_remove:
            value = re.sub(pattern, "", value, flags=re.DOTALL)

        # 修正轉義字符問題
        value = value.replace('\\\\', '\\')
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')

        # 移除空白行和多餘的空格
        lines = [line.rstrip() for line in value.splitlines() if line.strip()]
        value = '\n'.join(lines)

        # 返回清理後的結果
        try:
            value = black.format_str(value, mode=black.Mode())
            print(value)
        except black.InvalidInput:
            # 如果代碼無效，保持清理後的原樣
            pass
        return value.strip()

class AgentDependencies(BaseModel):
    """Agent 的依賴項"""
    file_path: str = Field(description="Excel 文件的絕對路徑")
    
    def __init__(self, **data):
        super().__init__(**data)
        logger.info(f"Creating AgentDependencies with data: {data}")
        # 確保文件路徑是絕對路徑
        if not os.path.isabs(self.file_path):
            self.file_path = os.path.abspath(self.file_path)
        # 標準化路徑分隔符
        self.file_path = os.path.normpath(self.file_path)
        logger.info(f"Initialized AgentDependencies with file_path: {self.file_path}")

class AnalysisResult(BaseModel):
    content: str

class UploadResponse(BaseModel):
    path: str
    rows: int
    columns: int

class ErrorResponse(BaseModel):
    error: str

class Tool(BaseModel):
    type: str = "function"
    function: Dict[str, Any]

class ExcelTool:
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.file_path: Optional[str] = None

    def load_excel(self, file_path: str) -> None:
        """載入 Excel 文件"""
        if not file_path:
            raise ValueError("No file path provided")
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            self.df = pd.read_excel(file_path)
            self.file_path = file_path
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {str(e)}")

    def get_column_info(self) -> Dict[str, str]:
        """獲取所有列的資訊"""
        if self.df is None:
            return {}
        
        return {
            col: str(dtype) for col, dtype in self.df.dtypes.items()
        }

    def execute_query(self, query: str) -> ExcelQueryResult:
        """執行自然語言查詢"""
        if self.df is None:
            raise ValueError("No Excel file loaded")

        # 獲取基本資訊
        info = {
            "columns": list(self.df.columns),
            "shape": self.df.shape,
            "dtypes": self.get_column_info()
        }

        # 根據查詢類型執行不同操作
        if "sum" in query.lower() or "total" in query.lower():
            # 處理求和查詢
            col = self._extract_column_from_query(query)
            if col:
                result = self.df[col].sum()
                return ExcelQueryResult(
                    result=float(result),
                    explanation=f"計算了 {col} 列的總和"
                )

        elif "average" in query.lower() or "mean" in query.lower():
            # 處理平均值查詢
            col = self._extract_column_from_query(query)
            if col:
                result = self.df[col].mean()
                return ExcelQueryResult(
                    result=float(result),
                    explanation=f"計算了 {col} 列的平均值"
                )

        elif "find" in query.lower() or "where" in query.lower():
            # 處理條件查詢
            condition = self._extract_condition_from_query(query)
            if condition:
                filtered_df = self.df.query(condition)
                return ExcelQueryResult(
                    result=filtered_df.to_dict('records'),
                    explanation=f"根據條件 '{condition}' 篩選了數據"
                )

        # 默認返回數據預覽
        return ExcelQueryResult(
            result=self.df.head().to_dict('records'),
            explanation="返回了前 5 行數據作為預覽"
        )

    def _extract_column_from_query(self, query: str) -> Optional[str]:
        """從查詢中提取列名"""
        for col in self.df.columns:
            if col.lower() in query.lower():
                return col
        return self.df.columns[0]  # 默認使用第一列

    def _extract_condition_from_query(self, query: str) -> Optional[str]:
        """從查詢中提取條件"""
        # 這裡使用簡單的規則，實際應用中可能需要更複雜的 NLP
        for col in self.df.columns:
            if col.lower() in query.lower():
                words = query.lower().split()
                col_idx = words.index(col.lower())
                if col_idx + 2 < len(words):
                    value = words[col_idx + 2]
                    return f"{col} == '{value}'"
        return None

def get_safe_globals():
    """Get restricted globals for safe Python execution"""
    safe_builtins = {
        'abs': abs, 'len': len, 'max': max, 'min': min,
        'sum': sum, 'round': round, 'sorted': sorted,
        'list': list, 'dict': dict, 'set': set,
        'str': str, 'int': int, 'float': float,
        'bool': bool, 'enumerate': enumerate,
        'zip': zip, 'map': map, 'filter': filter,
        'isinstance': isinstance,
        '_getiter_': iter,
        '_getattr_': getattr,
        '_getitem_': lambda obj, key: obj[key],
        '_write_': lambda x: x,
        '_print_': lambda *args, **kwargs: None,  # 使用空的 print 函數
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        'getattr': getattr,
        'hasattr': hasattr,
        'range': range,
        'any': any, 'all': all,
        'Exception': Exception,
        '__import__': __import__
    }

    safe_pd_funcs = [
        'read_excel', 'ExcelFile',
        'DataFrame', 'Series', 'Index',
        'concat', 'merge', 'to_datetime', 'to_json', 'json_normalize',
        'isnull', 'notnull', 'isna', 'notna',
        'groupby', 'agg', 'sum', 'mean', 'count', 'value_counts',
        'sort_values', 'head', 'tail', 'loc', 'iloc',
        'fillna', 'dropna', 'replace',
        'reset_index', 'set_index',
        'astype', 'convert_dtypes',
        'date_range', 'to_datetime',
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
        'isinstance': isinstance,
        'getattr': getattr,
        'hasattr': hasattr,
        'print': lambda *args, **kwargs: None,  # 使用空的 print 函數
    }

def generate_code_prompt(
    file_path: str,
    sheet_names: List[str],
    total_rows: int,
    columns: List[str],
    dtypes: Dict[str, Any],
    query: str
) -> str:
    """生成代碼提示"""
    return f"""Please generate Python code to analyze the Excel file.

File information:
- File path: {file_path}
- Sheets: {sheet_names}
- Total rows: {total_rows}
- Column names: {columns}
- Data types: {dtypes}

Query content: {query}

Please generate code that meets the following requirements:
1. Use pandas to read and process the data
2. Use English variable names to avoid Chinese characters
3. Ensure the result variable contains the final result
4. Use try-except to handle exceptions
5. If the result is a DataFrame or Series, use to_json(orient='records', force_ascii=False) to convert it to a JSON string
6. store result in a variable named 'result'"""

excel_agent = Agent(
    os.getenv('AI_MODEL', 'openai:gpt-4o-mini-2024-07-18'),
    deps_type=AgentDependencies,
    retries=50,
    system_prompt="""你是一個 Excel 文件分析助手，可以幫助用戶分析和理解 Excel 文件的內容。

你的主要任務是分析 Excel 文件並回答用戶的查詢。你有一個工具可以幫助你完成這個任務。

請記住：
1. 用戶的查詢已經包含了文件路徑，你不需要再詢問文件
2. 直接使用工具來處理查詢，不要自己回答
3. 將工具返回的結果直接返回給用戶，不要添加任何額外的解釋"""
)

excel_tool = ExcelTool()

@excel_agent.tool
async def analyze_excel(ctx: RunContext[AgentDependencies], query: str) -> AnalysisResult:
    """分析 Excel 文件並回答查詢"""
    logger.info(f"Starting Excel analysis with query: {query}")
    logger.info(f"Using model: {ctx.model}")
    
    if not ctx.deps or not ctx.deps.file_path:
        return AnalysisResult(content="Excel文件路徑未提供。")

    file_path = os.path.normpath(ctx.deps.file_path)

    if not os.path.exists(file_path):
        return AnalysisResult(content=f"Excel文件不存在：{file_path}")
    
    if not file_path.lower().endswith(('.xlsx', '.xls', '.xlsm')):
        return AnalysisResult(content=f"不支持的文件格式。請上傳 Excel 文件 (.xlsx, .xls, .xlsm)")

    try:
        # 先嘗試使用簡單的查詢工具
        with pd.ExcelFile(file_path) as xls:
            sheet_names = xls.sheet_names
            df_preview = pd.read_excel(xls, sheet_name=0, nrows=5)
            
            if file_path.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                sheet = wb[sheet_names[0]]
                total_rows = sheet.max_row
                wb.close()
            else:
                df_info = pd.read_excel(xls, sheet_name=0)
                total_rows = len(df_info)

        code_prompt = generate_code_prompt(
            file_path=file_path,
            sheet_names=sheet_names,
            total_rows=total_rows,
            columns=list(df_preview.columns),
            dtypes=df_preview.dtypes.to_dict(),
            query=query
        )

        logger.info(f"Sending code generation request to model: {excel_agent.model}")
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

        logger.info("Code content before cleaning: %s\n\n", python_code)

        python_code = CleanCodeResult(code=code_response.data).code
        logger.info("Code content after cleaning:\n\n %s", python_code)

        globals_dict = get_safe_globals()
        globals_dict['FILE_PATH'] = file_path


        logger.info("\n\nExecuting compiled code in sandbox...\n")
        try:
            byte_code = compile_restricted(python_code, '<inline>', 'exec')
            exec(byte_code, globals_dict)
            
            result = globals_dict.get('result')
            if result is None:
                return AnalysisResult(content="代碼執行完成，但未生成結果。")

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

    except Exception as e:
        logger.exception("Error in analyze_excel")
        return AnalysisResult(content=f"處理Excel文件時發生錯誤：{str(e)}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tools")
async def get_tools() -> List[Tool]:
    """Return available tools based on current system capabilities"""
    tools = [
        Tool(
            type="function",
            function={
                "name": "query_excel",
                "description": "Query Excel files using natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query for Excel data"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to Excel file (optional)"
                        }
                    },
                    "required": ["query"]
                }
            }
        )
    ]
    
    return tools

@app.post("/api/excel")
async def query_excel(request: ExcelQuery) -> Dict[str, Any]:
    try:
        logger.info(f"Querying Excel with: {request}")
        
        # 確保文件路徑是絕對路徑
        if request.file_path:
            if not os.path.isabs(request.file_path):
                request.file_path = os.path.join(ROOT_DIR, request.file_path)
            
            request.file_path = os.path.normpath(request.file_path)
            logger.info(f"Absolute file path: {request.file_path}")
            logger.info(f"File exists: {os.path.exists(request.file_path)}")
            
            if not os.path.exists(request.file_path):
                logger.error(f"File not found: {request.file_path}")
                return JSONResponse(
                    status_code=404,
                    content={"error": f"File not found: {request.file_path}"}
                )
            
            try:
                # 設置 agent 的依賴
                deps = AgentDependencies(file_path=request.file_path)
                logger.info(f"Agent deps file_path: {deps.file_path}")
                
                # 使用 excel_agent 分析查詢
                response = await excel_agent.run(
                    f"""使用工具分析以下 Excel 查詢：
                    查詢內容：{request.query}""",
                    deps=deps
                )
                
                logger.info(f"Successfully analyzed Excel file: {response}")
                return JSONResponse(content=response.data)
                
            except Exception as e:
                logger.error(f"Failed to analyze Excel file: {str(e)}")
                return JSONResponse(
                    status_code=400,
                    content={"error": f"無法分析 Excel 文件: {str(e)}"}
                )
        else:
            logger.error("No file path provided")
            return JSONResponse(
                status_code=400,
                content={"error": "請提供 Excel 文件路徑"}
            )
            
    except Exception as e:
        logger.error(f"Error querying Excel: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"查詢失敗: {str(e)}"}
        )

@app.post("/api/chat")
async def chat(message: Dict[str, Any]) -> StreamingResponse:
    try:
        logger.info("Received request: %s", message)
        
        async def generate_response():
            content = message.get("content", "")
            file_path = message.get("file_path", "")
            
            if not file_path:
                yield "看起來您還沒有上傳任何 Excel 檔案，因此我無法進行分析。請上傳檔案後重試。"
                return
            
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            file_path = os.path.normpath(file_path)
                
            if not os.path.exists(file_path):
                yield f"找不到檔案：{file_path}"
                return
            
            deps = AgentDependencies(file_path=file_path)
            try:
                result = await excel_agent.run(content, deps=deps)
                
                if hasattr(result, 'data'):
                    if isinstance(result.data, AnalysisResult):
                        yield result.data.content
                    else:
                        yield str(result.data)
                else:
                    yield str(result)
            except Exception as e:
                yield f"處理過程中發生錯誤：{str(e)}"

        return StreamingResponse(generate_response(), media_type="text/plain")
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error=str(e)).dict()
        )

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"Receiving file: {file.filename}")
        
        # 使用絕對路徑
        upload_dir = os.path.join(ROOT_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        logger.info(f"Upload directory: {upload_dir}")
        
        file_path = os.path.join(upload_dir, file.filename)
        logger.info(f"File path: {file_path}")
        
        # 檢查文件是否為 Excel 文件
        if not file.filename.endswith(('.xlsx', '.xls')):
            error_msg = "只支持 Excel 文件 (.xlsx, .xls)"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            logger.info(f"File saved: {file_path}")
        
        try:
            logger.info("Reading Excel file...")
            df = pd.read_excel(file_path)
            rows, columns = df.shape
            logger.info(f"Excel file read successfully: {rows} rows, {columns} columns")
        except Exception as e:
            error_msg = f"無法讀取 Excel 文件: {str(e)}"
            logger.error(error_msg)
            # 如果讀取失敗，刪除文件並返回錯誤
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=error_msg)
        
        response = UploadResponse(
            path=os.path.normpath(file_path),
            rows=rows,
            columns=columns
        ).model_dump()
        logger.info("Upload successful")
        return response
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        return JSONResponse(
            status_code=he.status_code,
            content={"error": he.detail}
        )
    except Exception as e:
        error_msg = f"上傳失敗: {str(e)}"
        logger.error(f"Unexpected error: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
