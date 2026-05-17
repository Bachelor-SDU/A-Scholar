# utils/audio_client.py
import tempfile
import os
import io
import sys
import asyncio
import base64
import threading
from http import HTTPStatus

import dashscope
from dashscope.audio.qwen_tts_realtime import *
from dashscope.audio.asr import Recognition
import streamlit as st
from openai import OpenAI
from pydub import AudioSegment

from utils.logger import *


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]


# ---------------------------------------------------------
# 1. STT: 语音转文字 (Agent 听你说)
# ---------------------------------------------------------
def transcribe_audio(audio_bytes):
    """
    使用阿里云 Paraformer
    """

    if not audio_bytes:
        return None

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as f:
            f.write(audio_bytes)
            temp_path = f.name

        recognition = Recognition(model='paraformer-realtime-v2',
                                  format='wav',
                                  sample_rate=16000,
                                  # “language_hints”只支持paraformer-realtime-v2模型
                                  language_hints=['zh', 'en'],
                                  callback=None)

        result = recognition.call(temp_path)

        if result.status_code == HTTPStatus.OK:
            return result.get_sentence()

        logger.warning("ASR Error:", result.message)
        return None

    except Exception as e:
        logger.exception(f"阿里ASR失败: {e}")
        return None

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------
# 2. TTS: 文字转语音 (Agent 回复你)
# ---------------------------------------------------------
# 设置 API Key
class TTSCallback(QwenTtsRealtimeCallback):
    def __init__(self):
        self.audio_data = bytearray()
        self.complete_event = threading.Event()

    def on_event(self, response: str) -> None:
        try:
            msg_type = response.get('type')
            if 'response.audio.delta' == msg_type:
                # 累加收到的流式音频块
                self.audio_data.extend(base64.b64decode(response['delta']))
            elif 'session.finished' == msg_type:
                self.complete_event.set()
        except Exception as e:
            logger.error(f"TTS 流式处理异常: {e}")

    def wait_for_finished(self):
        self.complete_event.wait(timeout=10)  # 加上超时保护


def pcm_to_wav(pcm_data):
    """将 PCM 转为 WAV 字节流供 st.audio 使用"""
    audio = AudioSegment(
        pcm_data,
        frame_rate=24000,
        sample_width=2,
        channels=1
    )
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    return wav_io.getvalue()


def generate_audio_reply(text, voice="Cherry"):
    """
    模块化接口：封装阿里实时TTS
    """
    callback = TTSCallback()

    # 初始化实时连接
    tts_realtime = QwenTtsRealtime(
        model='qwen3-tts-instruct-flash-realtime',
        callback=callback
    )

    try:
        tts_realtime.connect()
        tts_realtime.update_session(
            voice=voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='server_commit'
        )

        # 发送文本
        tts_realtime.append_text(text)
        tts_realtime.finish()

        # 等待完成
        callback.wait_for_finished()
        logger.success("✅ 实时语音合成完成，正在转换格式...")
        # 此时 callback.audio_data 包含了完整的 PCM 数据
        # 注意：这里返回的是 PCM，如果浏览器无法播放，可能需要转换成 WAV 或 MP3
        return pcm_to_wav(bytes(callback.audio_data))

    except Exception as e:
        logger.exception(f"❌ 实时语音合成失败: {e}")
        return None