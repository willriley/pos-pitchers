import statsapi
import argparse
import pprint
from datetime import datetime, timedelta
from dataclasses import dataclass

START_INNING = 6

# run with number of days specified
# returns a csv where columns are fields we care about
# and rows are games that meet our requirements

@dataclass
class GameData:
    """Class for keeping track of a game's data."""
    home_team: str = ''
    away_team: str = ''
    is_pos: bool = False
    pos_name: str = ''
    pos_runs: int = 0
    pos_num_pitches: int = 0
    home_score_after: dict[int, int] = {} # from inning to score
    away_score_after: dict[int, int] = {}
    home_pitchers_after: dict[int, int] = {} # from inning to num pitchers
    away_pitchers_after: dict[int, int] = {}

    def should_log(self) -> bool:
    """Whether we should log this game."""
        return True

    @staticmethod
    def from_boxscore(boxscore) -> GameData:
    """Parses raw boxscore into a GameData object. Throws an exception if it
    can't parse the game correctly."""

def parse_line(linescore, innings):
    away_score_after = {}
    home_score_after = {}

    lines = [line.split() for line in linescore.splitlines()[1:]]
    lines = [[s for s in line if s.isdigit()] for line in lines]

    away_score, home_score = 0, 0
    for i in range(START_INNING, innings):
        away_score += int(lines[0][i])
        home_score += int(lines[1][i])
        away_score_after[i] = away_score
        home_score_after[i] = home_score

    print(away_score_after)
    print(home_score_after)
    return (home_score_after, away_score_after)

def is_pos(player_id):
    players = statsapi.lookup_player(player_id)
    if not players:
        return False

    player = players[0]
    pos = player['primaryPosition']['abbreviation']
    return pos != 'P' and pos != 'TWP'

def get_pos(boxscore):
    def find_pos(pitchers):
        for pitcher in pitchers[1:]:
            if is_pos(pitcher['personId']):
                return pitcher
        return None

    away_pos = find_pos(boxscore['awayPitchers'])
    return away_pos if away_pos != None else find_pos(boxscore['homePitchers'])

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--days', type=int, default=30)

now = datetime.now()
today = now.strftime('%m/%d/%Y')

start = now - timedelta(days=parser.parse_args().days)
start_date = start.strftime('%m/%d/%Y')

games = statsapi.schedule(start_date=start_date, end_date=today)
for game in games:
    if game['status'] != 'Final':
        gid = game['game_id']

        # num of runs after 6/7/8/9
        # - fetch line score and parse (take num innings as param)
        linescore = statsapi.linescore(gid)
        home_score_after, away_score_after = parse_line(linescore, game['current_inning'])

        boxscore = statsapi.boxscore_data(gid)

        # 'away'
        # 'homePitchers'/'awayPitchers' (skip first entry)
        # -> lookup 'personId' to determine if pos
        # ->




    # check pos
    # get player ID, look up player primary position != 'TWP' != 'P'

    # pos name, runs and num pitches
    # if pos, get their name, runs, and num pitches

    # num pitchers — running count per team


# pprint.pp(games)

# pprint.pp(statsapi.boxscore_data(games[0]['game_id']))
# pprint.pp(statsapi.boxscore_data(661560))
# for player in statsapi.lookup_player(657272):
#     pprint.pp(player)
#
# pprint.pp(statsapi.linescore(661560))

# TODO:

# game 662357 10 innings
extra_inning_scoreline = statsapi.linescore(662357)
print(extra_inning_scoreline)
parse_line(extra_inning_scoreline, 10)
