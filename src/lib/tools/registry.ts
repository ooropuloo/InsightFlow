import { PydanticTool } from 'pydantic-ai'
import { tools } from './definitions'

class ToolRegistry {
  private tools: Map<string, PydanticTool>

  constructor() {
    this.tools = new Map()
  }

  register(tool: PydanticTool) {
    this.tools.set(tool.name, tool)
  }

  get(name: string) {
    return this.tools.get(name)
  }

  list() {
    return Array.from(this.tools.values())
  }
}

export const registry = new ToolRegistry()

// 註冊所有工具
Object.values(tools).forEach(tool => {
  registry.register(tool)
})
