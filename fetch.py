import pdb
import statsapi
import argparse
import pprint
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import csv

# run with number of days specified and output file
# returns a csv where columns are fields we care about
# and rows are games that meet our requirements

START_INNING = 6
RUN_THRESHOLD = 8
CSV_HEADERS = ['date', 'home', 'away', 'pos?', 'pos team', 'pos name', 'pos runs',
               'pos num pitches', 'score 6', 'score 7', 'score 8',
               'score 9', 'final score', 'pitchers 6', 'pitchers 7',
               'pitchers 8', 'pitchers 9', 'final pitchers']

# 'score 6' => (home score after 6, away score after 6)
# 'final pitchers' => (home total pitchers used, away total pitchers used)


@dataclass
class GameData:
    """Class for keeping track of a game's data."""
    date: str = ''
    game_id: int = 0
    home_team: str = ''
    away_team: str = ''
    is_pos: bool = False
    pos_name: str = ''
    pos_team: str = ''  # 'Home' or 'Away' (or '' if no pos)
    pos_runs: int = 0
    pos_num_pitches: int = 0
    innings = int = 9
    # map from inning to home score, starting at START_INNING until end of game
    home_score_after: dict[int, int] = field(default_factory=dict)
    away_score_after: dict[int, int] = field(default_factory=dict)
    # map from inning to num pitchers, starting at START_INNING until end of game
    home_pitchers_after: dict[int, int] = field(default_factory=dict)
    away_pitchers_after: dict[int, int] = field(default_factory=dict)

    def should_log(self) -> bool:
        """Whether we should log this game."""
        # check if score difference is >= RUN_THRESHOLD
        is_blowout = False
        for i in range(START_INNING, self.innings + 1):
            is_blowout |= (
                abs(self.home_score_after[i] - self.away_score_after[i]) >= RUN_THRESHOLD)

        return is_blowout or self.is_pos

    def to_csv_row(self):
        """CSV row representation of this GameData object."""
        def check(val):
            return val if val else 'null'

        return [self.date, self.home_team, self.away_team, str(self.is_pos)[0],
                check(self.pos_team), check(self.pos_name), self.pos_runs,
                self.pos_num_pitches,
                "({0}-{1})".format(self.home_score_after[6],
                                 self.away_score_after[6]),
                "({0}-{1})".format(self.home_score_after[7],
                                 self.away_score_after[7]),
                "({0}-{1})".format(self.home_score_after[8],
                                 self.away_score_after[8]),
                "({0}-{1})".format(self.home_score_after[9],
                                 self.away_score_after[9]),
                "({0}-{1})".format(self.home_score_after[self.innings],
                                 self.away_score_after[self.innings]),
                "({0}-{1})".format(self.home_pitchers_after[6],
                                 self.away_pitchers_after[6]),
                "({0}-{1})".format(self.home_pitchers_after[7],
                                 self.away_pitchers_after[7]),
                "({0}-{1})".format(self.home_pitchers_after[8],
                                 self.away_pitchers_after[8]),
                "({0}-{1})".format(self.home_pitchers_after[9],
                                 self.away_pitchers_after[9]),
                "({0}-{1})".format(self.home_pitchers_after[self.innings], self.away_pitchers_after[self.innings])]


def parse_line(linescore, innings):
    away_score_after = {}
    home_score_after = {}

    lines = [line.split() for line in linescore.splitlines()[1:]]
    lines = [[s for s in line if s.isdigit()] for line in lines]

    away_score, home_score = 0, 0
    for i in range(1, innings+1):
        away_score += int(lines[0][i-1])
        home_score += int(lines[1][i-1])

        if i >= START_INNING:
            away_score_after[i] = away_score
            home_score_after[i] = home_score
    return (home_score_after, away_score_after)


def parse_pitchers(boxscore, total_innings):
    def helper(pitchers, pitchers_after):
        innings, outs = 0, 0
        num_pitchers, last_insert = 0, 0

        for pitcher in pitchers[1:]:
            ip = pitcher['ip'].split('.')
            innings += int(ip[0])
            outs += int(ip[1])

            if outs >= 3:
                innings += 1
                outs = outs % 3

            num_pitchers += 1
            if innings >= START_INNING and innings > last_insert:
                # innings will always be >= START_INNING
                # last_insert will be 0 or >= START_INNING
                # we want to ensure that we don't insert for the same inning twice
                for inning in range(max(START_INNING, last_insert+1), innings+1):
                    pitchers_after[inning] = num_pitchers
                    last_insert = inning

        for inning in range(last_insert+1, total_innings+1):
            pitchers_after[inning] = pitchers_after[last_insert]

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
parser.add_argument('-f', '--file', type=str, default='games.csv')
parsed_args = parser.parse_args()
# pdb.set_trace()

now = datetime.now()
today = now.strftime('%m/%d/%Y')

start = now - timedelta(days=parsed_args.days)
start_date = start.strftime('%m/%d/%Y')

games = statsapi.schedule(start_date=start_date, end_date=today)
filtered_games = []

for game in games:
    if game['status'] == 'Final':
        gid = game['game_id']
        game_data = GameData(
            game['game_date'], gid, game['home_name'], game['away_name'])

        linescore = statsapi.linescore(gid)
        game_data.innings = game['current_inning']
        game_data.home_score_after, game_data.away_score_after = parse_line(
            linescore, game_data.innings)

        boxscore = statsapi.boxscore_data(gid)
        pos_team, pos = get_pos(boxscore)
        game_data.is_pos = pos != None

        if game_data.is_pos:
            # only logs the first pos found; doesn't log multiple pos
            game_data.pos_team = pos_team
            game_data.pos_name = pos['name']
            game_data.pos_runs = pos['r']
            game_data.pos_num_pitches = pos['p']

        game_data.home_pitchers_after, game_data.away_pitchers_after = parse_pitchers(
            boxscore, game_data.innings)

        if game_data.should_log():
            filtered_games.append(game_data)

with open(parsed_args.file, 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(CSV_HEADERS)

    game_rows = [game.to_csv_row() for game in filtered_games]
    pdb.set_trace()
    writer.writerows(game_rows)
