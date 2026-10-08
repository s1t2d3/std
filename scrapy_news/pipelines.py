# scrapy_new/pipelines.py
import json
import os
import hashlib
from datetime import datetime
from scrapy.exceptions import DropItem
from utils_tool.path_tool import get_abs_path
import redis


class NewsPipeline:
    """统一新闻存储Pipeline - 适用于央视和澎湃"""

    def __init__(self):
        self.file_dir = None
        self.redis_client = None

    def open_spider(self, spider):
        """爬虫启动时初始化"""
        # 1. 初始化存储目录
        self.file_dir = get_abs_path("data/news")
        os.makedirs(self.file_dir, exist_ok=True)
        spider.logger.info(f"数据存储目录: {self.file_dir}")

        # 2. 初始化 Redis 连接（复用 settings 的 REDIS_URL，与调度队列/去重保持同一 db3）
        try:
            redis_url = spider.settings.get('REDIS_URL', 'redis://127.0.0.1:6379/3')
            self.redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self.redis_client.ping()
            spider.logger.info(f"Redis 去重已启用: {redis_url}")
        except Exception as e:
            self.redis_client = None
            spider.logger.warning(f"Redis 连接失败，跳过去重: {e}")

    def process_item(self, item, spider):
        """处理每个Item"""
        # 1. 数据清洗
        item = self.clean_item(item, spider)

        # 2. 补充缺失字段
        item = self.fill_missing_fields(item)

        # 3. MD5 + Redis 去重
        if not self.is_duplicate(item, spider):
            # 4. 保存到 JSON
            self.save_to_json(item, spider)
        else:
            raise DropItem(f"重复数据，跳过: {item.get('标题', '')[:30]}")

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

    def is_duplicate(self, item, spider):
        """
        用 MD5 + Redis Set 判断是否重复
        返回 True 表示重复，False 表示新数据
        """
        # 如果 Redis 没连上，跳过去重，直接放行
        if not self.redis_client:
            return False

        url = item.get('详情链接', '')
        title = item.get('标题', '')

        url_md5 = hashlib.md5(url.encode('utf-8')).hexdigest() if url else None
        title_md5 = hashlib.md5(title.encode('utf-8')).hexdigest() if title else None

        # 先判断：任一已存在就是重复
        if url_md5 and self.redis_client.sismember('news:url_md5', url_md5):
            spider.logger.debug(f"URL 重复: {url}")
            return True
        if title_md5 and self.redis_client.sismember('news:title_md5', title_md5):
            spider.logger.debug(f"标题重复: {title[:30]}...")
            return True

        # 都通过了，再一起写入 Redis
        if url_md5:
            self.redis_client.sadd('news:url_md5', url_md5)
        if title_md5:
            self.redis_client.sadd('news:title_md5', title_md5)

        return False

    def save_to_json(self, item, spider):
        """保存到JSON文件（增量合并）

        分布式提示：当前为单机本地存储，多节点会把数据分散写到各自的 data/news 目录。
        作为分布式基础先保留此方案；后续若多节点汇总，可将该目录挂为共享盘，
        或改为写数据库（注意多节点并发写同一 JSON 文件的竞态问题）。
        """
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
            except Exception:
                existing_data = []

        # 写入新数据（去重已在 is_duplicate 里做了）
        item_dict = dict(item)
        existing_data.append(item_dict)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        spider.logger.debug(f"已保存: {item_dict.get('标题', '')[:30]}...")

    def close_spider(self, spider):
        """爬虫结束时关闭 Redis 连接"""
        if self.redis_client:
            self.redis_client.close()
            spider.logger.info("Redis 连接已关闭")