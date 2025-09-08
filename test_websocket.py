import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    print("Testing WebSocket connection...")
    print("="*50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            print("Waiting for real-time updates...")
            
            # Listen for 3 messages
            for i in range(3):
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                
                print(f"\n📡 Update #{i+1} received at {time.strftime('%H:%M:%S')}:")
                
                if 'price' in data:
                    print(f"   BTC Price: ${data['price']:,.0f}")
                if 'market_state' in data:
                    print(f"   Market State: {data['market_state']}")
                if 'fear_greed' in data:
                    print(f"   Fear & Greed: {data['fear_greed']}")
                if 'volume_24h' in data:
                    print(f"   Volume 24h: ${data['volume_24h']/1e9:.2f}B")
                    
            print("\n✅ WebSocket real-time updates working!")
            
    except asyncio.TimeoutError:
        print("⏱️ Timeout - no updates received in 10 seconds")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

asyncio.run(test_websocket())
