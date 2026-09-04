# scrapy_new/pipelines.py
import json
import os
from datetime import datetime
from scrapy.exceptions import DropItem
from utils_tool.path_tool import get_abs_path


class NewsPipeline:
    """统一新闻存储Pipeline - 适用于央视和澎湃"""

    def __init__(self):
        self.file_dir = None

    def open_spider(self, spider):
        """爬虫启动时初始化"""
        self.file_dir = get_abs_path("data/news")
        os.makedirs(self.file_dir, exist_ok=True)
        spider.logger.info(f"数据存储目录: {self.file_dir}")

    def process_item(self, item, spider):
        """处理每个Item"""
        # 1. 数据清洗
        item = self.clean_item(item, spider)

        # 2. 补充缺失字段
        item = self.fill_missing_fields(item)

        # 3. 保存到JSON
        self.save_to_json(item, spider)

        # 4. 可选：保存到Redis
        # self.save_to_redis(item, spider)

        return item

    def clean_item(self, item, spider):
        """数据清洗"""
        # 去除标题和简介的前后空格
        if item.get('标题'):
            item['标题'] = item['标题'].strip()
        if item.get('简介'):
            item['简介'] = item['简介'].strip()
        if item.get('关键词'):
            item['关键词'] = item['关键词'].strip()
        if item.get('详情链接'):
            item['详情链接'] = item['详情链接'].strip()

        # 如果标题为空，丢弃该Item
        if not item.get('标题'):
            raise DropItem(f"标题为空，丢弃: {item}")

        return item

    def fill_missing_fields(self, item):
        """填充缺失字段"""
        # 如果发布时间为空，使用当前时间
        if not item.get('发布时间'):
            item['发布时间'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 确保来源字段存在
        if not item.get('来源'):
            item['来源'] = '未知来源'

        return item

    def save_to_json(self, item, spider):
        """保存到JSON文件（增量合并）"""
        # 确定文件名：来源_频道_日期.json
        source = item.get('来源', 'unknown')
        channel = item.get('频道', 'unknown')
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{source}_{channel}_{date}.json"
        file_path = os.path.join(self.file_dir, filename)

        # 读取现有数据
        existing_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                existing_data = []

        # 去重（基于标题）
        item_dict = dict(item)
        existing_titles = {n.get('标题') for n in existing_data}

        if item_dict.get('标题') not in existing_titles:
            existing_data.append(item_dict)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            spider.logger.debug(f"已保存: {item_dict.get('标题')[:30]}...")
        else:
            spider.logger.debug(f"已存在，跳过: {item_dict.get('标题')[:30]}...")

    def save_to_redis(self, item, spider):
        """可选：保存到Redis"""
        try:
            import redis
            from scrapy_news import settings

            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )

            # 使用列表存储，便于后续消费
            key = f"news:{item.get('来源', 'unknown')}"
            redis_client.rpush(key, json.dumps(dict(item), ensure_ascii=False))
        except Exception as e:
            spider.logger.warning(f"Redis存储失败: {e}")

    def close_spider(self, spider):
        """爬虫结束时触发索引更新（可选）"""
        spider.logger.info("爬虫结束，可在此触发RAG索引更新")


        # vector = VectorStoreService()
        # # 加载新闻文件 - 使用配置中的目录
        # vector.load_news_from_directory()