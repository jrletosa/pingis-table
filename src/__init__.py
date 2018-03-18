# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import pickle
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from models import Match, TeamStats, PlayerPosition
import contact_info

STANDINGS_URL = 'https://www.profixio.com/fx/serieoppsett.php?t=SBTF_SERIE_AVD9006&k=LS9006&p=1'

def parse_standings(soup):
    stats = []
    table = soup.find('table', id='tabell_std')
    rows = table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [e.text.strip() for e in cols]
        team = TeamStats(
            name=cols[0].split('.')[1],
            position=int(cols[0].split('.')[0]),
            wins=int(cols[2]),
            ties=int(cols[3]),
            loses=int(cols[4]),
            points=int(cols[8])
        )
        stats.append(team)

    return stats

def parse_matches(soup):
    matches = []
    table = soup.find(text='Omgång 1').find_parent('table')
    rows = table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [e.text.strip() for e in cols]
        if len(cols) > 10 and '-' in cols[8]:
            result = cols[8].strip()
            match = Match(
                team_a=cols[2],
                team_b=cols[4],
                score_a=result.split('-')[0],
                score_b=result.split('-')[1]
            )
            matches.append(match)

    return matches

def get_latest_stats():
    r  = requests.get(STANDINGS_URL)
    data = r.text
    soup = BeautifulSoup(data, "html.parser")

    standings = parse_standings(soup)
    matches = parse_matches(soup)
    return {
        'standings': standings,
        'matches': matches
    }

def read_current_stats(filename):
    infile = open(filename, 'rb')
    stats = []
    while True:
        try:
            stats.append(pickle.load(infile))
        except (EOFError, pickle.UnpicklingError):
            break
    infile.close()

    return stats

def get_current_stats():
    standings = read_current_stats('team-stats.pkl')
    matches = read_current_stats('match-stats.pkl')
    return {
        'standings': standings,
        'matches': matches,
    }

def get_current_ranking():
    infile = open('ranking.pkl', 'rb')
    ranking = None
    while True:
        try:
            ranking = pickle.load(infile)
        except (EOFError, pickle.UnpicklingError):
            break
    infile.close()

    return ranking

def notify_changes(current_stats, latest_stats):
    matches_diff = set(current_stats['matches']).symmetric_difference(latest_stats['matches'])

    r  = requests.get(STANDINGS_URL)
    data = r.text
    soup = BeautifulSoup(data, "html.parser")
    table = str(soup.find('table', id='tabell_std'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(contact_info.SOURCE_ADDRESS, contact_info.SOURCE_PASSWORD)

    new_matches = [m for m in matches_diff if m in latest_stats['matches']]
    latest_results = ''
    for match in new_matches:
        latest_results += '{} - {}: {} - {}\n'.format(
            match.team_a.encode('utf-8'), match.team_b.encode('utf-8'), match.score_a, match.score_b)

    msg_body = """
        <html>
          <head></head>
          <body>
          {}</br></br>
          <p>
            Latest results:
          </p></br>
          {}</br></br>
          <p>
            <a href="{}">See table</a>
          </p>
        </body>
        </html>
    """.format(table, latest_results, STANDINGS_URL)


    msg = MIMEMultipart('alternative')

    msg['Subject'] = 'A new match update is available!'
    msg['From'] = contact_info.SOURCE_ADDRESS
    msg['To'] = contact_info.DESTINATION_ADDRESS

    part = MIMEText(msg_body, 'html')
    msg.attach(part)
    server.sendmail(contact_info.SOURCE_ADDRESS, contact_info.DESTINATION_ADDRESS, msg.as_string())
    server.quit()

def notify_ranking_changes(latest_ranking):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(contact_info.SOURCE_ADDRESS, contact_info.SOURCE_PASSWORD)

    msg_body = """
        <html>
          <head></head>
          <body>
          <p>
            New ranking update:
          </p>
          <p>
            Position: {} ({})
          </p>
          <p>
            Points: {} ({})</br></br>
          <p>
            <a href="{}">See table</a>
          </p>
        </body>
        </html>
    """.format(
        latest_ranking.current_pos,
        latest_ranking.previous_pos,
        latest_ranking.points,
        latest_ranking.diff,
        latest_ranking.source_url)


    msg = MIMEMultipart('alternative')

    msg['Subject'] = 'A new ranking update is available!'
    msg['From'] = contact_info.SOURCE_ADDRESS
    msg['To'] = contact_info.DESTINATION_ADDRESS

    part = MIMEText(msg_body, 'html')
    msg.attach(part)
    server.sendmail(contact_info.SOURCE_ADDRESS, contact_info.DESTINATION_ADDRESS, msg.as_string())
    server.quit()

def save_latest_stats(stats):
    output = open('team-stats.pkl', 'wb')
    for team in stats['standings']:
        pickle.dump(team, output, pickle.HIGHEST_PROTOCOL)

    output = open('match-stats.pkl', 'wb')
    for match in stats['matches']:
        pickle.dump(match, output, pickle.HIGHEST_PROTOCOL)

def save_latest_ranking(ranking):
    output = open('ranking.pkl', 'wb')
    pickle.dump(ranking, output, pickle.HIGHEST_PROTOCOL)

def parse_ranking(soup, url):
    table = soup.find('table',{'class':'table table-condensed table-hover table-striped'})
    rows = table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [e.text.strip() for e in cols]
        name = cols[2]
        if name == contact_info.PLAYER_NAME:
            return PlayerPosition(
                name=name,
                previous_pos=cols[1][1:-1],
                current_pos=cols[0],
                points=cols[5],
                diff=cols[6][1:-1],
                url=url,
            )
    return None

def get_latest_ranking():
    url_prefix = 'https://www.profixio.com/fx/ranking_sbtf/ranking_sbtf_list.php?rid=256&from='
    position = 1
    ranking_url = url_prefix + str(position)
    r  = requests.get(ranking_url)
    data = r.text
    soup = BeautifulSoup(data, "html.parser")

    myself = parse_ranking(soup, ranking_url)
    while myself is None:
        if position > 7000:
            break

        position += 500
        ranking_url = url_prefix + str(position)
        r  = requests.get(ranking_url)
        data = r.text
        soup = BeautifulSoup(data, "html.parser")
        myself = parse_ranking(soup, ranking_url)

    return myself

def main():
    print('Checking for new updates...')

    current_stats = get_current_stats()
    latest_stats = get_latest_stats()
    difference = set(current_stats['standings']).symmetric_difference(latest_stats['standings'])
    if len(difference) > 0:
        notify_changes(current_stats, latest_stats)
        save_latest_stats(latest_stats)

    current_ranking = get_current_ranking()
    latest_ranking = get_latest_ranking()
    if current_ranking is None or \
            latest_ranking != current_ranking:

        notify_ranking_changes(latest_ranking)
        save_latest_ranking(latest_ranking)


if __name__ == "__main__":
    main()
