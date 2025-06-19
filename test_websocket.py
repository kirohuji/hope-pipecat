#!/usr/bin/env python3
"""
测试 WebSocket 连接和参数传递功能
"""

import asyncio
import json
import urllib.parse
import websockets

async def test_websocket_connection():
    # 模拟 BotParams
    bot_params = {
        "conversation_id": "test_conversation_123",
        "actions": [],
        "bot_profile": "vision",
        "attachments": []
    }
    
    # 编码参数
    params_json = json.dumps(bot_params)
    encoded_params = urllib.parse.quote(params_json)
    
    # WebSocket URL
    ws_url = f"ws://localhost:7860/bot/ws?params={encoded_params}"
    
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("WebSocket connected successfully!")
            
            # 发送测试消息
            test_message = {"type": "test", "content": "Hello from client"}
            await websocket.send(json.dumps(test_message))
            print(f"Sent message: {test_message}")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received response: {response}")
            except asyncio.TimeoutError:
                print("No response received within 5 seconds")
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection()) 