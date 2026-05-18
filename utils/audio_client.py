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
from pydub import AudioSegment

from utils.logger import *


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
STT_MODEL = st.secrets["STT_MODEL"]
TTS_MODEL = st.secrets["TTS_MODEL"]


# ---------------------------------------------------------
# 1. STT
# ---------------------------------------------------------
def transcribe_audio(audio_bytes):
    """Speech-to-Text"""
    if not audio_bytes:
        return None
    temp_path = None
    try:
        # 先读取浏览器录音
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        # 转成阿里云需要的格式
        audio = (
            audio
            .set_frame_rate(16000)
            .set_channels(1)
            .set_sample_width(2)
        )
        # 保存为真正标准 wav
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            audio.export(f.name, format="wav")
            temp_path = f.name

        recognition = Recognition(model=STT_MODEL, format='wav', sample_rate=16000, language_hints=['zh', 'en'], callback=None)
        result = recognition.call(temp_path)

        if result.status_code == HTTPStatus.OK:
            # logger.info(result)
            # logger.info(result.output)
            output = result.output or {}
            sentences = output.get("sentence", [])
            text_parts = []
            for s in sentences:
                txt = s.get("text", "").strip()
                if txt:
                    text_parts.append(txt)
            final_text = " ".join(text_parts).strip()
            logger.info(f"ASR final result: {final_text}")
            return final_text if final_text else None

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------
# 2. TTS
# ---------------------------------------------------------
# 设置 API Key
class TTSCallback(QwenTtsRealtimeCallback):
    def __init__(self):
        self.audio_data = bytearray()
        self.complete_event = threading.Event()

    def on_event(self, response: dict) -> None:
        try:
            msg_type = response.get('type')
            # logger.info(response)
            if 'response.audio.delta' == msg_type:
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
        model=TTS_MODEL,
        callback=callback
    )
    try:
        # Websocket connect
        tts_realtime.connect()
        tts_realtime.update_session(
            voice=voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='server_commit'
        )
        tts_realtime.append_text(text)
        tts_realtime.finish()
        callback.wait_for_finished()
        # logger.success("✅ 实时语音合成完成，正在转换格式...")
        return pcm_to_wav(bytes(callback.audio_data))

    except Exception as e:
        logger.exception(f"❌ 实时语音合成失败: {e}")
        return None