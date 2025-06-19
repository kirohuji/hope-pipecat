#!/usr/bin/env python3
"""
测试 /connect 端点
"""

import requests
import json

def test_connect_endpoint():
    # 服务器 URL
    base_url = "http://localhost:7860"
    
    # 测试参数
    test_params = {
        "conversation_id": "test_conversation_123",
        "actions": [],
        "bot_profile": "vision",
        "attachments": []
    }
    
    print(f"Testing /connect endpoint with params: {test_params}")
    
    try:
        # 发送 POST 请求到 /connect 端点
        response = requests.post(
            f"{base_url}/bot/connect",
            json=test_params,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Response data: {response_data}")
            
            # 检查是否返回了 ws_url
            if "ws_url" in response_data:
                ws_url = response_data["ws_url"]
                print(f"WebSocket URL: {ws_url}")
                
                # 解析 URL 中的参数
                if "params=" in ws_url:
                    params_part = ws_url.split("params=")[1]
                    decoded_params = urllib.parse.unquote(params_part)
                    parsed_params = json.loads(decoded_params)
                    print(f"Decoded params: {parsed_params}")
                    
                    # 验证参数是否正确
                    if parsed_params == test_params:
                        print("✅ Parameters correctly encoded and decoded!")
                    else:
                        print("❌ Parameters mismatch!")
                else:
                    print("❌ No params found in WebSocket URL")
            else:
                print("❌ No ws_url in response")
        else:
            print(f"❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    import urllib.parse
    test_connect_endpoint() 