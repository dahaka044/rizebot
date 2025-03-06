import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pytz
from threading import Lock
from flask import Flask
import threading

# -------------------- FLASK SUNUCUSU --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Bot Aktif | " + datetime.now(pytz.timezone('Europe/Istanbul')).strftime("%d/%m %H:%M")

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# -------------------- ORTAM DEĞİŞKENLERİ --------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIZE_ROLE_ID = int(os.getenv("RIZE_ROLE_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# -------------------- GLOBAL AYARLAR --------------------
IST = pytz.timezone('Europe/Istanbul')
notification_lock = Lock()

# -------------------- DISCORD BOT AYARLARI --------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# -------------------- ETKİNLİK VERİLERİ --------------------
EVENT_DATA = {
    "BDW": {
        "img": "https://prnt.sc/IwzCXuokYbao",
        "schedule": [2, 14, 20],
        "emoji": "⚔️",
        "color": 0xff0000
    },
    "Death Match": {
        "img": "https://prnt.sc/ByWI6D6hmWaY",
        "schedule": [3, 11, 17],
        "emoji": "💀",
        "color": 0x000000
    },
    "At Yarışı": {
        "img": "https://prnt.sc/0W62i1Z_PIiw",
        "schedule": [6, 10, 15, 18],
        "emoji": "🏇",
        "color": 0x00ff00
    },
    "Inferno Temple": {
        "img": "https://prnt.sc/7Pb7YHC9IbJ8",
        "schedule": [8, 20.5],
        "emoji": "🔥",
        "color": 0xff4500
    },
    "Davulcu": {
        "img": "https://prnt.sc/ZehgOBYmzYxD",
        "schedule": [23],
        "emoji": "🥁",
        "color": 0x800080
    }
}

# -------------------- YARDIMCI FONKSİYONLAR --------------------
def create_event_list():
    events = []
    for event_name, data in EVENT_DATA.items():
        for time in data["schedule"]:
            hour = int(time)
            minute = 30 if (time % 1 != 0) else 0
            events.append({
                "name": event_name,
                "hour": hour,
                "minute": minute,
                "emoji": data["emoji"],
                "img": data["img"],
                "color": data["color"]
            })
    return events

EVENT_TIMES = create_event_list()

# -------------------- BİLDİRİM SİSTEMİ --------------------
async def send_notification(event):
    with notification_lock:
        try:
            now = datetime.now(IST)
            event_time = IST.localize(datetime(
                now.year, now.month, now.day,
                event["hour"], event["minute"]
            ))
            
            # Ertesi gün kontrolü
            if event_time < now:
                event_time += timedelta(days=1)
            
            embed = discord.Embed(
                title=f"{event['emoji']} {event['name']} Yaklaşıyor!",
                description=f"**30 Dakika Sonra Başlıyor!**\n`🕒 {event_time.strftime('%H:%M')}`",
                color=event["color"]
            )
            embed.set_image(url=event["img"])
            
            channel = bot.get_channel(CHANNEL_ID)
            rize_role = channel.guild.get_role(RIZE_ROLE_ID)
            await channel.send(f"{rize_role.mention} 🔔", embed=embed)
            
        except Exception as e:
            print(f"❌ Hata: {str(e)}")

# -------------------- ZAMAN KONTROL MEKANİZMASI --------------------
async def event_checker():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now(IST)
            for event in EVENT_TIMES:
                event_time = IST.localize(datetime(
                    now.year, now.month, now.day,
                    event["hour"], event["minute"]
                ))
                
                if event_time < now:
                    event_time += timedelta(days=1)
                
                reminder_time = event_time - timedelta(minutes=30)
                
                if (reminder_time - timedelta(seconds=30)) <= now <= (reminder_time + timedelta(seconds=30)):
                    await send_notification(event)
            
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"❌ Kontrol Hatası: {str(e)}")

# -------------------- GÜNCELLENMİŞ !takvim KOMUTU --------------------
@bot.command()
async def takvim(ctx):
    """Aynı gün içindeki etkinlikleri gösterir"""
    now = datetime.now(IST)
    start_hour = now.hour
    start_minute = now.minute
    
    embed = discord.Embed(
        title=f"🎮 **{now.strftime('%d/%m')} Günlük Etkinlik Takvimi** 🎮",
        description=f"**{start_hour:02d}:{start_minute:02d} - 23:59** arası etkinlikler:",
        color=0x7289da
    )
    
    events_added = False
    for event in EVENT_TIMES:
        event_time = IST.localize(datetime(
            now.year, now.month, now.day,
            event["hour"], event["minute"]
        ))
        
        # Ertesi gün etkinliklerini filtrele
        if event_time < now:
            continue
        
        # Saat aralığı kontrolü
        if event["hour"] >= start_hour:
            time_str = event_time.strftime("%H:%M")
            field_value = (
                f"{event['emoji']} **Saat:** ||`{time_str}`||\n"
                f"🔗 **Resim:** [Görüntüle]({event['img']})"
            )
            embed.add_field(
                name=f"**{event['name']}**",
                value=field_value,
                inline=False
            )
            events_added = True
    
    if not events_added:
        embed.description = "⏳ **Bugün başlayacak başka etkinlik yok**"
        
    embed.set_footer(text=f"🕒 Türkiye Saati: {now.strftime('%H:%M:%S')}")
    await ctx.send(embed=embed)

# -------------------- GÜNCELLENMİŞ !test KOMUTU --------------------
@bot.command()
async def test(ctx):
    """2 dakika sonrasına test bildirimi gönderir"""
    now = datetime.now(IST)
    test_time = now + timedelta(minutes=2)
    
    test_event = {
        "name": "TEST ETKİNLİK",
        "hour": test_time.hour,
        "minute": test_time.minute,
        "emoji": "⚠️",
        "img": "https://prnt.sc/eOcmjYQJ5k6m",
        "color": 0xffff00
    }
    
    await send_notification(test_event)
    await ctx.send(f"✅ **{test_time.strftime('%H:%M')}** saatine test bildirimi ayarlandı!")

# -------------------- BOT BAŞLATMA --------------------
@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} çevrimiçi!')
    await bot.change_presence(activity=discord.Game(name="Rise Online | !takvim"))
    bot.loop.create_task(event_checker())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
