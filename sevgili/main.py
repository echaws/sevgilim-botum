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

def get_days_until_anniversary():
    if not ANNIVERSARY_DATE_STR:
        return 0
    anniversary_date = datetime.strptime(ANNIVERSARY_DATE_STR, '%Y-%m-%d').date()
    today = date.today()
    
    # Get the next anniversary occurrence
    next_anniversary = anniversary_date.replace(year=today.year)
    if next_anniversary < today:
        next_anniversary = next_anniversary.replace(year=today.year + 1)
    
    delta = next_anniversary - today
    return delta.days

async def send_anniversary_message():
    days_left = get_days_until_anniversary()
    message = f"❤️ Günaydınnnnnnnnnn Sevgililik yıl dönümümüze tam **{days_left}** gün kaldı! Seni çok seviyoruuuuuuuummmmmmmm. ❤️"
    
    user1 = await bot.fetch_user(USER1_ID)
    user2 = await bot.fetch_user(USER2_ID)
    
    if user1: await user1.send(message)
    if user2: await user2.send(message)

async def send_random_movie():
    movie = random.choice(MOVIES)
    message = f"🎬 Rastgele Film Önerisi: **{movie}**. Bu akşam izlemeye ne dersin? 🍿"
    
    user1 = await bot.fetch_user(USER1_ID)
    user2 = await bot.fetch_user(USER2_ID)
    
    if user1: await user1.send(message)
    if user2: await user2.send(message)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    
    # Setup Scheduler
    scheduler = AsyncIOScheduler()
    
    # Daily anniversary countdown at 09:00
    scheduler.add_job(send_anniversary_message, CronTrigger(hour=9, minute=0))
    
    # Random movie suggestions
    times = ["12:00", "15:00", "18:00", "21:00"]
    for t in times:
        h, m = map(int, t.split(':'))
        scheduler.add_job(send_random_movie, CronTrigger(hour=h, minute=m))
        
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
    
    # Regex for emojis
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|<a?:.+?:\d+>')
    
    for content, timestamp in data:
        all_text += " " + content.lower()
        found_emojis = emoji_pattern.findall(content)
        emojis.extend(found_emojis)
        
        # timestamp is a string from SQLite
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        days[str(dt.date())] += 1

    # Most used words
    words = re.findall(r'\w+', all_text)
    filtered_words = [w for w in words if len(w) > 3]
    most_common_words = collections.Counter(filtered_words).most_common(5)
    
    # Most used emojis
    most_common_emojis = collections.Counter(emojis).most_common(5)
    
    # Busiest day
    busiest_day_str = max(days, key=days.get) if days else "N/A"
    busiest_count = days[busiest_day_str] if busiest_day_str != "N/A" else 0
    
    # Special keyword check
    askim_count = words.count('aşkım') + words.count('askim')

    response = "📊 **Chat Analiz Raporu** 📊\n\n"
    response += f"🏆 **En çok kullanılan kelimeler:**\n"
    for word, count in most_common_words:
        response += f"- {word}: {count} kez\n"
        
    response += f"\n🥰 **En çok kullanılan emojiler:**\n"
    for emoji, count in most_common_emojis:
        response += f"- {emoji}: {count} kez\n"
        
    response += f"\n📅 **En yoğun konuşulan gün:** {busiest_day_str} ({busiest_count} mesaj)\n"
    response += f"❤️ Toplamda **{askim_count}** kez 'aşkım' demişsiniz!"

    await ctx.send(response)

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
        await recipient.send(f"💌 **{ctx.author.name}** sana bir mesaj gönderdi:\n\n{message_content}")
        if ctx.guild:
            await ctx.message.delete()
        await ctx.author.send("Mesajın başarıyla gönderildi! ✅", delete_after=5)

if __name__ == "__main__":
    bot.run(TOKEN)
