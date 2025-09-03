import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

from nba_api.stats.endpoints import playergamelog, leaguedashteamstats
from nba_api.stats.static import players, teams

# Hardcode current season, only needs an update once a year
CURRENT_SEASON = "2024-25"
SEASON_TYPE = "Regular Season"

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

# Get a player's points and average over their last N games
@bot.command()
async def points_last(ctx, games: int, *, player_name):
    # Look up the player
    player = find_active_player(player_name)
    if not player:
        await ctx.send(f"Could not find player named {player_name}.")
        return
    id = player['id']

    # Get the games they've played this season
    games_this_season = playergamelog.PlayerGameLog(player_id = id, season = CURRENT_SEASON, season_type_all_star = SEASON_TYPE)
    games_data_frame = games_this_season.get_data_frames()[0]

    last_n_games = games_data_frame.head(games)
    if games > 15:
        # Only show average for large requests to avoid long messages
        await ctx.send(f"```Over the past {min(games, len(last_n_games))} games, {player['full_name']} has averaged {round(last_n_games['PTS'].mean(), 1)} points per game.\n```")
    else:
        # Format the games to display nicely
        output = f"{player['full_name']} - Last {games} Regular Season Games:\n"
        output += "```\n"
        output += "Date          Opponent        PTS\n"
        output += "-" * 33 + "\n"

        for _, game in last_n_games.iterrows():
            date = game['GAME_DATE']
            matchup = game['MATCHUP']
            points = game['PTS']
            output += f"{date}  {matchup:<16}{points:>3}\n"
        output += f"Over the past {min(games, len(last_n_games))} games, {player['full_name']} has averaged {round(last_n_games['PTS'].mean(), 1)} points per game.\n"
        output += "```"
        await ctx.send(output)

# Helper method used to search for a team (case insensitive)
# Possible use cases: Lakers, LAL, Los Angeles Lakers
# Potentially returns multiple teams, i.e. searching "Los Angeles" gives two teams
def find_team(team_name: str):
    team_name = team_name.lower()

    teams_list = teams.get_teams()
    matches = []
    for team in teams_list:
        if (team_name in team['full_name'].lower() or
            team_name == team['abbreviation'].lower() or
            team_name in team['nickname'].lower() or 
            team_name in team['city'].lower() or 
            team_name in team['state'].lower()):
                matches.append(team)
    return matches

# Helper method used to search for an active player (case insensitive)
def find_active_player(player_name: str):
    # Find a player by their full name
    player_list = players.find_players_by_full_name(player_name)
    if not player_list:
        return None

    active_players = [player for player in player_list if player['is_active']]
    if not active_players:
        return None
    
    # As of 2025, no active players share the exact same names, so return the first player
    return active_players[0]

bot.run(token = token, log_handler = handler, log_level = logging.DEBUG)