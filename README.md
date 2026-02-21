# NBA Fantasy Discord Bot
A work in progress NBA Discord Bot utilizing nba_api intended for fantasy basketball leagues.

## Bot Features
- **Player game logs** — view stats from a player's last N games
- **Head-to-head history** — see how a player has performed against a specific team this season
- **Player season stats** — averages and league rankings for the current season
- **Performance prediction** — forecasts a player's next game stats based on their last 10 games *(work in progress)*
- **Injury reports** — view current injury status for players *(intended feature)*
- **Team rankings** — offensive and defensive rankings for any team
- **Roster viewer** — full roster with position, height, weight, and age

## Commands

| Command | Description | Example |
|---|---|---|
| `!commands` | List all available commands | `!commands` |
| `!player_last <num_games> <player>` | Show a player's stats over their last N games | `!player_last 10 LeBron James` |
| `!player_vs <team> <player>` | Show a player's stats vs. a specific team this season | `!player_vs Lakers Stephen Curry` |
| `!player_stats <player>` | Show a player's season averages and league rankings | `!player_stats Nikola Jokic` |
| `!predict_performance <player>` | Predict a player's next game stats *(work in progress)* | `!predict_performance Jayson Tatum` |
| `!team <team>` | Show a team's offensive and defensive rankings | `!team Celtics` |
| `!roster <team>` | Show a team's current roster | `!roster Golden State` |

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the root directory with your Discord bot token:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

> Don't have a Discord bot token? Create one at the [Discord Developer Portal](https://discord.com/developers/applications).

