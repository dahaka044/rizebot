import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
import pytz
import json

# -------------------- ORTAM DEĞİŞKENLERİ --------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIZE_ROLE_ID = int(os.getenv("RIZE_ROLE_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# -------------------- GLOBAL AYARLAR --------------------
IST = pytz.timezone('Europe/Istanbul')  # Tüm zamanlar İstanbul'a göre

# -------------------- DISCORD BOT AYARLARI --------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# -------------------- ETKİNLİK VERİLERİ --------------------
EVENT_FILE = "events.json"

def load_events():
    """JSON dosyasından etkinlikleri yükler."""
    with open(EVENT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

EVENT_DATA = load_events()

def create_event_list():
    """Etkinlikleri uygun formata çevirir."""
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
                "color": int(data["color"], 16)
            })
    return events

EVENT_TIMES = create_event_list()

# -------------------- BİLDİRİM SİSTEMİ --------------------
async def send_notification(event):
    """Discord kanalına etkinlik bildirimi gönderir."""
    now_ist = datetime.now(IST)
    event_time = now_ist.replace(hour=event["hour"], minute=event["minute"], second=0)

    if event_time < now_ist:
        event_time += timedelta(days=1)

    time_left = (event_time - now_ist).seconds // 60

    embed = discord.Embed(
        title=f"{event['emoji']} {event['name']} Yaklaşıyor!",
        description=f"**{time_left} Dakika Sonra Başlıyor!**",
        color=event["color"]
    )
    embed.set_image(url=event["img"])

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        rize_role = channel.guild.get_role(RIZE_ROLE_ID)
        await channel.send(f"{rize_role.mention} 🔔", embed=embed)
        print(f"✅ Discord mesajı gönderildi: {event['name']}")
    else:
        print("⚠️ Discord kanal bulunamadı!")

# -------------------- ZAMAN KONTROL MEKANİZMASI --------------------
async def event_checker():
    """Gelecek etkinlikleri takip eder ve zamanı geldiğinde bildirim gönderir."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now_ist = datetime.now(IST)
            next_event = None
            min_time_diff = float("inf")

            for event in EVENT_TIMES:
                event_time = now_ist.replace(hour=event["hour"], minute=event["minute"], second=0)

                if event_time < now_ist:
                    event_time += timedelta(days=1)

                reminder_time = event_time - timedelta(minutes=30)
                time_diff = (reminder_time - now_ist).total_seconds()

                if 0 <= time_diff < min_time_diff:
                    min_time_diff = time_diff
                    next_event = event

            if next_event and 0 <= min_time_diff <= 10:
                print(f"🚨 Bildirim tetiklendi: {next_event['name']}")
                await send_notification(next_event)

            sleep_time = max(10, min_time_diff)  # Gereksiz döngüyü engelle
            print(f"⏳ Bir sonraki kontrol {sleep_time:.0f} saniye sonra yapılacak.")
            await asyncio.sleep(sleep_time)

        except Exception as e:
            print(f"❌ Kontrol Hatası: {str(e)}")
            await asyncio.sleep(10)

# -------------------- !takvim KOMUTU --------------------
@bot.command()
async def takvim(ctx):
    """İstanbul saatine göre etkinlikleri listeler"""
    now_ist = datetime.now(IST)

    main_embed = discord.Embed(
        title=f"🎮 **{now_ist.strftime('%d/%m')} GÜNLÜK ETKİNLİK TAKVİMİ** 🎮",
        description=f"⏳ **{now_ist.strftime('%H:%M')} - 23:59 (TR Saati)** arası etkinlikler:",
        color=0x7289da
    )

    event_embeds = []

    for event in EVENT_TIMES:
        event_time = now_ist.replace(hour=event["hour"], minute=event["minute"], second=0)
        if event_time < now_ist:
            event_time += timedelta(days=1)

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

    event_embeds.sort(key=lambda x: x[0])
    await ctx.send(embed=main_embed)

    for _, embed in event_embeds:
        await ctx.send(embed=embed)

# -------------------- BOT BAŞLATMA --------------------
@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} çevrimiçi!')
    await bot.change_presence(activity=discord.Game(name="Rise Online | !takvim"))
    bot.loop.create_task(event_checker())

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
