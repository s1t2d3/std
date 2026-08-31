"""
新闻RAG服务模块
提供新闻检索、摘要生成、问答等功能
"""
from datetime import datetime
from typing import List, Dict, Optional, Union
import json
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompt, load_summary_prompt
from utils.logger_handler import logger


class NewsRagService:
    """
    新闻RAG服务类
    支持新闻检索、摘要生成和智能问答
    """

    def __init__(self):
        """初始化新闻RAG服务"""
        # 初始化向量数据库服务
        self.vector_store = VectorStoreService()

        # 获取检索器，k值设置为10以获取更多相关文档
        self.retriever = self.vector_store.get_retriever(search_kwargs={"k": 20})

        # 加载基础问答prompt
        self.qa_prompt_text = load_rag_prompt()
        self.qa_prompt_template = PromptTemplate.from_template(self.qa_prompt_text)

        # 初始化问答链
        self.qa_chain = self._init_qa_chain()

        # 缓存当天的新闻摘要，避免重复生成
        self._cached_summary = None
        self._cached_date = None

    def _init_qa_chain(self):
        """初始化问答链"""
        return self.qa_prompt_template | chat_model | StrOutputParser()

    def load_news_to_vectorstore(self, news_data: Union[str, List[Dict]]) -> int:
        """
        将新闻数据加载到向量数据库

        Args:
            news_data: 新闻数据，可以是JSON文件路径或新闻列表

        Returns:
            int: 成功加载的新闻条数
        """
        # 如果是字符串，视为文件路径
        if isinstance(news_data, str):
            try:
                with open(news_data, 'r', encoding='utf-8') as f:
                    news_list = json.load(f)
            except Exception as e:
                logger.error(f"读取新闻文件失败: {str(e)}")
                return 0
        else:
            news_list = news_data

        # 使用VectorStoreService的load_news_documents方法
        return self.vector_store.load_news_documents(news_list)

    def _is_summary_request(self, query: str) -> bool:
        """
        检测用户是否在请求新闻摘要

        Args:
            query: 用户查询

        Returns:
            bool: 是否为摘要请求
        """
        summary_keywords = [
            "今天都发生了什么事",
            "今日新闻",
            "新闻摘要",
            "今天有什么新闻",
            "今日要闻",
            "今天发生了什么",
            "总结一下今天的新闻",
            "给我今天的新闻",
            "今日热点",
            "今天有哪些新闻",
            "今日大事",
            "今天新闻汇总",
            "每日新闻"
        ]
        query_lower = query.lower().strip()

        # 精确匹配或包含关键词
        for keyword in summary_keywords:
            if keyword in query_lower:
                return True

        # 同时包含"今天"和"新闻"也算
        if "今天" in query_lower and ("新闻" in query_lower or "发生" in query_lower):
            return True

        return False

    def _get_today_date(self) -> str:
        """获取今天的日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")

    def _filter_news_by_date(self, docs: List[Document], target_date: str) -> List[Document]:
        """
        按日期过滤新闻文档

        Args:
            docs: 文档列表
            target_date: 目标日期，格式YYYY-MM-DD

        Returns:
            List[Document]: 过滤后的文档列表
        """
        filtered_docs = []

        for doc in docs:
            # 检查元数据中的发布时间
            publish_time = doc.metadata.get('publish_time', '')
            # 如果发布时间包含目标日期，则保留
            if target_date in publish_time:
                filtered_docs.append(doc)
            # 如果没有发布时间，检查page_content是否包含日期
            elif target_date in doc.page_content:
                filtered_docs.append(doc)

        return filtered_docs

    def _format_docs_for_summary(self, docs: List[Document]) -> str:
        """
        格式化文档用于摘要生成

        Args:
            docs: 文档列表

        Returns:
            str: 格式化的文本
        """
        if not docs:
            return "暂无新闻数据"

        context = ""
        for i, doc in enumerate(docs, 1):
            context += f"\n【新闻{i}】\n"
            context += f"标题：{doc.metadata.get('title', '无标题')}\n"
            context += f"简介：{doc.metadata.get('summary', '无简介')}\n"
            context += f"来源：{doc.metadata.get('source', '未知来源')}\n"
            context += f"发布时间：{doc.metadata.get('publish_time', '未知时间')}\n"
            context += f"频道：{doc.metadata.get('channel', '未知频道')}\n"
            # 加上链接
            link = doc.metadata.get('link', '')
            if link:
                context += f"链接：{link}\n"
            context += "-" * 50 + "\n"

        return context

    def get_daily_summary(self, date: Optional[str] = None, force_refresh: bool = False) -> str:
        """
        获取每日新闻摘要

        Args:
            date: 指定日期，默认为今天，格式YYYY-MM-DD
            force_refresh: 是否强制刷新缓存

        Returns:
            str: 新闻摘要
        """
        # 确定日期
        if date is None:
            date = self._get_today_date()

        # 检查缓存
        if not force_refresh and self._cached_date == date and self._cached_summary is not None:
            return self._cached_summary

        # 构建检索查询
        query = f"{date} 新闻"

        try:
            # 检索相关文档
            all_docs = self.retriever.invoke(query)

            # 如果没有检索到文档，尝试更宽泛的检索
            if not all_docs:
                query = f"{date.replace('-', '')} 新闻"
                all_docs = self.retriever.invoke(query)

            # 如果还没有，尝试只检索日期
            if not all_docs:
                all_docs = self.retriever.invoke(date)

            # 过滤出当天的新闻
            today_docs = self._filter_news_by_date(all_docs, date)

            # 如果过滤后没有文档，使用所有检索到的文档
            if not today_docs:
                today_docs = all_docs[:20]

            if not today_docs:
                return f"抱歉，未找到{date}的新闻数据。"

            # 格式化文档
            context = self._format_docs_for_summary(today_docs)

            # 生成摘要
            summary_prompt = load_summary_prompt()

            summary = self.qa_chain.invoke({
                "input": summary_prompt,
                "context": context
            })

            # 缓存结果
            self._cached_date = date
            self._cached_summary = summary

            return summary

        except Exception as e:
            logger.error(f"生成新闻摘要失败: {str(e)}", exc_info=True)
            return f"生成新闻摘要时出现错误，请稍后重试。"

    def _format_context_from_docs(self, docs: List[Document], max_docs: int = 5) -> str:
        """
        格式化文档用于问答

        Args:
            docs: 文档列表
            max_docs: 最大文档数

        Returns:
            str: 格式化的文本
        """
        if not docs:
            return "未找到相关新闻资料"

        context = ""
        for i, doc in enumerate(docs[:max_docs], 1):
            context += f"\n【参考资料{i}】\n"
            context += f"标题：{doc.metadata.get('title', '无标题')}\n"
            context += f"内容：{doc.page_content[:500]}\n"
            context += f"发布时间：{doc.metadata.get('publish_time', '未知时间')}\n"
            context += f"来源：{doc.metadata.get('source', '未知来源')}\n"
            context += "-" * 30 + "\n"

        return context

    def get_news_answer(self, query: str) -> str:
        """
        获取新闻问答答案

        Args:
            query: 用户问题

        Returns:
            str: 回答
        """
        try:
            # 先判断是否为摘要请求
            if self._is_summary_request(query):
                return self.get_daily_summary()

            # 检索相关文档
            context_docs = self.retriever.invoke(query)

            if not context_docs:
                return "抱歉，我没有找到相关的新闻信息。建议您换个关键词或问题再试试。"

            # 格式化上下文
            context = self._format_context_from_docs(context_docs)

            # 生成回答
            answer = self.qa_chain.invoke({
                "input": query,
                "context": context
            })

            return answer

        except Exception as e:
            logger.error(f"新闻问答失败: {str(e)}", exc_info=True)
            return f"回答问题时出现错误，请稍后重试。"

    def search_news_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        根据关键词搜索新闻

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            List[Dict]: 新闻列表
        """
        try:
            # 频道映射
            channel_map = {
                "体育": "体育",
                "财经": "财经",
                "科技": "科技",
                "娱乐": "娱乐",
                "时事": "时事",
                "国际": "国际"
            }

            # 如果是频道名，先检索更多文档，再按频道过滤
            if keyword in channel_map:
                docs = self.retriever.invoke("新闻")  # 获取更多
                filtered = [d for d in docs if d.metadata.get('channel') == channel_map[keyword]]
                docs = filtered[:limit]
            else:
                docs = self.retriever.invoke(keyword)

            results = []
            for doc in docs[:limit]:
                results.append({
                    "title": doc.metadata.get('title', '无标题'),
                    "summary": doc.metadata.get('summary', '无简介'),
                    "publish_time": doc.metadata.get('publish_time', '未知时间'),
                    "source": doc.metadata.get('source', '未知来源'),
                    "link": doc.metadata.get('link', ''),
                    "channel": doc.metadata.get('channel', '未知频道')
                })

            return results

        except Exception as e:
            logger.error(f"搜索新闻失败: {str(e)}", exc_info=True)
            return []

    def clear_cache(self):
        """清除摘要缓存"""
        self._cached_summary = None
        self._cached_date = None


# 创建全局实例
news_rag = NewsRagService()