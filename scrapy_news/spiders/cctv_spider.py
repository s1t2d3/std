import scrapy
import json
import re
import os
from typing import Optional, List
from scrapy_news.items import NewsItem
from scrapy_redis.spiders import RedisSpider

COOKIE_FILE = "cookies_data/cctv_cookies.json"

def load_cookies(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
    return {}


headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Referer': 'https://cn.bing.com/',
}

cookies = load_cookies(COOKIE_FILE)   # 模块加载时读取一次


def parse_jsonp(text: str) -> Optional[dict]:
    if not text or not text.strip():
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def get_detail_data(data: dict) -> List[dict]:
    all_news = []
    news_list = data.get("data", {}).get("list", [])
    for news in news_list:
        if not news:
            continue
        all_news.append({
            "标题": news.get("title", ""),
            "简介": news.get("brief", ""),
            "关键词": news.get("keywords", ""),
            "发布时间": news.get("focus_date", ""),
            "详情链接": news.get("url", ""),
            "频道": "",
            "来源": "央视新闻",
        })
    return all_news


class CctvSpider(RedisSpider):
    name = "cctv"
    redis_key = "cctv:start_urls"   # 显式声明种子 key（共享队列模式下仍保留 start() 生成种子）
    channels = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']
    PAGE_SIZE = 1

    async def start(self):
        self.logger.info("=" * 60)
        self.logger.info("央视爬虫启动！")
        self.logger.info(f"已加载 cookies: {list(cookies.keys())}")
        self.logger.info("=" * 60)

        for channel in self.channels:
            url = f"https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/{channel}_{self.PAGE_SIZE}.jsonp"
            self.logger.info(f"正在爬取 {channel} 频道")
            yield scrapy.Request(
                url,
                meta={'channel': channel, 'page': self.PAGE_SIZE},
                headers=headers,
                cookies=cookies,          # ← 从 JSON 读出来的字典
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.error(f"请求失败: {failure.request.url if failure.request else '未知URL'}, 错误: {failure.value}")

    def parse(self, response):
        channel = response.meta['channel']
        current_page = response.meta['page']
        self.logger.info(f"正在解析 {channel} 频道，第 {current_page} 页")

        if response.status != 200:
            self.logger.error(f"状态码异常: {response.status}, URL: {response.url}")
            return

        json_data = parse_jsonp(response.text)
        if json_data is None:
            self.logger.error(f"解析JSON失败: {response.url}")
            return

        news_list = get_detail_data(json_data)
        self.logger.info(f"提取到 {len(news_list)} 条新闻")

        for news in news_list:
            item = NewsItem()
            item["标题"] = news["标题"]
            item["简介"] = news["简介"]
            item["关键词"] = news["关键词"]
            item["发布时间"] = news["发布时间"]
            item["详情链接"] = news["详情链接"]
            item["频道"] = channel
            item["来源"] = news["来源"]
            yield item

        if len(news_list) >= 20:
            return
            # next_page = current_page + 1
            # next_url = f"https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/{channel}_{next_page}.jsonp"
            # self.logger.info(f"继续翻页: {channel} 频道，第 {next_page} 页")
            # yield scrapy.Request(
            #     next_url,
            #     meta={'channel': channel, 'page': next_page},
            #     callback=self.parse,
            #     errback=self.handle_error)