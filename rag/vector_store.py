"""
向量数据库服务模块
支持新闻数据的存储和检索，包含md5去重机制
"""
from typing import List, Dict, Optional
import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from model.factory import embed_model
from utils.config_handler import chrom_config
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
import hashlib



class VectorStoreService:
    """向量数据库服务类"""

    def __init__(self) -> None:
        """初始化向量数据库"""
        self.vector_store: Chroma = Chroma(
            collection_name=chrom_config["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chrom_config["persist_directory"]),
        )

        self.spliter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(
            chunk_size=chrom_config["chunk_size"],
            chunk_overlap=chrom_config["overlap_size"],
            separators=chrom_config["separators"],
            length_function=len,
        )

    def get_retriever(self, search_kwargs: Optional[Dict] = None) -> BaseRetriever:
        if search_kwargs is None:
            search_kwargs = {"k": chrom_config.get("k", 5)}
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)

    def _check_md5(self, md5: str) -> bool:
        md5_path: str = get_abs_path(chrom_config["md5_path"])
        if not os.path.exists(md5_path):
            return False
        with open(md5_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == md5:
                    return True
        return False

    def _save_md5(self, md5: str) -> None:
        md5_path: str = get_abs_path(chrom_config["md5_path"])
        os.makedirs(os.path.dirname(md5_path), exist_ok=True)
        with open(md5_path, 'a', encoding='utf-8') as f:
            f.write(md5 + '\n')

    def load_news_documents(self, news_data: List[Dict]) -> int:
        """加载新闻JSON数据到向量库，包含md5去重"""
        if not news_data:
            logger.warning("新闻数据为空，跳过加载")
            return 0

        documents = []
        success_count = 0

        for item in news_data:
            try:
                title = item.get('标题', '无标题')
                summary = item.get('简介', '')
                publish_time = item.get('发布时间', '')
                source = item.get('来源', '')
                channel = item.get('频道', '')
                link = item.get('详情链接', '')
                keywords = item.get('关键词', '')

                # 直接使用 hashlib 计算MD5，不调用 get_md5_hex
                md5_content = f"{title}{summary}{publish_time}{link}"
                doc_md5 = hashlib.md5(md5_content.encode('utf-8')).hexdigest()

                if self._check_md5(doc_md5):
                    logger.info(f"新闻 '{title}' 已存在，跳过加载")
                    continue

                content_parts = [
                    f"标题：{title}",
                    f"简介：{summary}",
                    f"发布时间：{publish_time}",
                    f"来源：{source}",
                    f"频道：{channel}"
                ]
                if keywords:
                    content_parts.append(f"关键词：{keywords}")
                content = "\n".join(content_parts)

                doc = Document(
                    page_content=content,
                    metadata={
                        "title": title,
                        "summary": summary,
                        "publish_time": publish_time,
                        "source": source,
                        "channel": channel,
                        "link": link,
                        "keywords": keywords,
                        "type": "news",
                        "date": publish_time[:10] if publish_time else "",
                        "md5": doc_md5
                    }
                )
                documents.append(doc)
                success_count += 1
            except Exception as e:
                logger.error(f"处理新闻条目失败: {str(e)}, 数据: {item}")
                continue

        if documents:
            try:
                spliter_document = self.spliter.split_documents(documents)
                self.vector_store.add_documents(spliter_document)
                for doc in documents:
                    doc_md5 = doc.metadata.get("md5")
                    if doc_md5:
                        self._save_md5(doc_md5)
                logger.info(f"成功加载 {len(documents)} 条新闻到向量数据库")
            except Exception as e:
                logger.error(f"加载新闻到向量数据库失败: {str(e)}", exc_info=True)
                return 0

        return success_count

    def load_news_from_directory(self, directory_path: str = None) -> int:
        """从目录加载所有新闻JSON文件到向量数据库（自动去重）"""
        import json

        # 如果没有传入路径，使用配置中的目录
        if directory_path is None:
            directory_path = get_abs_path(chrom_config["directory"])

        if not os.path.exists(directory_path):
            logger.error(f"新闻目录不存在: {directory_path}")
            return 0

        total_count = 0
        json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]

        if not json_files:
            logger.warning(f"目录 {directory_path} 中没有JSON文件")
            return 0

        for json_file in json_files:
            file_path = os.path.join(directory_path, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    news_list = json.load(f)
                count = self.load_news_documents(news_list)
                total_count += count
                logger.info(f"从 {json_file} 加载了 {count} 条新新闻")
            except Exception as e:
                logger.error(f"加载文件 {json_file} 失败: {str(e)}")
                continue

        logger.info(f"总计从 {len(json_files)} 个文件加载了 {total_count} 条新新闻")
        return total_count


if __name__ == "__main__":
    vector = VectorStoreService()
    # # 加载普通文档（非新闻）- 自动跳过JSON文件
    # vector.load_document()
    # 加载新闻文件 - 使用配置中的目录
    vector.load_news_from_directory()