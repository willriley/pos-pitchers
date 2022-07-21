import smtplib, ssl, time
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import statsapi

SLEEP_TIME = 60
RUN_THRESHOLD = 8
INNING_THRESHOLD = 6
SMTP_PORT = 587
SMTP_SERVER = 'smtp.gmail.com'
SENDER_EMAIL = 'pospitchers@gmail.com'
EMAILS = ['wmr12198@gmail.com', 'joshbaum98@gmail.com', 'jake.ryan.sokol@gmail.com']

def parse_game(game):
    return {
        'home_team': game['home_name'],
        'home_score': game['home_score'],
        'away_team': game['away_name'],
        'away_score': game['away_score'],
        'inning': int(game['current_inning']) if game['current_inning'] else 0
    }

def is_blowout(game):
    return (game['inning'] >= INNING_THRESHOLD
            and abs(game['home_score'] - game['away_score']) >= RUN_THRESHOLD)

def send_email(game):
    password = 'ufzfqtyatptkwsny'

    raw_msg = f"""\
    {game['home_team']} {game['home_score']}
    {game['away_team']} {game['away_score']}
    Inning: {game['inning']}"""
    msg = MIMEText(raw_msg)
    msg['Subject'] = f"Blowout Alert: {game['home_team']} vs {game['away_team']}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = ', '.join(EMAILS)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER) as server:
        server.starttls(context=context)
        server.login(SENDER_EMAIL, password)
        server.sendmail(SENDER_EMAIL, EMAILS, msg.as_string())


already_notified_games = set()
already_notified_reset_date = datetime.now() + timedelta(days=1)

while True:
    dt = datetime.now() - timedelta(days=4)
    today = dt.strftime('%m/%d/%Y')

    games_today = statsapi.schedule(start_date=today, end_date=today)
    for g in games_today:
        # TODO: change to 'status' == 'Live'
        if g['status'] != 'Final' and g['game_id'] not in already_notified_games:
            game = parse_game(g)
            if is_blowout(game):
                already_notified_games.add(g['game_id'])
                send_email(game)

    if dt > already_notified_reset_date:
        already_notified_games.clear()
        already_notified_reset_date = datetime.now() + timedelta(days=1)

    time.sleep(SLEEP_TIME)
