# InsightFlow

An experimental platform for testing and showcasing Pydantic AI functionality, with a special focus on its Agent and Tool system implementation. Built with Next.js and Pydantic AI, this intelligent data analysis platform supports natural language processing and Excel data analysis.

## 🔍 Project Overview

This project explores and validates:
- Pydantic AI Agent system implementation
- Tool functionality extensibility and utility
- AI-assisted data analysis capabilities
- Excel file analysis
- AI-generated code for data analysis
- Secure sandbox code execution

### Core Testing Areas
1. **Pydantic AI Agent System**
   - Agent behavior pattern research
   - Tool invocation mechanism validation
   - Conversation context management

2. **Secure Code Execution**
   - RestrictedPython environment configuration
   - Dynamic code generation and validation
   - Secure sandbox execution

3. **Natural Language Processing**
   - Query intent understanding
   - Code generation optimization
   - Result presentation improvement

## 🚀 Current Features

### Implemented Features
- Smart Dialog: GPT-4 based natural language processing
- Excel Analysis: File upload and intelligent analysis
- Secure Execution: RestrictedPython sandbox environment
- Code Generation: AI-assisted Python code generation
- Conversational Queries: Natural language to data operations

### Technical
- Modern architecture based on Next.js 14
- Complete TypeScript support
- Tailwind CSS responsive design
- Comprehensive error handling

## 🛠️ Tech Stack

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Vercel AI SDK

### Backend
- FastAPI
- Pydantic AI
- Python 3.11+
- RestrictedPython
- Pandas

## 📦 Installation and Usage

### Prerequisites
- Node.js 18+
- Python 3.11+
- OpenAI API Key

### Installation Steps

1. Clone the project
```bash
git clone <repository-url>
cd InsightFlow
```

2. Install frontend dependencies
```bash
npm install
```

3. Install backend dependencies
```bash
cd python
pip install -r requirements.txt
```

4. Environment Configuration
Create `.env.local` file:
```env
OPENAI_API_KEY=your_api_key
PYTHON_API_URL=http://127.0.0.1:8000/api/chat
```

5. Start Services
```bash
# Start backend
python main.py

# Start frontend (new terminal)
npm run dev
```

Backend will be available at http://localhost:8000

API endpoint: http://localhost:8000/api/chat

6. Start Frontend Development Server
```bash
# Development mode
npm run dev

# Production build
npm run build
npm start

# Static export
npm run build
npm run export
```

Access the application at `http://localhost:3000`

## 📈 Development Status

### Completed Features
- [x] Excel file upload functionality
- [x] Excel operations using Pydantic AI Agent and Tools
- [x] Python code generation based on user requirements
- [x] Secure sandbox code execution
- [x] Results returned to frontend

### TODO List
- [x] Frontend UI Updates
  - [x] Implement Vercel AI SDK
  - [x] Display Agent tool usage information
  - [ ] Show generated Python code
  - [x] Real-time execution progress
- [ ] Database Integration
  - [ ] Text-to-SQL conversion validation
  - [ ] Database connection and query functionality
  - [ ] Query result visualization
- [ ] Data visualization enhancement
- [ ] Batch processing functionality
- [ ] Data export features
- [ ] User permission management
- [ ] History tracking
- [ ] Reference and integrate features from other open source projects
  - [ ] Study GPT Code Interpreter implementation ([gpt-code-ui](https://github.com/ricklamers/gpt-code-ui))
  - [ ] Explore OpenCodeInterpreter features ([OpenCodeInterpreter](https://github.com/OpenCodeInterpreter/OpenCodeInterpreter))
  - [ ] Evaluate and adapt best practices from both projects

## 📝 Usage Guide

1. Upload Excel file
2. Enter natural language query in the chat
3. The system will:
   - Analyze your requirements
   - Generate appropriate Python code
   - Execute code in secure environment
   - Return analysis results

## 🤝 Contributing

Welcome to submit Issues and Pull Requests to help improve the project. Before submitting, please ensure:
1. Code follows project coding standards
2. All tests have passed
3. Related documentation is updated
