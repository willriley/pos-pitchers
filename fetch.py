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
CSV_HEADERS = ['date', 'game id', 'home', 'away', 'pos?', 'pos team', 'pos name',
               'pos runs', 'runs in pos inning', 'pos num pitches', 'diff at decision pt',
               'score 6 diff', 'score 7 diff', 'score 8 diff', 'score 9 diff',
               'final score', 'pitchers 6', 'pitchers 7', 'pitchers 8', 'pitchers 9']


@dataclass
class GameData:
    """Class for keeping track of a game's data."""
    date: str = ''
    id: int = 0
    home_team: str = ''
    away_team: str = ''
    is_pos: bool = False
    pos_name: str = ''
    pos_team: str = ''  # 'Home' or 'Away' (or '' if no pos)
    # number of runs the pos pitcher gave up; NOT the number of runs in the whole inning
    pos_runs: int = 0
    pos_inning_pitched: int = 0
    runs_in_pos_inning: int = 0  # number of runs in the inning where the pos pitched
    # if pos came in, records the run diff right before they came in.
    # if pos didn't come in, records the run diff when the pos would've come in.
    run_diff_at_decision_point: int = 0
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

    def get_diff_at_decision_point(self):
        home_inning, away_innning = None, None

        # if is pos, fetch inning that they pitched and team
        # away team -> pitched in the bottom of inning x
        # score diff is (away_score_after[x] - home_score_after[x-1])
        # home team -> pitched in the top of inning x
        # score diff was (away_score_after[x-1] - home_score_after[x-1])
        if self.is_pos:
            if self.pos_team == 'Home':
                home_inning = away_innning = self.pos_inning_pitched - 1
            elif self.pos_team == 'Away':
                home_inning = self.pos_inning_pitched - 1
                away_innning = self.pos_inning_pitched
        else:
            # if no pos, get the team who's being blown out
            # away team -> assume they'd put pos in at bottom of 8th
            # score diff is (away_score_after[8] - home_score_after[7])
            # home team -> assume they'd put pos in at top of 9th
            # score diff is (away_score_after[8] - home_score_after[8])
            blown_out_team = 'Home' if self.home_score_after[
                self.innings] < self.away_score_after[self.innings] else 'Away'
            if blown_out_team == 'Home':
                home_inning = away_innning = 8
                self.runs_in_pos_inning = (self.home_score_after[9]-self.home_score_after[8]) + (
                    self.away_score_after[9] - self.away_score_after[8])
            else:
                home_inning, away_innning = 7, 8
                self.runs_in_pos_inning = (self.home_score_after[8]-self.home_score_after[7]) + (
                    self.away_score_after[8] - self.away_score_after[8])

        self.run_diff_at_decision_point = abs(
            self.home_score_after[home_inning] - self.away_score_after[away_innning])

    def to_csv_row(self):
        """CSV row representation of this GameData object."""
        def check(val):
            return val if val else '-'

        return [self.date, self.id, self.home_team, self.away_team, str(self.is_pos)[0],
                check(self.pos_team), check(self.pos_name),
                self.pos_runs if self.is_pos else '-',
                self.runs_in_pos_inning,
                self.pos_num_pitches if self.is_pos else '-',
                self.run_diff_at_decision_point,
                abs(self.home_score_after[6] - self.away_score_after[6]),
                abs(self.home_score_after[7] - self.away_score_after[7]),
                abs(self.home_score_after[8] - self.away_score_after[8]),
                abs(self.home_score_after[9] - self.away_score_after[9]),
                "({0}-{1})".format(self.home_score_after[self.innings],
                                   self.away_score_after[self.innings]),
                "({0}-{1})".format(self.home_pitchers_after[6],
                                   self.away_pitchers_after[6]),
                "({0}-{1})".format(self.home_pitchers_after[7],
                                   self.away_pitchers_after[7]),
                "({0}-{1})".format(self.home_pitchers_after[8],
                                   self.away_pitchers_after[8]),
                "({0}-{1})".format(self.home_pitchers_after[9],
                                   self.away_pitchers_after[9])]


def parse_line(linescore, innings):
    away_score_after = {}
    home_score_after = {}

    lines = [line for line in linescore.splitlines()]
    header = lines[0]
    inning, inning_idx = 1, header.find('1')
    away_score, home_score = 0, 0

    while inning <= innings:
        away_score += int(lines[1][inning_idx:inning_idx+2])
        home_score += int(lines[2][inning_idx:inning_idx+2])

        if inning >= START_INNING:
            away_score_after[inning] = away_score
            home_score_after[inning] = home_score

        inning_idx += 2
        inning += 1

    return (home_score_after, away_score_after)


def parse_pitchers(boxscore, total_innings, pos_id):
    def helper(pitchers, pitchers_after, pos_inning):
        innings, outs = 0, 0
        num_pitchers, last_insert = 0, 0

        for pitcher in pitchers[1:]:
            ip = pitcher['ip'].split('.')
            innings += int(ip[0])
            outs += int(ip[1])

            if outs >= 3:
                innings += 1
                outs = outs % 3

            if pitcher['personId'] == pos_id and pos_inning == None:
                pos_inning = innings

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

        return pos_inning

    away_pitchers_after = {}
    home_pitchers_after = {}
    pos_inning_pitched = helper(
        boxscore['awayPitchers'], away_pitchers_after, None)
    pos_inning_pitched = helper(
        boxscore['homePitchers'], home_pitchers_after, pos_inning_pitched)

    return (home_pitchers_after, away_pitchers_after, pos_inning_pitched)


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
    if home_pos:
        return ('Home', home_pos)
    return ('', None)


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--days', type=int, default=30)
parser.add_argument('-f', '--file', type=str, default='games.csv')
parsed_args = parser.parse_args()

now = datetime.now()
today = now.strftime('%m/%d/%Y')

start = now - timedelta(days=parsed_args.days)
start_date = start.strftime('%m/%d/%Y')

games = statsapi.schedule(start_date=start_date, end_date=today)
# pdb.set_trace()

with open(parsed_args.file, 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(CSV_HEADERS)

    for game in games:
        if game['status'] == 'Final':
            gid = game['game_id']
            game_data = GameData(
                game['game_date'], gid, game['home_name'], game['away_name'])

            linescore = statsapi.linescore(gid)
            game_data.innings = game['current_inning']
            if game_data.innings < 9:
                # throw out rain-shortened games
                continue

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

            pos_id = None if not pos else pos['personId']
            game_data.home_pitchers_after, game_data.away_pitchers_after, pos_inning_pitched = parse_pitchers(
                boxscore, game_data.innings, pos_id)

            if pos_inning_pitched:
                game_data.pos_inning_pitched = pos_inning_pitched
                game_data.runs_in_pos_inning = (game_data.home_score_after[pos_inning_pitched] - game_data.home_score_after[pos_inning_pitched-1]) + (
                    game_data.away_score_after[pos_inning_pitched] - game_data.away_score_after[pos_inning_pitched-1])

            game_data.get_diff_at_decision_point()

            if game_data.should_log():
                print(game_data)
                writer.writerow(game_data.to_csv_row())
