import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

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

@bot.command()
async def player(ctx, *, player_name):
    # Find a player by their full name
    player_list = players.find_players_by_full_name(player_name)
    if not player_list:
        await ctx.send(f"Player {player_name} not found.")
        return

    active_players = [player for player in player_list if player['is_active']]
    if not active_players:
        await ctx.send(f"No active player named {player_name} found.")
        return
    
    # As of 2025, no active players share the exact same names
    player = active_players[0]
    player_id = player['id']

    await ctx.send(f"Found active player {player['full_name']} with id {player_id}")


bot.run(token = token, log_handler = handler, log_level = logging.DEBUG)