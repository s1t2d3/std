"""
工具函数模块
为新闻Agent提供各种工具调用
"""
from datetime import datetime
from langchain_core.tools import tool

from rag.rag_service import news_rag
from utils_tool.logger_handler import logger

# 摘要模式标志
_is_summary = False


def set_summary_mode(value: bool):
    global _is_summary
    _is_summary = value


def get_summary_mode() -> bool:
    return _is_summary


@tool(description="根据问题查询新闻资料，并生成总结或摘要，以纯字符串形式返回。支持今日新闻摘要、具体新闻查询等")
def rag_summarize(query: str) -> str:
    try:
        keywords = ["今日新闻", "新闻摘要", "今天发生", "今日要闻", "每日新闻", "今天有什么新闻"]
        if any(kw in query for kw in keywords):
            set_summary_mode(True)
        else:
            set_summary_mode(False)
        return news_rag.get_news_answer(query)
    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}", exc_info=True)
        return f"查询新闻时出现错误，请稍后重试。"


@tool(description="获取当前日期，格式为YYYY-MM-DD，以纯字符串形式返回")
def get_current_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@tool(description="根据指定日期查询当天的所有新闻，以纯字符串形式返回。日期格式为YYYY-MM-DD")
def get_news_by_date(date: str) -> str:
    try:
        set_summary_mode(True)
        return news_rag.get_daily_summary(date=date)
    except Exception as e:
        logger.error(f"按日期查询新闻失败: {str(e)}", exc_info=True)
        return f"查询{date}的新闻时出现错误，请稍后重试。"


@tool(description="根据关键词搜索相关新闻，返回结构化的新闻列表，包含标题、简介、时间和链接。关键词为纯文本字符串")
def search_news_by_keyword(keyword: str) -> str:
    try:
        results = news_rag.search_news_by_keyword(keyword, limit=5)
        if not results:
            return f"未找到与'{keyword}'相关的新闻"

        output = f"找到 {len(results)} 条与'{keyword}'相关的新闻：\n\n"
        for i, item in enumerate(results, 1):
            output += f"{i}. 【{item['title']}】\n"
            output += f"   简介：{item['summary'][:100]}...\n" if len(item['summary']) > 100 else f"   简介：{item['summary']}\n"
            output += f"   发布时间：{item['publish_time']}\n"
            output += f"   来源：{item['source']}\n"
            if item.get('link'):
                output += f"   🔗 链接：{item['link']}\n"
            output += "\n"
        return output
    except Exception as e:
        logger.error(f"搜索新闻失败: {str(e)}", exc_info=True)
        return f"搜索新闻时出现错误，请稍后重试。"

# 导出所有工具
tools = [
    rag_summarize,
    get_current_date,
    get_news_by_date,
    search_news_by_keyword,
]