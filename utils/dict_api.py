# utils/dict_api.py

import random
import time
from functools import lru_cache

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import logger


# ==========================================
# Session 全局复用
# ==========================================

session = requests.Session()

retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("https://", adapter)
session.mount("http://", adapter)


# ==========================================
# 请求头池（防反爬）
# ==========================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://dict.youdao.com/",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


# ==========================================
# 工具函数
# ==========================================

def safe_get(d, *keys, default=None):
    """
    安全获取嵌套字典字段
    """
    for key in keys:
        try:
            d = d[key]
        except (KeyError, IndexError, TypeError):
            return default
    return d


# ==========================================
# 解析释义
# ==========================================

def parse_explains(word_info):
    explains = []

    trs = word_info.get("trs", [])

    for tr in trs:
        try:
            text = tr["tr"][0]["l"]["i"][0]
            explains.append(text)
        except Exception:
            continue

    return explains


# ==========================================
# 解析例句
# ==========================================

def parse_sentences(data):
    result = []

    sentence_data = (
        data.get("blng_sents_part", {})
        .get("sentence-pair", [])
    )

    for item in sentence_data[:5]:
        result.append({
            "en": item.get("sentence", ""),
            "zh": item.get("sentence-translation", "")
        })

    return result


# ==========================================
# 解析短语
# ==========================================

def parse_phrases(data):
    phrases = []

    phrase_data = (
        data.get("phrase", {})
        .get("phrases", [])
    )

    for item in phrase_data[:10]:
        phrases.append({
            "phrase": item.get("p", ""),
            "translation": item.get("t", "")
        })

    return phrases


# ==========================================
# 主查词函数
# ==========================================

@lru_cache(maxsize=2048)
def lookup_word_youdao(word: str):
    """
    有道词典网页版接口
    """

    if not word:
        return None

    word = word.strip()

    url = "https://dict.youdao.com/jsonapi"

    params = {
        "q": word
    }

    try:
        # ==================================
        # 随机延迟（防频繁）
        # ==================================
        time.sleep(random.uniform(0.1, 0.4))

        response = session.get(
            url,
            params=params,
            headers=get_headers(),
            timeout=(5, 10)
        )

        response.raise_for_status()

        data = response.json()

        # ==================================
        # 英汉词典主数据
        # ==================================
        word_info = safe_get(
            data,
            "ec",
            "word",
            0,
            default={}
        )

        if not word_info:
            logger.warning(f"未找到单词: {word}")
            return None

        explains = parse_explains(word_info)

        result = {
            # 基础
            "word": word,

            # 音标
            "uk_phonetic":
                word_info.get("ukphone", ""),

            "us_phonetic":
                word_info.get("usphone", ""),

            # 发音
            "uk_speech":
                f"https://dict.youdao.com/dictvoice?audio={word}&type=1",

            "us_speech":
                f"https://dict.youdao.com/dictvoice?audio={word}&type=2",

            # 释义
            "translation": explains,
            "explains": explains,

            # 等级
            "exam_type":
                word_info.get("exam_type", []),

            # 例句
            "sentences":
                parse_sentences(data),

            # 短语
            "phrases":
                parse_phrases(data),
        }

        return result

    except requests.exceptions.Timeout:
        logger.warning(f"查词超时: {word}")
        return None

    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP错误: {e}")
        return None

    except Exception as e:
        logger.exception(f"查词失败: {e}")
        return None