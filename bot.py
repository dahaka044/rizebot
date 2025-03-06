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
IST = pytz.timezone('Europe/Istanbul')  # Tüm zamanlar İstanbul'a göre
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
            now_ist = datetime.now(IST)
            event_time = IST.localize(datetime(
                now_ist.year, now_ist.month, now_ist.day,
                event["hour"], event["minute"]
            ))
            
            if event_time < now_ist:
                event_time += timedelta(days=1)
            
            embed = discord.Embed(
                title=f"{event['emoji']} {event['name']} Yaklaşıyor!",
                description=f"**30 Dakika Sonra Başlıyor!**\n`🕒 {event_time.strftime('%H:%M')} (TR Saati)`",
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
            now_ist = datetime.now(IST)
            print(f"\n🔍 Kontrol Zamanı (TR): {now_ist.strftime('%d/%m %H:%M:%S')}")
            
            for event in EVENT_TIMES:
                # Etkinlik zamanını İstanbul'a göre oluştur
                event_time = IST.localize(datetime(
                    now_ist.year, now_ist.month, now_ist.day,
                    event["hour"], event["minute"]
                ))
                
                # Ertesi gün kontrolü
                if event_time < now_ist:
                    event_time += timedelta(days=1)
                
                # Hatırlatma zamanını hesapla
                reminder_time = event_time - timedelta(minutes=30)
                time_diff = (reminder_time - now_ist).total_seconds()
                
                print(f"|__ {event['name']} | TR Saati: {event_time.strftime('%H:%M')} | Hatırlatma: {reminder_time.strftime('%H:%M:%S')} | Fark: {time_diff:.0f}s")
                
                # Hassas zaman kontrolü (±10 saniye)
                if -10 <= time_diff <= 10:
                    print(f"🚨 Bildirim tetiklendi: {event['name']}")
                    await send_notification(event)
            
            await asyncio.sleep(5)  # 5 saniyede bir kontrol
            
        except Exception as e:
            print(f"❌ Kontrol Hatası: {str(e)}")
            await asyncio.sleep(10)

# -------------------- GÜNCELLENMİŞ !takvim KOMUTU --------------------
@bot.command()
async def takvim(ctx):
    """İstanbul saatine göre etkinlikleri listeler"""
    now_ist = datetime.now(IST)
    
    # Ana Embed
    main_embed = discord.Embed(
        title=f"🎮 **{now_ist.strftime('%d/%m')} GÜNLÜK ETKİNLİK TAKVİMİ** 🎮",
        description=f"⏳ **{now_ist.strftime('%H:%M')} - 23:59 (TR Saati)** arası etkinlikler:",
        color=0x7289da
    )
    main_embed.set_thumbnail(url="https://i.imgur.com/8KZfW3G.png")
    
    # Etkinlik Embed'leri
    event_embeds = []
    
    for event in EVENT_TIMES:
        event_time = IST.localize(datetime(
            now_ist.year, now_ist.month, now_ist.day,
            event["hour"], event["minute"]
        ))
        
        if event_time < now_ist:
            event_time += timedelta(days=1)
        
        if event_time.time() > datetime.strptime("23:59", "%H:%M").time():
            continue
        
        # Etkinlik Embed'i
        embed = discord.Embed(
            title=f"{event['emoji']} {event['name']}",
            color=event["color"]
        )
        embed.add_field(
            name="⏰ **BAŞLAMA SAATİ (TR)**",
            value=f"```fix\n{event_time.strftime('%H:%M')}```",
            inline=False
        )
        embed.set_image(url=event["img"])
        event_embeds.append((event_time, embed))
    
    if not event_embeds:
        main_embed.description = "🎉 **Bugün başka etkinlik yok!**"
        await ctx.send(embed=main_embed)
        return
    
    # Etkinlikleri sırala
    event_embeds.sort(key=lambda x: x[0])
    
    # Ana mesajı gönder
    await ctx.send(embed=main_embed)
    
    # Etkinlikleri gönder
    for _, embed in event_embeds:
        await ctx.send(embed=embed)

# -------------------- BOT BAŞLATMA --------------------
@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} çevrimiçi!')
    await bot.change_presence(activity=discord.Game(name="Rise Online | !takvim"))
    bot.loop.create_task(event_checker())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
