# ========================================
# 项目基础配置
# ========================================
BOT_NAME = 'scrapy_new'
SPIDER_MODULES = ['scrapy_new.spiders']
NEWSPIDER_MODULE = 'scrapy_new.spiders'

# ========================================
# 全局性能配置（爬虫可通过 custom_settings 覆盖）
# ========================================
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# 默认下载延迟（爬虫可单独调整）
DOWNLOAD_DELAY = 0.5

# ========================================
# 重试与超时（全局统一）
# ========================================
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
DOWNLOAD_TIMEOUT = 15
DOWNLOAD_MAXSIZE = 0  # 不限制下载大小

# ========================================
# 其他全局配置
# ========================================
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

# ========================================
# Pipeline（所有爬虫共享）
# ========================================
ITEM_PIPELINES = {
    'scrapy_new.pipelines.NewsPipeline': 300,
}

# ========================================
# Redis 配置（全局共享）
# ========================================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 1

CHANNELS = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']