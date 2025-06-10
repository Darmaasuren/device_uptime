import time
import datetime
import signal
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB-тэй холбогдох
MONGODB_URL = os.getenv("MONGODB_URL")
client = MongoClient("MONGODB_URL")
db = client["system_logs"]                 # Өгөгдлийн сан
session_collection = db["sessions"]         # Сессийн мэдээлэл хадгалах хүснэгт
downtime_collection = db["downtime_logs"]   # Унтарсан хугацааг хадгалах хүснэгт

# Одоо сессийн ID-г глобал хувиргагч болгон хадгалах
current_session_id = None

def log_start():
    """Компьютер асаах үед шинэ сессийн бичлэг үүсгэж, өмнөх унтарсан хугацааг (downtime)-г тооцоолно."""
    global current_session_id
    startup_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Сүүлд унтарсан сессийг олох
    last_shutdown = downtime_collection.find_one(
        sort=[("shutdown_time", -1)]
    )
    downtime_minutes = None
    downtime_recorded_at = None
    
    if last_shutdown:
        shutdown_time = last_shutdown.get("shutdown_time")
        if shutdown_time:
            if isinstance(shutdown_time, str):
                shutdown_time = datetime.datetime.strptime(shutdown_time, "%Y-%m-%d %H:%M:%S")
            startup_time_dt = datetime.datetime.strptime(startup_time, "%Y-%m-%d %H:%M:%S")
            downtime = startup_time_dt - shutdown_time
            downtime_minutes = int(downtime.total_seconds() / 60)  # Минутаар хөрвүүлэх

            # Downtime-ийг downtime_logs хүснэгтэд хадгалах
            downtime_data = {
                "shutdown_time": shutdown_time.strftime("%Y-%m-%d %H:%M:%S"),  # Унтарсан цаг
                "startup_time": startup_time,  # Ассан цаг
                "downtime_minutes": downtime_minutes,  # Downtime-ийн минут
                "downtime_recorded_at": downtime_recorded_at  # Бүртгэсэн огноо
            }
            downtime_collection.insert_one(downtime_data)
            print(f"Унтарсан хугацаа: {downtime_minutes} минут ({downtime_recorded_at})")
        else:
            print("Унтарсан хугацааг олсонгүй.")

    session_data = {
        "startup_time": startup_time,
        "shutdown_time": None  # Унтарсан цаг одоогоор бичигдээгүй
    }
    
    result = session_collection.insert_one(session_data)
    current_session_id = result.inserted_id
    print(f"Сесс эхэллээ: {startup_time}")

def log_shutdown():
    """Компьютер унтарсан үед сессийн бичлэгийг шинэчилж, shutdown_time-г оруулна."""
    shutdown_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if current_session_id:
        session_collection.update_one(
            {"_id": current_session_id},
            {"$set": {"shutdown_time": shutdown_time}}
        )
        # Downtime-ийг шууд downtime_logs цуглуулгад хадгалах
        downtime_data = {
            "shutdown_time": shutdown_time,
            "startup_time": None,  # Ассан цаг одоогоор бичигдээгүй
            "downtime_minutes": None,  # Минут одоогоор тодорхойгүй
            "downtime_recorded_at": shutdown_time
        }
        downtime_collection.insert_one(downtime_data)
        print(f"Сесс дууслаа: {shutdown_time}")
    else:
        print("Сессийн ID олдсонгүй. Shutdown цагийг бүртгэх боломжгүй.")
    sys.exit(0)

# SIGINT (CTRL+C) болон SIGTERM (system shutdown)-ийг барьж, log_shutdown дуудаж ажиллуулах
signal.signal(signal.SIGINT, lambda signum, frame: log_shutdown())
signal.signal(signal.SIGTERM, lambda signum, frame: log_shutdown())

if __name__ == "__main__":
    log_start()  # Компьютер асаах үед сессийн эхэлсэн цагийг бүртгэнэ

    # Сервисийн үндсэн үйлдэл: тодорхой хугацаа тутамд ямар нэгэн үйлдэл хийх (энд зөвхөн sleep хийж байна)
    try:
        while True:
            time.sleep(60)  # 1 минут тутамд системийн ажиллахыг шалгах
            print(f"Систем ажиллаж байна: {datetime.datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"Алдаа гарлаа: {e}")
        log_shutdown()
