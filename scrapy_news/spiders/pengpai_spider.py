# spiders/pengpai_spider.py
import json
import time
import os
import scrapy
from scrapy_news.items import NewsItem
from scrapy_redis.spiders import RedisSpider


COOKIE_FILE = "cookies_data/pengpai_cookies.json"


def load_cookies(path: str) -> dict:
    """从浏览器导出的 JSON 读取 cookies，返回 {name: value} 字典"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
    return {}


def extract_tags(tag_list):
    """从 tagList 中提取标签，用逗号分隔"""
    if not tag_list:
        return ""
    tags = []
    for t in tag_list:
        tag_name = t.get("tag", "").strip()
        if tag_name:
            tags.append(tag_name)
    return ",".join(tags)


def get_detail_data(data, page, channel):
    """解析数据，直接返回与央视新闻格式一致的列表

    分布式说明：不再使用实例级 seen 集合（多节点/多进程间不共享，形同虚设），
    去重统一交给 RFPDupeFilter（请求级）+ Pipeline 的 Redis MD5（item 级）。
    """
    all_list = []
    start_time = int(time.time() * 1000)

    # 置顶内容
    top_content = data.get("data", {}).get("topContent")
    if top_content:
        cont_id = top_content.get("contId")
        if cont_id:
            tag_list = top_content.get("tagList", [])
            tag_str = extract_tags(tag_list)

            all_list.append({
                "标题": top_content.get("name", ""),
                "简介": top_content.get("nodeInfo", {}).get("summarize", ""),
                "关键词": tag_str,
                "发布时间": top_content.get('pubTime', ""),
                "详情链接": f"https://www.thepaper.cn/newsDetail_forward_{cont_id}",
                "频道": channel,
                "来源": "澎湃新闻"
            })

    # 新闻列表
    news_list = data.get("data", {}).get("pageInfo", {}).get("list", [])
    if not news_list:
        news_list = data.get("data", {}).get("list", [])

    if not news_list:
        print(f"第{page}页无数据，停止")
        return all_list, start_time

    for new in news_list:
        cont_id = new.get("contId")
        if cont_id:
            tag_list = new.get("tagList", [])
            tag_str = extract_tags(tag_list)

            all_list.append({
                "标题": new.get("name", ""),
                "简介": new.get("nodeInfo", {}).get("summarize", ""),
                "关键词": tag_str,
                "发布时间": new.get("pubTime", ""),
                "详情链接": f"https://www.thepaper.cn/newsDetail_forward_{cont_id}",
                "频道": channel,
                "来源": "澎湃新闻"
            })

    print(f"第{page}页: {len(news_list)} 条, 新增: {len(all_list)} 条")

    if data.get("data", {}).get("pageInfo", {}).get("startTime"):
        start_time = data["data"]["pageInfo"]["startTime"]
    elif data.get("data", {}).get("startTime"):
        start_time = data["data"]["startTime"]

    return all_list, start_time


class PengpaiSpider(RedisSpider):
    name = "pengpai"
    redis_key = "pengpai:start_urls"   # 共享队列模式下显式声明种子 key

    # ========== 最大翻页数（每个频道最多爬取的页数）==========
    MAX_PAGES = 1

    # ========== 只有这个爬虫生效的配置 ==========
    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'client-type': '1',
            'content-type': 'application/json',
            'origin': 'https://www.thepaper.cn',
            'referer': 'https://www.thepaper.cn/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0',
        },
        'COOKIES_ENABLED': True,
        # 'COOKIES': {...}  已删除硬编码，改为从 JSON 动态加载
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 5,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookies = load_cookies(COOKIE_FILE)
        self.logger.info(f"已加载 cookies: {list(self.cookies.keys())}")

    async def start(self):
        """获取频道列表，然后为每个频道生成请求"""
        self.logger.info("=" * 60)
        self.logger.info("澎湃爬虫启动！")
        self.logger.info("=" * 60)
        self.logger.info(f"每个频道最大翻页数: {self.MAX_PAGES}")

        yield scrapy.Request(
            url='https://cache.thepaper.cn/contentapi/node/getWwwAllNodes',
            cookies=self.cookies,
            callback=self.parse_channels,
        )

    def parse_channels(self, response):
        """解析频道列表，生成每个频道的新闻请求"""
        data = response.json()
        all_channels = data['data']['channelList']

        skip_channels = {"播客", "视频", "直播", "短剧"}

        for channel in all_channels[1:12]:
            channel_name = channel['name']
            if channel_name in skip_channels:
                continue

            channel_id = channel['nodeId']

            if channel_name == "精选":
                url = "https://api.thepaper.cn/contentapi/channel/depth"
            else:
                url = "https://api.thepaper.cn/contentapi/nodeCont/getByChannelId"

            self.logger.info(f"正在爬取 {channel_name} 频道")

            yield scrapy.Request(
                url=url,
                method='POST',
                headers={'Content-Type': 'application/json'},
                cookies=self.cookies,
                body=json.dumps({
                    "channelId": channel_id,
                    'pageSize': 20,
                    'cardMode': 152,
                    'startTime': str(int(time.time() * 1000)),
                    'pageNum': 1,
                }),
                meta={
                    'channel': channel_name,
                    'channel_id': channel_id,
                    'url_type': 'depth' if channel_name == "精选" else 'normal',
                    'page': 1,
                },
                callback=self.parse_news
            )

    def parse_news(self, response):
        """解析新闻列表"""
        channel = response.meta['channel']
        current_page = response.meta['page']
        channel_id = response.meta['channel_id']
        url_type = response.meta['url_type']

        self.logger.info(f"正在解析 {channel} 频道，第 {current_page} 页")

        data = response.json()

        news_list, start_time = get_detail_data(data, current_page, channel)

        # 生成 Item
        for news in news_list:
            item = NewsItem()
            item['标题'] = news['标题']
            item['简介'] = news['简介']
            item['关键词'] = news['关键词']
            item['发布时间'] = news['发布时间']
            item['详情链接'] = news['详情链接']
            item['频道'] = news['频道']
            item['来源'] = '澎湃新闻'
            yield item

        # ========== 翻页逻辑（最多爬取 MAX_PAGES 页） ==========
        if current_page >= self.MAX_PAGES:
            self.logger.info(f"{channel} 频道已爬取到最大页数 {self.MAX_PAGES}，停止翻页")
            return

        if url_type == 'depth':
            has_next = data.get('data', {}).get('pageInfo', {}).get('hasNext', False)
        else:
            has_next = data.get('data', {}).get('hasNext', False)

        if has_next:
            next_page = current_page + 1
            if url_type == 'depth':
                url = "https://api.thepaper.cn/contentapi/channel/depth"
            else:
                url = "https://api.thepaper.cn/contentapi/nodeCont/getByChannelId"

            self.logger.info(f"继续翻页: {channel} 频道，第 {next_page} 页")
            yield scrapy.Request(
                url=url,
                method='POST',
                headers={'Content-Type': 'application/json'},
                cookies=self.cookies,
                body=json.dumps({
                    "channelId": channel_id,
                    'pageSize': 20,
                    'cardMode': 152,
                    'startTime': str(start_time),
                    'pageNum': next_page,
                }),
                meta={
                    'channel': channel,
                    'channel_id': channel_id,
                    'url_type': url_type,
                    'page': next_page,
                },
                callback=self.parse_news
            )
        else:
            self.logger.info(f"{channel} 频道没有更多数据了")