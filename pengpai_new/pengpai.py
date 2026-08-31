# pengpai_news_crawler.py
import os
import json
import time
import random
import requests
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime

from utils.path_tool import get_abs_path

# ========================================
# 配置
# ========================================
FILE_DIR = "data/news"
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 1

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

cookies = {
    '_c_WBKFRo': 'bAXPhJB1QGeO7nsWA4rEscPL2SJyMrGF39CyBzDg',
    'Hm_lvt_94a1e06bbce219d29285cee2e37d1d26': '1786165724,1786688887,1786755543',
    'HMACCOUNT': '62BD216B7B90239C',
    'Hm_lpvt_94a1e06bbce219d29285cee2e37d1d26': '1786755791',
    'ariaDefaultTheme': 'undefined',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'client-type': '1',
    'content-type': 'application/json',
    'origin': 'https://www.thepaper.cn',
    'priority': 'u=1, i',
    'referer': 'https://www.thepaper.cn/',
    'sec-ch-ua': '"Not=A?Brand";v="99", "Microsoft Edge";v="151", "Chromium";v="151"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0',
}


# ========================================
# JSON 存储函数（与央视新闻格式完全一致）
# ========================================
def get_json_path(channel: str, date: str = None) -> str:
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    dir_path = get_abs_path(FILE_DIR)
    return os.path.join(dir_path, f"pengpai_{channel}_{date}.json")


def save_to_json(channel: str, news_list: list):
    """保存到 JSON 文件（格式与央视新闻完全一致）"""
    dir_path = get_abs_path(FILE_DIR)
    os.makedirs(dir_path, exist_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"pengpai_{channel}_{date}.json"
    file_path = os.path.join(dir_path, filename)

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


def load_from_json(channel: str = None) -> list:
    """从 JSON 加载新闻"""
    dir_path = get_abs_path(FILE_DIR)
    all_news = []

    if not os.path.exists(dir_path):
        return all_news

    if channel:
        for filename in os.listdir(dir_path):
            if filename.startswith(f"pengpai_{channel}_") and filename.endswith('.json'):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_news.extend(json.load(f))
    else:
        for filename in os.listdir(dir_path):
            if filename.startswith('pengpai_') and filename.endswith('.json'):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_news.extend(json.load(f))

    return all_news


def load_all_news() -> list:
    """加载所有新闻"""
    dir_path = get_abs_path(FILE_DIR)
    all_news = []

    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            if filename.startswith('pengpai_') and filename.endswith('.json'):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_news.extend(json.load(f))
    return all_news


# ========================================
# 获取频道列表
# ========================================
def get_channel_list():
    channel_list = []
    try:
        response = requests.get('https://cache.thepaper.cn/contentapi/node/getWwwAllNodes',
                                cookies=cookies, headers=headers, timeout=10)
        data = response.json()
        all_channels = data['data']["channelList"]

        # 安全切片，从索引1开始（跳过首页），最多取11个
        for channel in all_channels[1:12]:
            channel_id = channel["nodeId"]
            channel_name = channel["name"]
            channel_list.append({
                "name": channel_name,
                "channel_id": channel_id
            })
    except Exception as e:
        print(f"获取频道列表失败: {e}")
        return []

    return channel_list


# ========================================
# 提取标签
# ========================================
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


# ========================================
# 获取详情数据 - 直接返回统一格式
# ========================================
def get_detail_data(data, page, seen, channel):
    """解析数据，直接返回与央视新闻格式一致的列表"""
    all_list = []
    start_time = int(time.time() * 1000)

    # 置顶内容
    top_content = data.get("data", {}).get("topContent")
    if top_content:
        cont_id = top_content.get("contId")
        if cont_id and cont_id not in seen:
            seen.add(cont_id)
            # 提取标签（注意：topContent 中可能是 tagList）
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
        if cont_id and cont_id not in seen:
            seen.add(cont_id)

            # 提取标签
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


# ========================================
# 获取多页数据
# ========================================
def get_page_data(channel_type, channel_id):
    """爬取单个频道数据"""
    all_news = []
    seen = set()
    start_time = int(time.time() * 1000)

    if channel_type == "精选":
        url = "https://api.thepaper.cn/contentapi/channel/depth"
    else:
        url = "https://api.thepaper.cn/contentapi/nodeCont/getByChannelId"

    for page in range(1, 2):
        json_data = {
            "channelId": channel_id,
            'pageSize': 20,
            'cardMode': 152,
            'startTime': str(start_time),
            'pageNum': page,
        }

        try:
            response = requests.post(url, cookies=cookies, headers=headers, json=json_data, timeout=10)
            data = response.json()
        except Exception as e:
            print(f"第{page}页请求失败: {e}")
            break

        page_list, start_time = get_detail_data(data, page, seen, channel_type)
        all_news.extend(page_list)

        # 检查是否有下一页
        if url == "https://api.thepaper.cn/contentapi/channel/depth":
            has_next = data.get("data", {}).get("pageInfo", {}).get("hasNext", False)
        else:
            has_next = data.get("data", {}).get("hasNext", False)

        if not has_next and page > 1:
            print("没有下一页了，停止")
            break

        time.sleep(random.uniform(1, 2))

    # 注意：不需要再补全频道信息，get_detail_data 中已经设置了

    # 保存到 Redis
    redis_key = f"news:pengpai:{channel_type}"
    redis_client.set(redis_key, json.dumps(all_news, ensure_ascii=False))
    print(f"  ✅ Redis: {channel_type} -> {len(all_news)} 条")

    # 保存到 JSON
    save_to_json(channel_type, all_news)

    print(f"  ✅ {channel_type}类: 共 {len(all_news)} 条数据")
    return all_news


# ========================================
# 多线程处理
# ========================================
print_lock = threading.Lock()


def safe_print(msg):
    with print_lock:
        print(msg)


def process_one_channel(channel):
    skip_channels = {"播客", "视频", "直播", "短剧"}

    if channel['name'] in skip_channels:
        return None

    safe_print(f"\n📰 正在获取 [{channel['name']}] 数据...")

    try:
        result = get_page_data(channel['name'], channel['channel_id'])
        return result
    except Exception as e:
        safe_print(f"  ❌ {channel['name']} 失败: {e}")
        return None


def get_pengpai_news():
    channels = get_channel_list()

    if not channels:
        print("❌ 未获取到任何频道，请检查网络或接口")
        return []

    print("=" * 60)
    print(f"🚀 开始爬取澎湃新闻，共 {len(channels)} 个频道")
    print("=" * 60)

    dir_path = get_abs_path(FILE_DIR)
    print(f"📁 数据保存到: {dir_path}\n")

    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_channel = {
            executor.submit(process_one_channel, channel): channel
            for channel in channels
        }

        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                result = future.result(timeout=120)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ❌ {channel['name']} 处理失败: {e}")

    print("\n" + "=" * 60)
    print(f"📊 爬取完成，成功 {len(results)} 个频道")
    print("=" * 60)
    return results


# # ========================================
# # 统计
# # ========================================
# def show_stats():
#     print("\n📊 数据统计:")
#     print("-" * 40)
#
#     keys = redis_client.keys('news:pengpai:*')
#     redis_total = 0
#     for key in keys:
#         data = redis_client.get(key)
#         if data:
#             news_list = json.loads(data)
#             redis_total += len(news_list)
#             channel = key.replace("news:pengpai:", "")
#             print(f"  Redis {channel}: {len(news_list)} 条")
#     print(f"  Redis 总计: {redis_total} 条")
#
#     print()
#     dir_path = get_abs_path(FILE_DIR)
#     json_total = 0
#     if os.path.exists(dir_path):
#         for filename in os.listdir(dir_path):
#             if filename.startswith('pengpai_') and filename.endswith('.json'):
#                 file_path = os.path.join(dir_path, filename)
#                 with open(file_path, 'r', encoding='utf-8') as f:
#                     news_list = json.load(f)
#                     json_total += len(news_list)
#                     parts = filename.replace("pengpai_", "").split('_')
#                     channel = '_'.join(parts[:-1]) if len(parts) >= 2 else parts[0]
#                     print(f"  JSON {channel}: {len(news_list)} 条")
#     print(f"  JSON 总计: {json_total} 条")
#     print("-" * 40)


# ========================================
# 主程序
# ========================================
if __name__ == "__main__":
    try:
        redis_client.ping()
        print("✅ Redis 连接成功\n")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        exit(1)

    get_pengpai_news()
    # show_stats()