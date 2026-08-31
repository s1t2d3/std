"""
工具函数模块
为新闻Agent提供各种工具调用
"""
from datetime import datetime
from langchain_core.tools import tool

from rag.rag_service import news_rag
from utils.logger_handler import logger

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


@tool(description="获取用户所在城市名称，以纯字符串形式返回")
def get_city() -> str:
    import random
    return random.choice(["北京", "上海", "广州", "深圳", "杭州"])


@tool(description="根据城市名称查询天气，以纯字符串形式返回")
def get_weather(city: str) -> str:
    weather_data = {
        "北京": {"weather": "晴", "temperature": "28", "humidity": "45%"},
        "上海": {"weather": "多云", "temperature": "26", "humidity": "60%"},
        "广州": {"weather": "雷阵雨", "temperature": "30", "humidity": "75%"},
        "深圳": {"weather": "多云", "temperature": "28", "humidity": "70%"},
        "杭州": {"weather": "小雨", "temperature": "24", "humidity": "80%"}
    }
    if city in weather_data:
        data = weather_data[city]
        return f"{city}天气：{data['weather']}，温度{data['temperature']}°C，湿度{data['humidity']}"
    return f"{city}天气：晴，温度26°C，湿度50%"


# 导出所有工具
tools = [
    rag_summarize,
    get_current_date,
    get_news_by_date,
    search_news_by_keyword,
    get_city,
    get_weather
]