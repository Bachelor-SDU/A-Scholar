# utils/dict_api.py
import requests
import hashlib
import time
import uuid
import streamlit as st
from utils.logger import logger  # 引入我们之前写好的 loguru 日志


def encrypt_youdao_sign(app_key, app_secret, q, salt, curtime):
    """生成有道API所需的签名"""

    def truncate(q):
        if q is None: return None
        size = len(q)
        return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]

    sign_str = app_key + truncate(q) + salt + curtime + app_secret
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(sign_str.encode('utf-8'))
    return hash_algorithm.hexdigest()


def lookup_word_youdao(word):
    """
    调用有道词典 API 查词
    返回标准化字典，如果查询失败返回 None
    """
    app_key = st.secrets.get("YOUDAO_APP_KEY")
    app_secret = st.secrets.get("YOUDAO_APP_SECRET")

    if not app_key or not app_secret:
        logger.error("未配置有道词典 API Key！")
        return None

    # 请求参数构造
    q = word.strip()
    salt = str(uuid.uuid1())
    curtime = str(int(time.time()))
    sign = encrypt_youdao_sign(app_key, app_secret, q, salt, curtime)

    params = {
        'q': q,
        'from': 'en',
        'to': 'zh-CHS',
        'appKey': app_key,
        'salt': salt,
        'sign': sign,
        'signType': 'v3',
        'curtime': curtime,
    }

    try:
        response = requests.get('https://openapi.youdao.com/api', params=params, timeout=5)
        res_json = response.json()

        # 错误码判断 (0 代表成功)
        if res_json.get("errorCode") != "0":
            logger.warning(f"有道API返回错误码: {res_json.get('errorCode')}")
            return None

        # --- 核心：解析返回的数据，重构为前端好用的格式 ---
        # 基础翻译
        translation = res_json.get("translation", [])

        # 词典扩展数据 (包含音标、发音等)
        basic = res_json.get("basic", {})

        parsed_data = {
            "word": q,
            "translation": translation,
            "uk_phonetic": basic.get("uk-phonetic", ""),
            "us_phonetic": basic.get("us-phonetic", ""),
            # 发音 MP3 链接
            "uk_speech": basic.get("uk-speech", ""),
            "us_speech": basic.get("us-speech", ""),
            # 详细释义
            "explains": basic.get("explains", []),
            # 词汇级别标签 (如: 考研, CET4)
            "exam_type": basic.get("exam_type", [])
        }

        return parsed_data

    except Exception as e:
        logger.exception(f"查词接口调用异常: {e}")
        return None