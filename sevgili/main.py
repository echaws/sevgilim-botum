import discord
from discord.ext import commands, tasks
import os
import json
import random
from datetime import datetime, date
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import collections
import re
import database
import aiohttp

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
USER1_ID = int(os.getenv('USER_ID_1') or 0)
USER2_ID = int(os.getenv('USER_ID_2') or 0)
ANNIVERSARY_DATE_STR = os.getenv('ANNIVERSARY_DATE')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
database.init_db()

# Load movies
with open('movies.json', 'r') as f:
    MOVIES = json.load(f)

async def get_random_cat_gif():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search?mime_types=gif") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[0]['url']
    except Exception as e:
        print(f"Kedi GIF'i alınırken hata oluştu: {e}")
    return None

def get_days_until_anniversary():
    if not ANNIVERSARY_DATE_STR:
        return 0
    try:
        anniversary_date = datetime.strptime(ANNIVERSARY_DATE_STR, '%Y-%m-%d').date()
    except:
        return 0
    today = date.today()
    
    # Get the next anniversary occurrence
    next_anniversary = anniversary_date.replace(year=today.year)
    if next_anniversary < today:
        next_anniversary = next_anniversary.replace(year=today.year + 1)
    
    delta = next_anniversary - today
    return delta.days

async def send_anniversary_message():
    days_left = get_days_until_anniversary()
    
    embed = discord.Embed(
        title="⌛ Yıl Dönümü Sayacı",
        description=f"❤️ Günaydınnnnnnnnnn Sevgililik yıl dönümümüze tam **{days_left}** gün kaldı! Seni çok seviyoruuuuuuuummmmmmmm. ❤️",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Her gün daha fazla aşkla...")
    
    user1 = await bot.fetch_user(USER1_ID)
    user2 = await bot.fetch_user(USER2_ID)
    
    if user1: await user1.send(embed=embed)
    if user2: await user2.send(embed=embed)

async def send_random_movie():
    if not MOVIES:
        return
    movie = random.choice(MOVIES)
    
    embed = discord.Embed(
        title="🎬 Günün Film Önerisi",
        description=f"Bu akşam izlemeye ne dersin?\n\n🍿 **{movie}**",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="İyi seyirler dilerim!")
    
    user1 = await bot.fetch_user(USER1_ID)
    user2 = await bot.fetch_user(USER2_ID)
    
    if user1: await user1.send(embed=embed)
    if user2: await user2.send(embed=embed)

async def send_random_cat():
    gif_url = await get_random_cat_gif()
    if not gif_url:
        return
        
    embed = discord.Embed(
        title="🐱 Günün Kedi GIF'i",
        description="Şu tatlışlığa bak! 😍",
        color=discord.Color.from_rgb(255, 192, 203), # Pink
        timestamp=datetime.now()
    )
    embed.set_image(url=gif_url)
    embed.set_footer(text="Günün neşesi olsun!")
    
    user1 = await bot.fetch_user(USER1_ID)
    user2 = await bot.fetch_user(USER2_ID)
    
    if user1: await user1.send(embed=embed)
    if user2: await user2.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    
    # Setup Scheduler
    scheduler = AsyncIOScheduler()
    
    # Daily anniversary countdown at 09:00
    scheduler.add_job(send_anniversary_message, CronTrigger(hour=9, minute=0))
    
    # Random movie suggestions
    times = ["12:00", "18:00", "21:00"]
    for t in times:
        h, m = map(int, t.split(':'))
        scheduler.add_job(send_random_movie, CronTrigger(hour=h, minute=m))
        
    # Random cat GIFs (3 times daily)
    cat_times = ["10:30", "14:30", "19:30"]
    for t in cat_times:
        h, m = map(int, t.split(':'))
        scheduler.add_job(send_random_cat, CronTrigger(hour=h, minute=m))
        
    scheduler.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.author.id in [USER1_ID, USER2_ID]:
        if not message.content.startswith('!'):
            database.log_message(message.author.id, message.content)
    
    await bot.process_commands(message)

@bot.command(name='analiz')
async def analyze_chat(ctx):
    if ctx.author.id not in [USER1_ID, USER2_ID]:
        return

    data = database.get_stats()
    if not data:
        await ctx.send("Henüz analiz edilecek mesaj yok! 🤷‍♂️")
        return

    all_text = ""
    emojis = []
    days = collections.defaultdict(int)
    
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|<a?:.+?:\d+>')
    
    for content, timestamp in data:
        all_text += " " + content.lower()
        found_emojis = emoji_pattern.findall(content)
        emojis.extend(found_emojis)
        
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except:
                continue
        days[str(dt.date())] += 1

    words = re.findall(r'\w+', all_text)
    filtered_words = [w for w in words if len(w) > 3]
    most_common_words = collections.Counter(filtered_words).most_common(5)
    most_common_emojis = collections.Counter(emojis).most_common(5)
    
    busiest_day_str = max(days, key=days.get) if days else "N/A"
    busiest_count = days[busiest_day_str] if busiest_day_str != "N/A" else 0
    askim_count = words.count('aşkım') + words.count('askim')

    embed = discord.Embed(
        title="📊 Chat Analiz Raporu",
        description="Aranızdaki konuşmaların özeti:",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    
    word_list = "\n".join([f"• {word}: {count}" for word, count in most_common_words])
    embed.add_field(name="🏆 En Çok Kelimeler", value=word_list or "Yok", inline=True)
    
    emoji_list = "\n".join([f"• {emoji}: {count}" for emoji, count in most_common_emojis])
    embed.add_field(name="🥰 En Çok Emojiler", value=emoji_list or "Yok", inline=True)
    
    embed.add_field(name="📅 En Yoğun Gün", value=f"{busiest_day_str} ({busiest_count} mesaj)", inline=False)
    embed.add_field(name="❤️ Aşkım Sayacı", value=f"Tam **{askim_count}** kez 'aşkım' dediniz!", inline=False)
    
    embed.set_footer(text=f"Analizi isteyen: {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command(name='mesaj')
async def send_private_message(ctx, *, message_content):
    if ctx.author.id == USER1_ID:
        recipient_id = USER2_ID
    elif ctx.author.id == USER2_ID:
        recipient_id = USER1_ID
    else:
        return
    
    recipient = await bot.fetch_user(recipient_id)
    if recipient:
        embed = discord.Embed(
            title="💌 Yeni Bir Mesajın Var!",
            description=message_content,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await recipient.send(embed=embed)
        if ctx.guild:
            await ctx.message.delete()
        await ctx.author.send("Mesajın başarıyla gönderildi! ✅", delete_after=5)

if __name__ == "__main__":
    bot.run(TOKEN)
