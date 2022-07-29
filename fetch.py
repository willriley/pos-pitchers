import statsapi
import argparse
import pprint
from datetime import datetime, timedelta
from dataclasses import dataclass

START_INNING = 6
RUN_THRESHOLD = 8

# run with number of days specified
# returns a csv where columns are fields we care about
# and rows are games that meet our requirements

@dataclass
class GameData:
    """Class for keeping track of a game's data."""
    date: str = ''
    home_team: str = ''
    away_team: str = ''
    is_pos: bool = False
    pos_name: str = ''
    pos_team: str = ''  # 'Home' or 'Away' (or '' if no pos)
    pos_runs: int = 0
    pos_num_pitches: int = 0
    # map from inning to home score, starting at START_INNING until end of game
    home_score_after: dict[int, int] = {} #
    away_score_after: dict[int, int] = {}
    # map from inning to num pitchers, starting at START_INNING until end of game
    home_pitchers_after: dict[int, int] = {}
    away_pitchers_after: dict[int, int] = {}

    def should_log(self) -> bool:
    """Whether we should log this game."""
        # check if score difference is >= RUN_THRESHOLD
        is_blowout = False
        for i in range(START_INNING, START_INNING + len(self.home_score_after)):
            is_blowout |= (abs(home_score_after[i] - away_score_after[i]) >= RUN_THRESHOLD)

        return is_blowout or self.is_pos


def parse_line(linescore, innings):
    away_score_after = {}
    home_score_after = {}

    lines = [line.split() for line in linescore.splitlines()[1:]]
    lines = [[s for s in line if s.isdigit()] for line in lines]

    away_score, home_score = 0, 0
    for i in range(START_INNING, innings):
        away_score += int(lines[0][i-1])
        home_score += int(lines[1][i-1])
        away_score_after[i] = away_score
        home_score_after[i] = home_score

    print(away_score_after)
    print(home_score_after)
    return (home_score_after, away_score_after)


def parse_pitchers(boxscore):
    # TODO: double check math
    def helper(pitchers, pitchers_after):
        innings, outs = 0, 0
        pitchers = 0

        for pitcher in pitchers[1:]:
            ip = pitcher['ip'].split('.')
            innings += int(ip[0])
            outs += int(ip[1])

            if outs >= 3:
                outs = outs % 3

            pitchers += 1
            if innings >= START_INNING and innings not in pitchers_after:
                pitchers_after[innings] = pitchers

    away_pitchers_after = {}
    home_pitchers_after = {}
    helper(boxscore['awayPitchers'], away_pitchers_after)
    helper(boxscore['homePitchers'], home_pitchers_after)

    return (home_pitchers_after, away_pitchers_after)


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
    if away_pos:
        return ('Away', away_pos)

    home_pos = find_pos(boxscore['homePitchers'])
    return ('Home', home_pos)

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--days', type=int, default=30)

now = datetime.now()
today = now.strftime('%m/%d/%Y')

start = now - timedelta(days=parser.parse_args().days)
start_date = start.strftime('%m/%d/%Y')

games = statsapi.schedule(start_date=start_date, end_date=today)
filtered_games = []

for game in games:
    if game['status'] != 'Final':
        gid = game['game_id']
        game_data = GameData(game['game_date'], game['home_name'], game['away_name'])

        linescore = statsapi.linescore(gid)
        game_data.home_score_after, game_data.away_score_after = parse_line(linescore, game['current_inning'])

        boxscore = statsapi.boxscore_data(gid)
        pos_team, pos = get_pos(boxscore)
        game_data.is_pos = pos != None

        if is_pos:
            # only logs the first pos found; doesn't log multiple pos
            game_data.pos_team = pos_team
            game_data.pos_name = pos['name']
            game_data.pos_runs = pos['r']
            game_data.pos_num_pitches = pos['p']

        game_data.home_pitchers_after, game_data.away_pitchers_after = parse_pitchers(boxscore)

        if game_data.should_log():
            filtered_games.append(game_data)
            # log to csv

# TODO: exceptions, csv logging, debugging

# pprint.pp(games)

# pprint.pp(statsapi.boxscore_data(games[0]['game_id']))
# pprint.pp(statsapi.boxscore_data(661560))
# for player in statsapi.lookup_player(657272):
#     pprint.pp(player)
#
# pprint.pp(statsapi.linescore(661560))

# TODO:

# game 662357 10 innings
# extra_inning_scoreline = statsapi.linescore(662357)
# print(extra_inning_scoreline)
# parse_line(extra_inning_scoreline, 10)
