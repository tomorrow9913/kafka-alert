import os
from discordwebhook import Discord
from datetime import datetime, timezone

from utils.logger import setup_logging

logger = setup_logging(__name__)

alert = None
async def callback(key: str, value :dict) -> None:
    global alert
    if alert is None:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url is None:
            logger.debug("No Discord webhook URL configured")       
            return
        alert = Alert(webhook_url)
    alert.send_alert(value)

class Alert:
    def __init__(self, webhook_url: str):
        self.url = webhook_url
        self.client = Discord(url=webhook_url)
        
    def send_alert(self, data: dict):
        try:
            # 데이터 검증
            if not all(key in data for key in ['pid', 'timestamp', 'detection_time', 'detection_info']):
                raise ValueError("Missing required fields in data")
            
            fields = [
                        {
                        "name": "🚨 PID",
                        "value": str(data['pid']),
                        "inline": True
                        },
                        {
                        "name": "⏰ Called At",
                        # "value": datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).isoformat(),
                        "value": data['timestamp'],
                        },
                        {
                        "name": "⏰ Detected At",
                        # "value": datetime.strptime(data['detection_time'], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).isoformat(),
                        "value": data['detection_time'],
                        },
                        {
                        "name": "🔍 Detection Info",
                        "value": "-"*10,
                        }
                    ]
            for key, value in data['detection_info'].items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
            self.client.post(
                username="Alert",
                avatar_url="https://t3.ftcdn.net/jpg/01/93/90/82/360_F_193908219_ak4aB1PzlhizUVGLOVowzHICc3tl6WeX.jpg",

                embeds=[{
                    "title": "Suspicious Process Detection",
                    "description": f"Detected a suspicious process with PID {data['pid']} at {data['detection_time']}",
                    "fields": fields,
                    "footer": {
                        "text": "Process Monitoring Security Alert System",
                        "icon_url": "https://avatars.githubusercontent.com/u/187281017?v=4"
                    },
                    "timestamp": datetime.now().isoformat()
                }]
            )
            print("Alert sent successfully!")
            
        except Exception as e:
            print(f"Error sending Discord alert: {str(e)}")
            raise