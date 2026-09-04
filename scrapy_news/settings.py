# ========================================
# 项目基础配置
# ========================================
BOT_NAME = 'scrapy_news'
SPIDER_MODULES = ['scrapy_news.spiders']
NEWSPIDER_MODULE = 'scrapy_news.spiders'

# ========================================
# 全局性能配置
# ========================================
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5

# ========================================
# 重试与超时
# ========================================
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
DOWNLOAD_TIMEOUT = 15
DOWNLOAD_MAXSIZE = 0

# ========================================
# 其他全局配置
# ========================================
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

# ========================================
# Pipeline
# ========================================
ITEM_PIPELINES = {
    'scrapy_news.pipelines.NewsPipeline': 300,
}

# ========================================
# Redis 配置
# ========================================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 1

CHANNELS = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']

# ========================================
# ✅ 强制使用默认爬虫加载器（修复 DummySpiderLoader）
# ========================================
SPIDER_LOADER_CLASS = 'scrapy.spiderloader.SpiderLoader'