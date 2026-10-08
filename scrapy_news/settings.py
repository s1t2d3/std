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

# 启用自动限速（推荐）
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

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


# SPIDER_MIDDLEWARES = {
#     'scrapy_news.middlewares.ScrapyNewsSpiderMiddleware': 543,
# }

# ========================================
# scrapy-redis 分布式配置（共享调度队列模式）
# 所有节点必须指向同一个 Redis 实例，统一使用 db3
# ========================================
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.PriorityQueue"

# 分布式关键项：启动时不清空 Redis 队列/去重集合，
# 否则先启动的节点会把其他节点正在跑的任务清掉
SCHEDULER_FLUSH_ON_START = False
# 爬虫结束时不保留队列，避免去重集合无限累积（定时全量爬取场景）
SCHEDULER_PERSIST = False

# 统一 Redis 连接（调度队列 + 去重集合，与 celery 的 db0 隔离）
REDIS_URL = "redis://127.0.0.1:6379/3"
# ========================================
# Pipeline
# ========================================
ITEM_PIPELINES = {
    'scrapy_news.pipelines.NewsPipeline': 300,
}

CHANNELS = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']

# ========================================
# ✅ 强制使用默认爬虫加载器（修复 DummySpiderLoader）
# ========================================
SPIDER_LOADER_CLASS = 'scrapy.spiderloader.SpiderLoader'