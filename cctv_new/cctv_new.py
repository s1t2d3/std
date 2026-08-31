# cctv_news_crawler.py
import os
import json
import re
import asyncio
import aiohttp
import redis
from typing import List, Dict, Optional, Set
from datetime import datetime

import nest_asyncio

from utils.path_tool import get_abs_path

nest_asyncio.apply()

# ========================================
# 配置
# ========================================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 1
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2
PAGE_SIZE = 1

CHANNELS = ['news', 'china', 'world', 'society', 'law', 'ent', 'tech', 'life', 'edu']

# ========================================
# ⭐ 数据目录（项目根目录下的 data/）
# ========================================
FILE_DIR = "data/news"

# ========================================
# Redis 连接
# ========================================
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# ========================================
# 请求头
# ========================================
cookies = {
    'cna': 'iPXsIv/e30ICAXs1fPIQXk11',
    'HMF_CI': 'ee87bd7344039c8d265eca6c8a88ab3e6f8502e7fde49d6dff935f585c00e43946b905054021ec526198c23cb199c29466750973f7f3ccf0fc603eebb6957aa495',
    'sca': '94dd4c40',
    'HMY_JC': '7f72a18db48d17ea3be1c4f50ec39138ff76ee82a3d649da6431c2589ab54cd0d1,',
    'HBB_HC': '7944b375fb08396d8b2758583d7d106e41004248999c56618ff5f69a3269055681ca0373dba19164283dd590babc17b6e1',
    'atpsida': '9185062880b51ec5a830a34b_1787530164_5',
}

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Referer': 'https://cn.bing.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0',
    'sec-ch-ua': '"Not=A?Brand";v="99", "Microsoft Edge";v="151", "Chromium";v="151"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


# ========================================
# JSON 存储函数
# ========================================
def get_json_path(channel: str, date: str = None) -> str:
    """获取 JSON 文件路径"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    # 用 get_abs_path 获取完整目录路径，然后拼接文件名
    dir_path = get_abs_path(FILE_DIR)
    return os.path.join(dir_path, f"cctv_{channel}_{date}.json")


def save_to_json(channel: str, news_list: List[Dict]):
    """保存到 JSON 文件（增量合并）"""
    # 用 get_abs_path 获取完整目录路径
    dir_path = get_abs_path(FILE_DIR)
    # 确保目录存在
    os.makedirs(dir_path, exist_ok=True)

    # 生成文件名和完整路径
    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"cctv_{channel}_{date}.json"
    file_path = os.path.join(dir_path, filename)

    # 如果文件存在，合并去重
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing_titles = {n.get("标题") for n in existing}
            for news in news_list:
                if news.get("标题") not in existing_titles:
                    existing.append(news)
            news_list = existing
        except:
            pass

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print(f"  💾 JSON: {file_path} ({len(news_list)} 条)")


def load_from_json(channel: str = None, date: str = None) -> List[Dict]:
    """从 JSON 加载新闻"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    dir_path = get_abs_path(FILE_DIR)
    all_news = []

    if channel:
        file_path = get_json_path(channel, date)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                all_news = json.load(f)
    else:
        # 加载所有频道的新闻
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if date in filename and filename.endswith('.json'):
                    file_path = os.path.join(dir_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        all_news.extend(json.load(f))

    return all_news


def load_all_news() -> List[Dict]:
    """加载所有新闻（所有日期）"""
    dir_path = get_abs_path(FILE_DIR)
    all_news = []

    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            if filename.endswith('.json'):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_news.extend(json.load(f))
    return all_news


# ========================================
# 解析函数
# ========================================
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


# ========================================
# 异步爬虫
# ========================================
async def fetch_page_async(
        session: aiohttp.ClientSession,
        channel: str,
        page: int,
        seen_titles: Set[str],
        semaphore: asyncio.Semaphore,
        max_items_per_page: int = 20
) -> List[dict]:
    url = f"https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/{channel}_{page}.jsonp"
    params = {'cb': channel}

    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:
                async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        print(f"  ⚠️ [{channel}] 第{page}页 状态码: {response.status}")
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        continue

                    text = await response.text(encoding='utf-8')
                    data = parse_jsonp(text)

                    if data is None:
                        print(f"  ⚠️ [{channel}] 第{page}页 解析失败")
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        continue

                    news_list = get_detail_data(data)
                    new_items = []
                    for item in news_list:
                        title = item.get("标题", "").strip()
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            new_items.append(item)
                            if len(new_items) >= max_items_per_page:
                                break

                    print(f"  ✅ [{channel}] 第{page}页: 新增 {len(new_items)} 条")
                    return new_items

        except asyncio.TimeoutError:
            print(f"  ⚠️ [{channel}] 第{page}页 超时")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f"  ⚠️ [{channel}] 第{page}页 错误: {e}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return []


async def process_channel_async(
        session: aiohttp.ClientSession,
        channel: str,
        semaphore: asyncio.Semaphore
) -> Dict:
    print(f"\n📰 正在获取 [{channel}] 数据...")

    seen_titles = set()
    channel_news = []

    try:
        tasks = [
            fetch_page_async(session, channel, page, seen_titles, semaphore, max_items_per_page=20)
            for page in range(1, PAGE_SIZE + 1)
        ]

        pages_result = await asyncio.gather(*tasks, return_exceptions=True)

        for result in pages_result:
            if isinstance(result, list):
                channel_news.extend(result)

        # 添加频道信息
        for news in channel_news:
            news["频道"] = channel

        # 保存到 Redis
        redis_key = f"news:cctv:{channel}"
        redis_client.set(redis_key, json.dumps(channel_news, ensure_ascii=False))
        print(f"  ✅ Redis: {channel} -> {len(channel_news)} 条")

        # 保存到 JSON
        save_to_json(channel, channel_news)

        return {
            'channel': channel,
            'count': len(channel_news),
            'status': 'success'
        }

    except Exception as e:
        print(f"  ❌ {channel} 失败: {e}")
        return {
            'channel': channel,
            'count': 0,
            'status': 'failed',
            'error': str(e)
        }


async def get_all_news_async(max_concurrent: int = 10):
    print("=" * 60)
    print(f"🚀 开始爬取央视新闻，共 {len(CHANNELS)} 个频道")
    print("=" * 60)

    # 显示实际保存路径
    dir_path = get_abs_path(FILE_DIR)
    print(f"📁 数据保存到: {dir_path}\n")

    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent * 2)

    async with aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    ) as session:

        tasks = [process_channel_async(session, channel, semaphore) for channel in CHANNELS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计
    print("\n" + "=" * 60)
    print("📊 爬取完成:")
    total = 0
    for r in results:
        if isinstance(r, dict) and r['status'] == 'success':
            print(f"  ✅ {r['channel']}: {r['count']} 条")
            total += r['count']
        else:
            print(f"  ❌ {r}: 失败")
    print(f"📈 总计: {total} 条")
    print("=" * 60)
    return results


# ========================================
# 入口函数
# ========================================
def get_all_news():
    """同步入口"""
    return asyncio.run(get_all_news_async(max_concurrent=10))


# ========================================
# 统计
# ========================================
def show_stats():
    """查看统计数据"""
    print("\n📊 数据统计:")
    print("-" * 40)

    # Redis
    keys = redis_client.keys('news:cctv:*')
    redis_total = 0
    for key in keys:
        data = redis_client.get(key)
        if data:
            news_list = json.loads(data)
            redis_total += len(news_list)
            channel = key.replace("news:cctv:", "")
            print(f"  Redis {channel}: {len(news_list)} 条")
    print(f"  Redis 总计: {redis_total} 条")

    # JSON
    print()
    dir_path = get_abs_path(FILE_DIR)
    json_total = 0
    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            if filename.endswith('.json'):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    news_list = json.load(f)
                    json_total += len(news_list)
                    channel = filename.replace("cctv_", "").replace(".json", "")
                    print(f"  JSON {channel}: {len(news_list)} 条")
    print(f"  JSON 总计: {json_total} 条")
    print("-" * 40)


# ========================================
# 主程序
# ========================================
if __name__ == '__main__':
    try:
        redis_client.ping()
        print("✅ Redis 连接成功\n")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        exit(1)

    get_all_news()
    # show_stats()