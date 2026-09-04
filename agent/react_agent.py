from langchain.agents import create_agent

from agent.tools.agent_tools import *
from agent.tools.middleware import *
from model.factory import chat_model
from utils_tool.prompt_loader import load_system_prompt

def set_current_user(user_id):
    current_user_id = user_id


class ReactAgent:
    def __init__(self, user_id=None):

        if user_id:
            set_current_user(user_id)

        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompt(),  # 默认使用系统提示词
            tools=tools,
            middleware=[log_before_model, monitor_tools, report_prompt_switch]
        )

    def execute_stream(self, query):
        input_dict = {
            "messages": [
                {"role": "user", "content": query}
            ]
        }

        # 初始化上下文
        context = {
            "report": False,
            "is_summary": False  # 新增摘要标志
        }

        for chunk in self.agent.stream(
            input_dict,
            stream_mode="values",
            context=context
        ):
            latest_message = chunk['messages'][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"