import os
import html
import time
import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
    def send_message(self, text, parse_mode="HTML"):
        """Sends a text message to the configured Telegram chat/channel with 429 rate limit handling."""
        if not self.token or "change-me" in str(self.token).lower() or not self.chat_id or "change-me" in str(self.chat_id).lower():
            print("[WARNING] Telegram credentials not configured. Skipping message notification.")
            return False
            
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=15)
                    
                if response.status_code == 200:
                    print("[INFO] Telegram text alert sent successfully.")
                    return True
                elif response.status_code == 429:
                    res_json = response.json()
                    retry_after = int(res_json.get("parameters", {}).get("retry_after", 5))
                    print(f"[WARNING] Telegram rate limit hit. Sleeping for {retry_after}s (Attempt {attempt+1}/3)...")
                    time.sleep(retry_after)
                else:
                    print(f"[ERROR] Failed to send Telegram message: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"[ERROR] Exception sending Telegram message: {e}")
                time.sleep(2)
                
        return False
            
    def send_photo(self, photo_path, caption="", parse_mode="HTML"):
        """Sends a photo with a caption to the configured Telegram chat/channel with rate limit handling."""
        if not self.token or "change-me" in str(self.token).lower() or not self.chat_id or "change-me" in str(self.chat_id).lower():
            print("[WARNING] Telegram credentials not configured. Skipping photo notification.")
            return False
            
        if not os.path.exists(photo_path):
            print(f"[ERROR] Photo file not found at {photo_path}. Sending text alert instead.")
            return self.send_message(caption, parse_mode=parse_mode)
            
        url = f"{self.base_url}/sendPhoto"
        
        for attempt in range(3):
            try:
                with open(photo_path, "rb") as photo_file:
                    files = {"photo": photo_file}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": parse_mode
                    }
                    
                    print(f"[INFO] Uploading and sending photo {photo_path} to Telegram...")
                    response = requests.post(url, files=files, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        print("[INFO] Telegram photo alert sent successfully.")
                        return True
                    elif response.status_code == 429:
                        res_json = response.json()
                        retry_after = int(res_json.get("parameters", {}).get("retry_after", 5))
                        print(f"[WARNING] Telegram rate limit hit on photo upload. Sleeping for {retry_after}s...")
                        time.sleep(retry_after)
                    else:
                        print(f"[ERROR] Failed to send Telegram photo: {response.status_code} - {response.text}")
                        return self.send_message(caption, parse_mode=parse_mode)
            except Exception as e:
                print(f"[ERROR] Exception sending Telegram photo: {e}")
                time.sleep(2)
                
        return self.send_message(caption, parse_mode=parse_mode)
            
    @staticmethod
    def get_wind_direction_cardinal(deg):
        """Converts wind degrees to cardinal directions."""
        if deg is None:
            return "N/A"
        deg = deg % 360
        val = int((deg / 22.5) + 0.5)
        arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        return arr[val % 16]

    @staticmethod
    def get_wind_direction_cardinal_fa(deg):
        """Converts wind degrees to Persian cardinal directions."""
        if deg is None:
            return "نامشخص"
        deg = deg % 360
        val = int((deg / 22.5) + 0.5)
        arr = ["شمال", "شمال-شمال شرقی", "شمال شرقی", "شرق-شمال شرقی",
               "شرق", "شرق-جنوب شرقی", "جنوب شرقی", "جنوب-جنوب شرقی",
               "جنوب", "جنوب-جنوب غربی", "جنوب غربی", "غرب-جنوب غربی",
               "غرب", "غرب-شمال غربی", "شمال غربی", "شمال-شمال غربی"]
        return arr[val % 16]

    def format_fire_alert(self, lat, lon, frp, confidence, acq_time, status, 
                           temp=None, humidity=None, wind_speed=None, wind_direction=None, 
                           risk_score=None, is_update=False, bypass_reason=None):
        """Formats the fire metrics into a bilingual (Persian/English) HTML string for Telegram."""
        
        # Escape dynamic string parameters to avoid HTML entity parsing errors in Telegram API
        status = html.escape(str(status))
        acq_time = html.escape(str(acq_time))
        
        emoji_status = "🔥" if status == "CONFIRMED" else "⚠️"
        
        # Persian translations
        status_fa = {"CONFIRMED": "تأیید شده", "PENDING": "در انتظار تأیید",
                     "FALSE_POSITIVE": "هشدار کذب", "RESOLVED": "خاموش شده"}.get(status, status)
        
        title_en = "ONGOING ACTIVE FIRE UPDATE" if is_update else "NEW FOREST FIRE DETECTED"
        title_fa = "به‌روزرسانی آتش‌سوزی فعال" if is_update else "آتش‌سوزی جدید در جنگل شناسایی شد"
        
        # Status detail text
        status_detail = f"<b>{status_fa} | {status}</b>"
        if status == "CONFIRMED":
            if bypass_reason:
                status_detail += " (تأیید خودکار | Auto-Confirmed by FRP/Cluster ⚡)"
            else:
                status_detail += " (تأیید توسط دود | Smoke Plume Verified 💨)"
        elif status == "PENDING":
            status_detail += " (در انتظار تأیید ماهواره‌ای | Awaiting Satellite Verification ⏳)"
        elif status == "FALSE_POSITIVE":
            status_detail += " (فیلتر هشدار کذب | False Alarm Filtered 🛡️)"
            
        msg = [
            f"{emoji_status} <b>{title_fa} | {title_en} — ایران 🇮🇷</b> {emoji_status}\n",
            f"<b>وضعیت | Status:</b> {status_detail}",
            f"<b>موقعیت | Location:</b> {lat:.4f}, {lon:.4f}",
            f"<b>توان تابشی | FRP:</b> {frp:.1f} MW",
            f"<b>اطمینان ماهواره | Confidence:</b> {confidence}%",
            f"<b>زمان تشخیص | Detection:</b> {acq_time}\n"
        ]
        
        # Add Weather parameters if available
        if temp is not None or humidity is not None or wind_speed is not None:
            msg.append("🌤️ <b>شرایط جوی | Weather & Risk Assessment:</b>")
            if temp is not None:
                msg.append(f"• <b>دما | Temp:</b> {temp:.1f}°C")
            if humidity is not None:
                msg.append(f"• <b>رطوبت | Humidity:</b> {humidity:.1f}%")
            if wind_speed is not None:
                cardinal_en = self.get_wind_direction_cardinal(wind_direction)
                cardinal_fa = self.get_wind_direction_cardinal_fa(wind_direction)
                deg_lbl = f"{wind_direction:.1f}°" if wind_direction is not None else "N/A"
                msg.append(f"• <b>باد | Wind:</b> {wind_speed:.1f} km/h از {cardinal_fa} | from {cardinal_en} ({deg_lbl})")
            
            # Extreme Wind check: hot and dry conditions with strong winds
            is_extreme_wind = False
            if temp is not None and temp > 38 and humidity is not None and humidity < 25:
                if wind_speed is not None and wind_speed > 20:
                    is_extreme_wind = True
            
            if is_extreme_wind:
                msg.append("⚠️ <b>هشدار باد شدید و خشک | Extreme fire weather — hot, dry, strong winds</b>")
                
            if risk_score is not None:
                risk_level_en = "LOW"
                risk_level_fa = "کم"
                if risk_score >= 80:
                    risk_level_en = "EXTREME 🚨"
                    risk_level_fa = "بسیار زیاد 🚨"
                elif risk_score >= 50:
                    risk_level_en = "HIGH ⚠️"
                    risk_level_fa = "زیاد ⚠️"
                elif risk_score >= 25:
                    risk_level_en = "MODERATE"
                    risk_level_fa = "متوسط"
                msg.append(f"• <b>خطر آتش‌سوزی | Fire Risk:</b> {risk_score:.0f}/100 ({risk_level_fa} | {risk_level_en})")
            
            msg.append("") # newline
            
        if bypass_reason:
            msg.append(f"{bypass_reason}\n")
            
        msg.append(f"📍 <a href='https://www.google.com/maps/search/?api=1&query={lat},{lon}'>مشاهده در Google Maps | Open in Google Maps</a>")
        
        return "\n".join(msg)
