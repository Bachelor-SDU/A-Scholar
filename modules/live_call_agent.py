# modules/live_call_agent.py
import streamlit as st
import threading
import queue
import asyncio
import websockets
import json
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from utils.logger import logger


# ==========================================
# 1. 前端 UI：纯 CSS 实现的会呼吸的发光球
# ==========================================
def render_breathing_sphere():
    css = """
    <style>
    .sphere-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 300px;
    }
    .glowing-sphere {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #4facfe, #00f2fe);
        box-shadow: 0 0 20px #00f2fe, 0 0 40px #00f2fe, 0 0 80px #4facfe;
        animation: breathe 3s infinite ease-in-out;
    }
    @keyframes breathe {
        0% { transform: scale(0.95); box-shadow: 0 0 20px #00f2fe; opacity: 0.8; }
        50% { transform: scale(1.1); box-shadow: 0 0 50px #00f2fe, 0 0 100px #4facfe; opacity: 1; }
        100% { transform: scale(0.95); box-shadow: 0 0 20px #00f2fe; opacity: 0.8; }
    }
    </style>
    <div class="sphere-container">
        <div class="glowing-sphere"></div>
    </div>
    """
    st.markdown(css, unsafe_allow_html=True)


# ==========================================
# 2. 数据桥梁：用于在 WebRTC 和 WebSocket 间传递音频帧
# ==========================================
audio_input_queue = queue.Queue()  # 存入用户麦克风的声音
audio_output_queue = queue.Queue()  # 存入大模型返回的声音


# ==========================================
# 3. WebRTC 音频处理器 (运行在 Streamlit 独立线程)
# ==========================================
class RealtimeAudioProcessor(AudioProcessorBase):
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # 1. 拿到用户麦克风的 PCM 音频数据，丢给大模型处理队列
        pcm_data = frame.to_ndarray()
        audio_input_queue.put(pcm_data)

        # 2. 检查大模型有没有传回来的声音
        if not audio_output_queue.empty():
            ai_pcm_data = audio_output_queue.get_nowait()
            # 用大模型的声音替换当前帧，播放给用户听
            new_frame = av.AudioFrame.from_ndarray(ai_pcm_data, format=frame.format.name)
            new_frame.sample_rate = frame.sample_rate
            new_frame.layout = frame.layout
            return new_frame

        # 如果 AI 没说话，就返回静音帧 (避免回音)
        empty_data = np.zeros_like(pcm_data)
        empty_frame = av.AudioFrame.from_ndarray(empty_data, format=frame.format.name)
        empty_frame.sample_rate = frame.sample_rate
        empty_frame.layout = frame.layout
        return empty_frame


# ==========================================
# 4. 后台长连接：与大模型的 Realtime API 通信
# ==========================================
async def llm_websocket_client():
    """这是一个标准的与支持端到端语音大模型(如 OpenAI Realtime API) 通信的模板"""
    # 替换为您真实使用的 Realtime API 地址和 Key
    uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
    headers = {
        "Authorization": f"Bearer {st.secrets.get('REALTIME_API_KEY', '')}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        # 如果没有配置 API Key，就进入模拟测试模式 (避免报错崩溃)
        if not st.secrets.get('REALTIME_API_KEY'):
            logger.warning("未配置 REALTIME_API_KEY，进入音频队列测试模式。")
            while True:
                await asyncio.sleep(0.1)
                if not audio_input_queue.empty():
                    audio_input_queue.get()  # 消耗掉不处理
            return

        async with websockets.connect(uri, extra_headers=headers) as websocket:
            logger.info("✅ 成功连接到 Realtime 语音大模型！")

            async def send_audio():
                """持续将麦克风队列的声音发给 AI"""
                while True:
                    if not audio_input_queue.empty():
                        pcm_data = audio_input_queue.get_nowait()
                        # 需要根据各家 API 文档，将 pcm_data 转为 base64 发送
                        # 示例伪代码:
                        # base64_audio = base64.b64encode(pcm_data.tobytes()).decode("utf-8")
                        # await websocket.send(json.dumps({"type": "input_audio_buffer.append", "audio": base64_audio}))
                    await asyncio.sleep(0.01)

            async def receive_audio():
                """持续接收 AI 发来的声音并塞给播放队列"""
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    if data.get("type") == "response.audio.delta":
                        # 将收到的 base64 音频解压为 numpy array 放入 audio_output_queue
                        pass

            # 并发运行收和发
            await asyncio.gather(send_audio(), receive_audio())

    except Exception as e:
        logger.exception(f"WebSocket 连线断开: {e}")


def start_websocket_thread():
    """将 asyncio 循环放到独立线程中运行，防止阻塞 Streamlit"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(llm_websocket_client())


# ==========================================
# 5. 模块主入口渲染
# ==========================================
def render_live_call_module():
    st.header("📞 零延迟实境通话 (Live Call)")
    st.caption("采用端到端实时大模型技术，支持随时打断与全双工自由对谈。")
    st.divider()

    col_ui, col_ctrl = st.columns([2, 1])

    with col_ui:
        st.subheader("AI 导师 - A-Scholar")
        # 渲染科幻的呼吸灯球
        render_breathing_sphere()

    with col_ctrl:
        st.write("### 连线控制面板")
        st.info("点击下方 START 开始通话，请允许浏览器使用麦克风。通话过程中直接讲话即可，AI 说话时你也可以随时插嘴打断。")

        # WebRTC 麦克风接管组件
        webrtc_ctx = webrtc_streamer(
            key="realtime_voice_call",
            mode=WebRtcMode.SENDRECV,  # 开启发送(麦克风)和接收(扬声器)
            audio_processor_factory=RealtimeAudioProcessor,
            media_stream_constraints={
                "video": False,  # 我们只要语音，不要视频画面
                "audio": {
                    "echoCancellation": True,  # 必须开启回声消除
                    "noiseSuppression": True,  # 开启降噪
                    "autoGainControl": True
                }
            },
            async_processing=True  # 开启异步处理提升性能
        )

        if webrtc_ctx.state.playing:
            st.success("🟢 连线已接通，正在聆听...")

            # 开启后台大模型 WebSocket 通信线程 (防止重复开启)
            if "ws_thread_started" not in st.session_state:
                st.session_state.ws_thread_started = True
                threading.Thread(target=start_websocket_thread, daemon=True).start()

        else:
            st.warning("🔴 连线已挂断")
            st.session_state.ws_thread_started = False