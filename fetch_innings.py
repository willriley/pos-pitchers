from concurrent.futures import ThreadPoolExecutor
import statsapi
import argparse
import pprint
from datetime import datetime, timedelta
from dataclasses import dataclass
import csv
import sys
from threading import Lock

# GLOBAL VARIABLES

# map of (game_id, inning, is_top) -> InningData
innings = {}
games_and_linescores = []
# map of game_id -> boxscore object
boxscores = {}
lock = Lock()
# I got the player IDs of any position player who pitched in 2022 from the statcast data.
pos_pitchers = set([593643, 665019, 670768, 642165, 608348, 624503, 621433, 542194, 643524, 596117,
                    571976, 605612, 543281, 641914, 670712, 425877, 644374, 676391, 620443, 621011,
                    660636, 664670, 572191, 606993, 642851, 663630, 444876, 592743, 665155, 518586,
                    573131, 608703, 676946, 405395, 506702, 570560, 622268, 670032, 553902, 572008,
                    572816, 593160, 605170, 641531, 543829, 608686, 608700, 640461, 645801, 545121,
                    545341, 594838, 598265, 606115, 607054, 622569, 624512, 668800, 501303, 650339,
                    661531, 669742, 503556, 571466, 614177])

START_INNING = 7
RUN_THRESHOLD = 8
CSV_HEADERS = ['game_id', 'date', 'home', 'away', 'inning', 'is_top',
               'is_winning_team_batting', 'pre_half_score_diff', 'runs_scored', 'did_pos_start']


@dataclass
class InningData:
    game_id: int = 0
    date: str = ''
    home_team: str = ''
    away_team: str = ''
    inning: int = 0
    is_top_inning: bool = False
    winning_team_is_batting: bool = False
    score_diff_before_half_inning: int = 0
    runs_socred: int = 0
    pos_started: bool = False

    def to_csv_row(self):
        """CSV row representation of this GameData object."""
        return [self.game_id, self.date, self.home_team, self.away_team, self.inning, self.is_top_inning,
                self.winning_team_is_batting, self.score_diff_before_half_inning, self.runs_socred,
                self.pos_started]


def parse_line(linescore, last_inning):
    away_score_after = {}
    home_score_after = {}

    lines = [line for line in linescore.splitlines()]
    header = lines[0]
    curr_inning, curr_inning_idx = 1, header.find('1')
    away_score, home_score = 0, 0

    while curr_inning <= last_inning:
        away_score += int(lines[1][curr_inning_idx:curr_inning_idx+2])
        home_score += int(lines[2][curr_inning_idx:curr_inning_idx+2])

        if curr_inning >= START_INNING:
            away_score_after[curr_inning] = away_score
            home_score_after[curr_inning] = home_score

        curr_inning_idx += 2
        curr_inning += 1

    return (home_score_after, away_score_after)


def getGames():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--days', type=int, default=30)
    parsed_args = parser.parse_args()

    now = datetime(2022, 11, 1)
    today = now.strftime('%m/%d/%Y')

    start = now - timedelta(days=parsed_args.days)
    start_date = start.strftime('%m/%d/%Y')

    return statsapi.schedule(start_date=start_date, end_date=today)


def getLinescore(game):
    # Only regular season games
    if game['game_type'] != 'R':
        return

    linescore = statsapi.linescore(game['game_id'])
    lock.acquire()
    games_and_linescores.append((game, linescore))
    lock.release()


def processGamesAndLinescores():
    for game_and_linescore in games_and_linescores:
        game = game_and_linescore[0]
        linescore = game_and_linescore[1]

        final_inning = game['current_inning']
        # Rain / postponed games
        if not final_inning or final_inning < 9:
            continue

        home_score_after, away_score_after = parse_line(
            linescore, final_inning)

        winner = ''
        if home_score_after[final_inning] > away_score_after[final_inning]:
            winner = 'Home'
        else:
            winner = 'Away'

        for inning in away_score_after.keys():
            # We start tracking the score one inning before we care to.
            if inning == START_INNING:
                continue
            # Is it a blowout when the away team comes to bat in inning
            score_diff_before_half_inning = abs(
                away_score_after[inning - 1] - home_score_after[inning - 1])
            if score_diff_before_half_inning >= RUN_THRESHOLD:
                runs_scored = away_score_after[inning] - \
                    away_score_after[inning - 1]
                innings[(game['game_id'], inning, True)] = InningData(game['game_id'], game['game_date'], game['home_name'], game['away_name'], inning,
                                                                      True, winner == 'Away', score_diff_before_half_inning, runs_scored)

        for inning in home_score_after.keys():
            # We start tracking the score one inning before we care to.
            if inning == START_INNING:
                continue
            # Is it a blowout when the home team comes to bat in inning
            score_diff_before_half_inning = abs(
                away_score_after[inning] - home_score_after[inning - 1])
            if score_diff_before_half_inning >= RUN_THRESHOLD:
                runs_scored = home_score_after[inning] - \
                    home_score_after[inning - 1]
                innings[(game['game_id'], inning, False)] = InningData(game['game_id'], game['game_date'], game['home_name'], game['away_name'], inning,
                                                                       False, winner == 'Home', score_diff_before_half_inning, runs_scored)


def getBoxscore(game_id):
    boxscore = statsapi.boxscore_data(game_id)
    lock.acquire()
    boxscores[game_id] = boxscore
    lock.release()


def processBoxscoreForInningsForPos():
    for (game_id, num_inning, is_top) in innings.keys():
        boxscore = boxscores[game_id]
        # If the other team didn't pos at all, we can skip this game.
        if not teamHasAnyPos(boxscore, is_top):
            continue
        # TODO(joshbaum): Process the boxscore to find out if the POS pitched in num_inning


def teamHasAnyPos(boxscore, is_top):
    pitcher_ids = boxscore['home' if is_top else 'away']['pitchers']
    for pitcher_id in pitcher_ids:
        if pitcher_id in pos_pitchers:
            return True
    return False


def outputInnings():
    with open('innings.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for inning in innings.values():
            writer.writerow(inning.to_csv_row())


def main():
    games = getGames()

    with ThreadPoolExecutor() as executor:
        for game in games:
            executor.submit(getLinescore, game)

    processGamesAndLinescores()

    with ThreadPoolExecutor() as executor:
        for (game_id, _, _) in innings.keys():
            executor.submit(getBoxscore, game_id)

    processBoxscoreForInningsForPos()

    outputInnings()


if __name__ == "__main__":
    main()