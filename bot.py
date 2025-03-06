import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pytz
from threading import Lock

# -------------------- ORTAM DEĞİŞKENLERİ --------------------
load_dotenv()
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
RIZE_ROLE_ID = int(os.environ["RIZE_ROLE_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# -------------------- GLOBAL AYARLAR --------------------
IST = pytz.timezone('Europe/Istanbul')  # Türkiye saat dilimi
notification_lock = Lock()  # Çoklu bildirim engelleme

# -------------------- DISCORD BOT AYARLARI --------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# -------------------- ETKİNLİK VERİLERİ --------------------
EVENT_DATA = {
    "BDW": {"img": "https://prnt.sc/IwzCXuokYbao", "schedule": [2, 14, 20]},
    "Death Match": {"img": "https://prnt.sc/ByWI6D6hmWaY", "schedule": [3, 11, 17]},
    "At Yarışı": {"img": "https://prnt.sc/0W62i1Z_PIiw", "schedule": [6, 10, 15, 18]},
    "Inferno Temple": {"img": "https://prnt.sc/7Pb7YHC9IbJ8", "schedule": [8, 20.5]},  # 20.5 = 20:30
    "Davulcu": {"img": "https://prnt.sc/ZehgOBYmzYxD", "schedule": [23]}
}

# -------------------- YARDIMCI FONKSİYONLAR --------------------
def create_event_list():
    """EVENT_TIMES listesini dinamik olarak oluşturur"""
    events = []
    for event_name, data in EVENT_DATA.items():
        for time in data["schedule"]:
            hour = int(time)
            minute = 30 if (time % 1 != 0) else 0
            events.append({"name": event_name, "hour": hour, "minute": minute})
    return events

EVENT_TIMES = create_event_list()

# -------------------- BİLDİRİM SİSTEMİ --------------------
async def send_notification(event):
    """Discord"""
    with notification_lock:
        try:
            # Discord Embed
            embed = discord.Embed(
                title=f"🚨 {event['name']} Yaklaşıyor!",
                description=f"**30 Dakika Sonra Başlıyor!**\n`🕒 {event['hour']:02d}:{event['minute']:02d}`",
                color=0x00ff00
            )
            embed.set_image(url=EVENT_DATA[event["name"]]["img"])
            
            channel = bot.get_channel(CHANNEL_ID)
            rize_role = channel.guild.get_role(RIZE_ROLE_ID)
            await channel.send(f"{rize_role.mention} 🔔", embed=embed)                
        except Exception as e:
            print(f"❌ Bildirim Hatası: {str(e)}")

# -------------------- ZAMAN KONTROL MEKANİZMASI --------------------
async def event_checker():
    """Etkinlikleri kontrol eden ana döngü"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            now = datetime.now(IST)
            for event in EVENT_TIMES:
                # Etkinlik zamanını İstanbul saatine göre oluştur
                event_time = IST.localize(datetime(
                    now.year, 
                    now.month, 
                    now.day, 
                    event["hour"], 
                    event["minute"]
                ))
                
                # 30 dakika öncesini hesapla
                reminder_time = event_time - timedelta(minutes=30)
                
                # Hassas zaman kontrolü (±10 saniye)
                if (reminder_time - timedelta(seconds=10)) <= now <= (reminder_time + timedelta(seconds=10)):
                    await send_notification(event)
            
            await asyncio.sleep(15)  # 15 saniyede bir kontrol
            
        except Exception as e:
            print(f"❌ Kontrol Döngüsü Hatası: {str(e)}")
            await asyncio.sleep(30)

# -------------------- KOMUTLAR --------------------
@bot.event
async def on_ready():
    """Bot hazır olduğunda çalışır"""
    print(f'✅ {bot.user.name} çevrimiçi!')
    await bot.change_presence(activity=discord.Game(name="Rise Online"))
    bot.loop.create_task(event_checker())

@bot.command()
async def test(ctx):
    """Manuel test komutu"""
    test_event = {"name": "TEST", "hour": 23, "minute": 59}
    await send_notification(test_event)
    await ctx.send("✅ Test bildirimi gönderildi!")

# -------------------- BAŞLATMA --------------------
if __name__ == "__main__":    
    # Discord botunu çalıştır
    bot.run(DISCORD_TOKEN)