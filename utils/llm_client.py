# utils/llm_client.py
import streamlit as st
from openai import OpenAI
import json
import re
import time
from utils.logger import *

client = OpenAI(
    api_key=st.secrets["API_KEY"],
    base_url=st.secrets["BASE_URL"]
)
MODEL = st.secrets["MODEL_NAME"]


@log_execution_time
def get_llm_response(messages, json_mode=False):
    # 记录请求概况 (不要把巨大的 history 都打出来，打最后一条或者长度即可)
    last_msg = messages[-1]["content"] if messages else "Empty"
    logger.info(f"LLM Request [{MODEL}] | json_mode={json_mode} | Last Msg: {last_msg[:50]}...")

    try:
        kwargs = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7
        }
        if json_mode:
            # 强制模型输出JSON
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        logger.debug(f"LLM Raw Content: {content}")

        if json_mode:
            content = re.sub(r"```json\n|\n```|```", "", content).strip()
            try:
                parsed_json = json.loads(content)
                return parsed_json
            except json.JSONDecodeError as je:
                logger.exception(f"JSON Decode Error! Raw string: {content} | Error: {je}")
                return None
        return content
    except Exception as e:
        logger.exception(f"LLM API Call Failed! Reason: {str(e)}")
        return None
