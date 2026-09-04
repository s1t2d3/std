from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command

from utils_tool.logger_handler import logger
from utils_tool.prompt_loader import load_system_prompt, load_summary_prompt

# 摘要模式标志
_is_summary = False


def set_summary_mode(value: bool):
    global _is_summary
    _is_summary = value


def get_summary_mode() -> bool:
    return _is_summary


@wrap_tool_call
def monitor_tools(
        request: ToolCallRequest,
        handler: ToolMessage | Command
) -> ToolMessage | Command:
    logger.info(f"[tool monitor]执行工具: {request.tool_call['name']}")
    logger.info(f"[tool monitor]传入参数: {request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具: {request.tool_call['name']}调用成功")
        return result
    except Exception as e:
        logger.error(f"[tool monitor]工具: {request.tool_call['name']}调用失败: {str(e)}")
        raise e


@before_model
def log_before_model(
        state: AgentState,
        runtime: Runtime
):
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息")
    return None


@dynamic_prompt
def report_prompt_switch(request: ModelRequest):
    """只有在摘要模式时才切换提示词"""
    if get_summary_mode():
        logger.info("[prompt_switch] 🔄 切换到摘要提示词")
        return load_summary_prompt()

    logger.info("[prompt_switch] 🔄 切换到系统提示词")
    return load_system_prompt()