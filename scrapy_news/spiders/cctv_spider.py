import scrapy
import json
import re
from typing import Optional, List
from scrapy_new.scrapy_news.items import NewsItem


def parse_jsonp(text: str) -> Optional[dict]:
    """解析JSONP格式的响应"""
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
    """从API数据中提取新闻列表"""
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


class CctvSpider(scrapy.Spider):
    name = "cctv"

    # ========== 频道配置 ==========
    channels = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']
    PAGE_SIZE = 1  # 每页数量
    MAX_PAGES = 1  # 最大翻页数（1表示只爬第一页）

    # ========== 爬虫专属配置 ==========
    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Referer': 'https://cn.bing.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'
        },
        'COOKIES': {
            'cna': 'iPXsIv/e30ICAXs1fPIQXk11',
            'HMF_CI': 'ee87bd7344039c8d265eca6c8a88ab3e6f8502e7fde49d6dff935f585c00e43946b905054021ec526198c23cb199c29466750973f7f3ccf0fc603eebb6957aa495',
            'sca': '94dd4c40',
            'HMY_JC': '7f72a18db48d17ea3be1c4f50ec39138ff76ee82a3d649da6431c2589ab54cd0d1,',
            'HBB_HC': '7944b375fb08396d8b2758583d7d106e41004248999c56618ff5f69a3269055681ca0373dba19164283dd590babc17b6e1',
            'atpsida': '9185062880b51ec5a830a34b_1787530164_5'
        },
        'COOKIES_ENABLED': True,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 10,
    }

    def start_requests(self):
        """为每个频道生成初始请求"""
        self.logger.info("=" * 60)
        self.logger.info("🚀 央视爬虫启动")
        self.logger.info("=" * 60)
        self.logger.info(f"频道列表: {self.channels}")
        self.logger.info(f"每页数量: {self.PAGE_SIZE}")
        self.logger.info(f"最大翻页: {self.MAX_PAGES}")

        for channel in self.channels:
            url = f"https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/{channel}_{self.PAGE_SIZE}.jsonp"
            self.logger.info(f"正在爬取 {channel} 频道")
            yield scrapy.Request(
                url,
                meta={'channel': channel, 'page': self.PAGE_SIZE},
                callback=self.parse,
                errback=self.handle_error
            )

    def handle_error(self, failure):
        """处理请求错误"""
        self.logger.error(f"请求失败: {failure.request.url if failure.request else '未知URL'}, 错误: {failure.value}")

    def parse(self, response):
        """解析API响应，提取新闻数据"""
        channel = response.meta['channel']
        current_page = response.meta['page']
        self.logger.info(f"正在解析 {channel} 频道，第 {current_page} 页")

        # 检查响应状态
        if response.status != 200:
            self.logger.error(f"状态码异常: {response.status}, URL: {response.url}")
            return

        # 解析JSONP数据
        json_data = parse_jsonp(response.text)
        if json_data is None:
            self.logger.error(f"解析JSON失败: {response.url}")
            self.logger.debug(f"响应内容预览: {response.text[:200]}")
            return

        # 提取新闻列表
        news_list = get_detail_data(json_data)
        self.logger.info(f"提取到 {len(news_list)} 条新闻")

        # 生成Item
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

        # ========== 翻页逻辑 ==========
        # 如果当前页数小于最大页数，且新闻数量达到每页上限，继续请求下一页
        if current_page < self.MAX_PAGES and len(news_list) >= 20:
            next_page = current_page + 1
            next_url = f"https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/{channel}_{next_page}.jsonp"
            self.logger.info(f"继续翻页: {channel} 频道，第 {next_page} 页")
            yield scrapy.Request(
                next_url,
                meta={'channel': channel, 'page': next_page},
                callback=self.parse,
                errback=self.handle_error
            )
        elif current_page >= self.MAX_PAGES:
            self.logger.info(f"{channel} 频道已爬取到最大页数 {self.MAX_PAGES}，停止翻页")