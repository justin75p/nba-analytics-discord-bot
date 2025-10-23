import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import requests_cache
import pandas as pd

from nba_api.stats.endpoints import playergamelog, teaminfocommon, leaguedashteamstats, playerprofilev2, commonteamroster
from nba_api.stats.static import players, teams

from statsmodels.tsa.arima.model import ARIMA

# Hardcode current season, only needs an update once a year
CURRENT_SEASON = "2025-26"
LAST_SEASON = "2024-25"
SEASON_TYPE = "Regular Season"

requests_cache.install_cache('nba_bot_cache', expire_after=3600)

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
async def commands(ctx):
    output = "NBA Bot Commands:\n"
    output += "```"
    output += "!player_last <num_games> <player>        - Show player's stats over last N games this season\n"
    output += "!player_vs <team> <player>               - Show player's performance vs specific team this season\n"
    output += "!player_stats <player>                   - Show player's overall stat averages and rankings this season\n"
    output += "!team <team>                             - Show team's offensive and defensive rankings this season"
    output += "!roster <team>                           - Show team's current roster with player details"
    output += "```"
    await ctx.send(output)

# Command to show a player's stats in their last N games
# Uses PlayerGameLog endpoint
@bot.command()
async def player_last(ctx, games: int, *, player_name: str):
    # Look up the player
    player = find_active_player(player_name)
    if not player:
        await ctx.send(f"Could not find player named {player_name}.")
        return
    id = player['id']

    # Get the games they've played this season
    games_data_frame = get_games_played(id)

    last_n_games = games_data_frame.head(games)
    if games > 15:
        # Only show average for large requests to avoid long messages
        await ctx.send(f"```{player['full_name']} - Last {min(games, len(last_n_games))} Games Averages:\n"
                        f"PTS: {last_n_games['PTS'].mean():.1f}  |  "
                        f"REB: {last_n_games['REB'].mean():.1f}  |  "
                        f"AST: {last_n_games['AST'].mean():.1f}  |  "
                        f"FG%: {last_n_games['FG_PCT'].mean():.1%}  |  "
                        f"3P%: {last_n_games['FG3_PCT'].mean():.1%}\n```")
        # Format the games to display nicely
        output = f"{player['full_name']} - Last {games} Regular Season Games:\n"
        output += "```"
        output += "Date            PTS   REB   AST   FGM   FGA   FG_PCT   FG3M   FG3A   FG3_PCT   FTM   FTA   FT_PCT\n"
        output += "-" * 97 + "\n"

        for _, game in last_n_games.iterrows():
            date = game['GAME_DATE']
            pts = game['PTS']
            reb = game['REB']
            ast = game['AST']
            fgm = game['FGM']
            fga = game['FGA']
            fg_pct = f"{game['FG_PCT']:.1%}"
            fg3m = game['FG3M']
            fg3a = game['FG3A']
            fg3_pct = f"{game['FG3_PCT']:.1%}"
            ftm = game['FTM']
            fta = game['FTA']
            ft_pct = f"{game['FT_PCT']:.1%}"

            output += f"{date}    {pts:>3}   {reb:>3}   {ast:>3}   {fgm:>3}   {fga:>3}   {fg_pct:>6}   {fg3m:>4}   {fg3a:>4}    {fg3_pct:>6}   {ftm:>3}   {fta:>3}   {ft_pct:>6}\n"
        output += "```"
        await ctx.send(output)

# Command that shows a player's performance against a specific team this season
# Uses PlayerGameLog endpoint
@bot.command()
async def player_vs(ctx, team: str, *, player_name: str):
    # Look up the player
    player = find_active_player(player_name)
    if not player:
        await ctx.send(f"Could not find player named {player_name}.")
        return
    player_id = player['id']

    # Look up the team
    potential_teams = find_team(team_name=team)
    if not potential_teams:
        await ctx.send(f"Could not find team using search term \"{team}\".")
        return
    elif len(potential_teams) > 1:
        await ctx.send("Search term too broad, please be more specific.")
        return
    # If there was only one match, the team was found correctly
    team_abbreviation = potential_teams[0]['abbreviation']

    player_game_log = get_games_played(player_id=player_id)

    output = f"{player['full_name']} - Head to Head vs. {potential_teams[0]['full_name']} this season:\n"
    output += "```"
    output += "Date            PTS   REB   AST   FGM   FGA   FG_PCT   FG3M   FG3A   FG3_PCT   FTM   FTA   FT_PCT\n"
    output += "-" * 97 + "\n"

    for _, game in player_game_log.iterrows():
        if team_abbreviation in game['MATCHUP']:
            date = game['GAME_DATE']
            pts = game['PTS']
            reb = game['REB']
            ast = game['AST']
            fgm = game['FGM']
            fga = game['FGA']
            fg_pct = f"{game['FG_PCT']:.1%}"
            fg3m = game['FG3M']
            fg3a = game['FG3A']
            fg3_pct = f"{game['FG3_PCT']:.1%}"
            ftm = game['FTM']
            fta = game['FTA']
            ft_pct = f"{game['FT_PCT']:.1%}"

            output += f"{date}    {pts:>3}   {reb:>3}   {ast:>3}   {fgm:>3}   {fga:>3}   {fg_pct:>6}   {fg3m:>4}   {fg3a:>4}    {fg3_pct:>6}   {ftm:>3}   {fta:>3}   {ft_pct:>6}\n"
    output += "```"
    await ctx.send(output)

# Command that utilizes ARIMA model to predict a player's next performance
@bot.command()
async def predict_performance(ctx, *, player_name: str):
    # Look up the player
    player = find_active_player(player_name)
    if not player:
        await ctx.send(f"Could not find player named {player_name}.")
        return
    # TODO: implement prediction logic
    

# Command that displays a player's stat averages along with their rankings this season
# Uses PlayerProfileV2 endpoint with SeasonRankingsRegularSeason and SeasonTotalsRegularSeason dataset 
@bot.command()
async def player_stats(ctx, *, player_name: str):
    # Look up the player
    player = find_active_player(player_name)
    if not player:
        await ctx.send(f"Could not find player named {player_name}.")
        return
    player_id = player['id']

    # Get the player's profile from the endpoint
    player_profile = playerprofilev2.PlayerProfileV2(player_id=player_id, per_mode36="PerGame")

    # Get their season stat averages and stat rankings as DataSets, then convert them to DataFrame
    season_stats = player_profile.season_totals_regular_season.get_data_frame().iloc[0]
    season_rankings = player_profile.season_rankings_regular_season.get_data_frame().iloc[0]

    output = f"{player['full_name']} - {CURRENT_SEASON} Season Stats:\n"
    output += "```"
    output += f"PPG: {season_stats['PTS']:.1f} (Rank: #{season_rankings['PTS']})\n"
    output += f"RPG: {season_stats['REB']:.1f} (Rank: #{season_rankings['REB']})\n"
    output += f"APG: {season_stats['AST']:.1f} (Rank: #{season_rankings['AST']})\n"
    output += f"FG%: {season_stats['FG_PCT']:.1%} (Rank: #{season_rankings['FG_PCT']})\n"
    output += f"3P%: {season_stats['FG3_PCT']:.1%} (Rank: #{season_rankings['FG3_PCT']})\n"
    output += f"FT%: {season_stats['FT_PCT']:.1%} (Rank: #{season_rankings['FT_PCT']})\n"
    output += "```"

    await ctx.send(output)    

# Command that shows a team's offensive and defensive stat rankings this season
# Uses TeamInfoCommon endpoint
@bot.command()
async def team(ctx, *, team_name: str):
    # Depending on the search term, there may be multiple teams
    potential_teams = find_team(team_name)
    if not potential_teams:
        await ctx.send(f"Could not find team using search term \"{team_name}\".")
        return
    elif len(potential_teams) > 1:
        await ctx.send("Search term too broad, please be more specific.")
        return
    # If there was only one match, the team was found correctly
    team_id = potential_teams[0]['id']

    # Get the season rankings for this team
    team_info = teaminfocommon.TeamInfoCommon(team_id = team_id, league_id = "00", season_nullable = CURRENT_SEASON, season_type_nullable = SEASON_TYPE)
    # Get the only row of data since only one team
    team_season_ranks_data = team_info.team_season_ranks.get_data_frame().iloc[0]

    # Format the output message nicely
    output = f"Season Rankings for the {potential_teams[0]['full_name']}:"
    output += "```\n"
    output += f"#{team_season_ranks_data['PTS_RANK']} in PPG ({team_season_ranks_data['PTS_PG']})\n"
    output += f"#{team_season_ranks_data['REB_RANK']} in RPG ({team_season_ranks_data['REB_PG']})\n"
    output += f"#{team_season_ranks_data['AST_RANK']} in APG ({team_season_ranks_data['AST_PG']})\n"
    output += f"#{team_season_ranks_data['OPP_PTS_RANK']} in OPP PTG ({team_season_ranks_data['OPP_PTS_PG']})\n"
    output += "```"

    # TODO: Show more advanced stat rankings using LeagueDashTeamStats (in the future)
    await ctx.send(output)

# Command that shows a team's roster of players
# Uses CommonTeamRoster endpoint and its dataset containing the players on the team
@bot.command()
async def roster(ctx, *, team_name: str):
    # Look for team
    potential_teams = find_team(team_name)
    if not potential_teams:
        await ctx.send(f"Could not find team using search term \"{team_name}\".")
        return
    elif len(potential_teams) > 1:
        await ctx.send("Search term too broad, please be more specific.")
        return
    # If there was only one match, the team was found correctly
    team_id = potential_teams[0]['id']

    # Get CommonTeamRoster object and its DataFrame
    roster_object = commonteamroster.CommonTeamRoster(team_id=team_id, season=CURRENT_SEASON)
    roster = roster_object.common_team_roster.get_data_frame()

    # TODO: format output
    output = f"Roster information for the {potential_teams[0]['full_name']}:"
    output += "```\n"
    output += "NUM     NAME                       POS   AGE    HGHT    WGHT\n"
    output += "-" * 60 + '\n'
    for _, player in roster.iterrows():
        name = player['PLAYER']
        number = player['NUM']
        position = player['POSITION']
        height = player['HEIGHT']
        weight = player['WEIGHT']
        age = player['AGE']
        output += f"#{number:>3}    {name:<25} {position:>3}    {int(age):>2}    {height:>4}     {weight:>3}\n"
    output += "```"
    await ctx.send(output)

# Helper method used to search for a team (case insensitive)
# Uses static team database
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
# Uses static player database
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

# Helper method that returns a DataFrame of all games a player has played in the current and previous season.
# Uses PlayerGameLog endpoint
def get_games_played(player_id: int):
    games_this_season = playergamelog.PlayerGameLog(player_id = player_id, season = CURRENT_SEASON, season_type_all_star = SEASON_TYPE)
    games_last_season = playergamelog.PlayerGameLog(player_id = player_id, season = LAST_SEASON, season_type_all_star = SEASON_TYPE)

    current_data = games_this_season.player_game_log.get_data_frame()
    last_data = games_last_season.player_game_log.get_data_frame()
    return pd.concat([current_data, last_data])

bot.run(token = token, log_handler = handler, log_level = logging.DEBUG)