import scrapy


class NewsItem(scrapy.Item):
    """统一新闻 Item, 字段名与 pipeline、已有 JSON 数据、澎湃爬虫保持一致"""
    标题 = scrapy.Field()
    简介 = scrapy.Field()
    关键词 = scrapy.Field()
    发布时间 = scrapy.Field()
    详情链接 = scrapy.Field()
    频道 = scrapy.Field()
    来源 = scrapy.Field()
