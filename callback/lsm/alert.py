import os
from discordwebhook import Discord
from datetime import datetime, timezone

ALERT_DISABLE = True

def callback(key: str, value :dict) -> None:
    try:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url is None:
            return
        Alert(webhook_url).send_alert(value)
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        raise
    finally:
        pass

class Alert:
    def __init__(self, webhook_url: str):
        self.url = webhook_url
        self.client = Discord(url=webhook_url)
        
    def send_alert(self, data: dict, container_data: dict = None):
        try:
            # 데이터 검증
            if not all(key in data for key in ['data', 'command', 'process', 'event_id', 'cgroup_id', 'container_id', ]):
                raise ValueError("Missing required fields in data")
            
            ret_val = data["return_value"]

            self.client.post(
                username="Alert",
                avatar_url="https://t3.ftcdn.net/jpg/01/93/90/82/360_F_193908219_ak4aB1PzlhizUVGLOVowzHICc3tl6WeX.jpg",
                embeds=[{
                    "title": "LSM Block Alert",
                    "description": f"컨테이너에서 {'의심스런' if ret_val == -1 else '아래'} 접근이 {'차단' if ret_val == -1 else '허용'} 되었습니다.",
                    "fields": [
                        {
                        "name": "🚨 Event ID",
                        "value": str(data['event_id']),
                        "inline": True
                        },
                        {
                        "name": "⚡ Command",
                        "value": str(data['command']),
                        "inline": True
                        },
                        {
                        "name": "📁 Path",
                        "value": str(data["data"]['path']),
                        "inline": True
                        },
                        {
                        "name": "🔍 Source",
                        "value": str(data["data"]['source']),
                        "inline": True
                        },
                        {
                        "name": "📦 Container Information",
                        
                        },
                        {
                        "name": "👤 Process Information",
                        "value": f"NAME: {container_data['name'] if container_data else 'None'}, Image: {container_data['image'] if container_data else 'None'}\nMNT_NS: {data['container_id']['mnt_ns']}\nPID_NS: {data['container_id']['pid_ns']}\nCGROUP_ID: {data['cgroup_id']}"
                        },
                        {
                        "name": "⏰ Timestamp",
                        "value": datetime.strptime(data['timestamp'][:-4], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).isoformat(),
                        }
                    ],
                    "color": 0xFF0000 if ret_val == -1 else 0x00FF00,  
                    "footer": {
                        "text": "LSM Security Alert System",
                        "icon_url": "https://avatars.githubusercontent.com/u/187281017?v=4"
                    },
                    "timestamp": datetime.now().isoformat()
                }]
            )
            print("Alert sent successfully!")
            
        except Exception as e:
            print(f"Error sending Discord alert: {str(e)}")
            raise