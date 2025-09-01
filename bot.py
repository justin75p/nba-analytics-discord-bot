import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

# Load token
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Set up bot
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected!")

@bot.command()
async def echo(ctx, *, arg):
    await ctx.send(arg)


bot.run(token = token, log_handler = handler, log_level = logging.DEBUG)