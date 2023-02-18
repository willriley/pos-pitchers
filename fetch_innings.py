from concurrent.futures import ThreadPoolExecutor
import statsapi
import argparse
import pprint
from datetime import datetime, timedelta
from dataclasses import dataclass
import csv
from threading import Lock

# GLOBAL VARIABLES
innings = []
games_and_linescores = []
lock = Lock()
pos_pitchers = set([593643, 665019, 670768, 642165, 608348, 624503, 621433, 542194, 643524, 596117,
                    571976, 605612, 543281, 641914, 670712, 425877, 644374, 676391, 620443, 621011,
                    660636, 664670, 572191, 606993, 642851, 663630, 444876, 592743, 665155, 518586,
                    573131, 608703, 676946, 405395, 506702, 570560, 622268, 670032, 553902, 572008,
                    572816, 593160, 605170, 641531, 543829, 608686, 608700, 640461, 645801, 545121,
                    545341, 594838, 598265, 606115, 607054, 622569, 624512, 668800, 501303, 650339,
                    661531, 669742, 503556, 571466, 614177])

START_INNING = 7
RUN_THRESHOLD = 8
CSV_HEADERS = ['date', 'home', 'away', 'inning', 'is_top',
               'is_winning_team_batting', 'pre_half_score_diff', 'runs_scored', 'did_pos_start']


@dataclass
class InningData:
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

        return [self.date, self.home_team, self.away_team, self.inning, self.is_top_inning,
                self.winning_team_is_batting, self.score_diff_before_half_inning, self.runs_socred,
                self.pos_started]


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
    if game['game_type'] != 'R':
        # Only regular season games
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

        # TODO(joshbaum): Did POS start the inning pitching?

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
                innings.append(InningData(game['game_date'], game['home_name'], game['away_name'], inning,
                                          True, winner == 'Away', score_diff_before_half_inning, runs_scored))

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
                innings.append(InningData(game['game_date'], game['home_name'], game['away_name'], inning,
                                          False, winner == 'Home', score_diff_before_half_inning, runs_scored))


def writeInnings():
    with open('innings.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for inning in innings:
            writer.writerow(inning.to_csv_row())


def main():
    games = getGames()
    with ThreadPoolExecutor() as executor:
        for game in games:
            executor.submit(getLinescore, game)
    processGamesAndLinescores()
    writeInnings()


if __name__ == "__main__":
    main()
