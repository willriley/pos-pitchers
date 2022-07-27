import statsapi
import argparse
import pprint
from datetime import datetime, timedelta

# run with number of days specified
# returns a csv where columns are fields we care about
# and rows are games that meet our requirements

def parse_line(linescore, innings):
    away_scores_after = []
    home_scores_after = []

    lines = [line.split() for line in linescore.splitlines()[1:]]
    lines = [[s for s in line if s.isdigit()] for line in lines]

    away_score, home_score = 0, 0
    for i in range(innings):
        away_score += int(lines[0][i])
        home_score += int(lines[1][i])
        away_scores_after.append(away_score)
        home_scores_after.append(home_score)

    print(away_scores_after)
    print(home_scores_after)


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--days', type=int, default=30)

now = datetime.now()
today = now.strftime('%m/%d/%Y')

start = now - timedelta(days=parser.parse_args().days)
start_date = start.strftime('%m/%d/%Y')

games = statsapi.schedule(start_date=start_date, end_date=start_date)
# pprint.pp(games)

# pprint.pp(statsapi.boxscore_data(games[0]['game_id']))
# pprint.pp(statsapi.boxscore_data(661560))
# for player in statsapi.lookup_player(657272):
#     pprint.pp(player)
#
# pprint.pp(statsapi.linescore(661560))

# TODO:
# collect pos pitcher, pos runs, pos num pitches
# num of runs after 6/7/8/9, num of pitchers 6/7/8/9

# num of runs after 6/7/8/9
# - fetch line score and parse (take num innings as param)

# check pos
# get player ID, look up player primary position != 'TWP' != 'P'

# pos name, runs and num pitches
# if pos, get their name, runs, and num pitches

# num pitchers — running count per team

# game 662357 10 innings
extra_inning_scoreline = statsapi.linescore(662357)
print(extra_inning_scoreline)
parse_line(extra_inning_scoreline, 10)
