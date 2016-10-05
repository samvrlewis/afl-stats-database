"""
Some code to get the JSON from the AFL.com.au stats api

I found the header info by using the developer tools in Chrome:
	- Visit http://www.afl.com.au/stats
	- Open developer tools
	- Change to network tab
	- Add a filter for 'XHR'
	- Change season to 2014, round to round 1 and match to collingwood vs freo
	- There should be a GET request in the developer tools log
	- Can examine the request to see the request headers, cookies etc

It only seems to work if the X-media-mis-token header is included, I'm not sure how this is generated
I'm also not sure how the query string is generated but this could probably be found by looking at a few different requests
and looking for the pattern

competitionId I would guess is constant
roundId and matchId might just be the date + game number or something?
"""
import requests
from bs4 import BeautifulSoup
import collections
import sqlite3 as sql

def flatten(d):
    items = []
    for k, v in d.items():
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v).items())
        else:
            items.append((k, v))
    return dict(items)


class aflcomau_scraper:

    
    def __init__(self):
        self.session = requests.session()
        self.token = self.get_token(self.session)
    
    def get_token(self, session):
        TOKEN_URL = 'http://www.afl.com.au/api/cfs/afl/WMCTok'
        response = session.post(TOKEN_URL)
        return response.json()['token']

    def get_season_ids(self):
        stats_url = 'http://www.afl.com.au/afl/stats'
        response = self.session.get(stats_url)
        soup = BeautifulSoup(response.content)
        season_dropdown = soup.find('select', {'id' : 'selTeamSeason'})
        season_ids = [option['value'] for option in season_dropdown.find_all('option')]
        return season_ids

    def get_round_ids(self, season_id):
        rounds = []
        headers = {'X-media-mis-token': self.token}
        response = self.session.get('http://www.afl.com.au/api/cfs/afl/season?seasonId=' + season_id, headers=headers)
        json = response.json()
        for round_json in json['season']['competitions'][0]['rounds']:
            rounds.append((round_json['roundId'], round_json['roundNumber'], round_json['year']))
    
        return rounds

    def get_games(self, season_id, round_id):
        games = []
        headers = {'X-media-mis-token': self.token}
    
        response = self.session.get('http://www.afl.com.au/api/cfs/afl/matchItems/round/' + round_id[0], headers=headers)
        json = response.json()
    
        for game_json in json['items']:
            match_id = game_json['match']['matchId']
    
            stats = self.session.get('http://www.afl.com.au/api/cfs/afl/statsCentre/teams?competitionId=' + season_id +
                                '&roundId=' + round_id[0] + '&matchId=' + match_id, headers=headers)
    
            stats_json = stats.json()
    
            games.append([game_json, stats_json])
    
        return games


def get_table_rows(game):
    table_rows = {}
    
    table_rows['matches'] = get_match_row(game)
    table_rows['weather'] = get_weather_row(game)
    table_rows['scores'] = get_score_rows(game)
    table_rows['stats'] = get_stats_rows(game)
    
    return table_rows

def get_match_row(game):
    row = {}
    
    row['matchId'] = game[0]['match']['matchId']
    row['roundId'] = game[0]['match']['round']
    row['venueId'] = game[0]['venue']['venueId']
    row['awayTeamId'] = game[0]['match']['awayTeam']['teamId']
    row['homeTeamId'] = game[0]['match']['homeTeam']['teamId']
    row['localStartTime'] = game[0]['match']['venueLocalStartTime']
    
    return row
    
def get_weather_row(game):
    try:
        row = game[0]['score']['weather']
    except:
        return None
    
    row['matchId'] = game[0]['match']['matchId']
    
    return row


def get_score_rows(game):
    team_names = [('awayTeamScore', 'awayTeamScoreChart'),
                  ('homeTeamScore', 'homeTeamScoreChart')]
    
    score = game[0]['score']
    rows = []
    
    for team in team_names:
        row = {}
        
        if 'away' in team[0]:  
            row['teamId'] = game[0]['match']['awayTeam']['teamId']
        else:
            row['teamId'] = game[0]['match']['homeTeam']['teamId']
            
        row['matchId'] = game[0]['match']['matchId']
        row['behinds'] = score[team[0]]['matchScore']['behinds']
        row['goals'] = score[team[0]]['matchScore']['goals']
        row['minutesInFront'] = score[team[0]]['minutesInFront']
        row['rushedBehinds'] = score[team[0]]['rushedBehinds']
       
        row['q1Behinds'] = score[team[0]]['periodScore'][0]['score']['behinds']
        row['q1Goals'] = score[team[0]]['periodScore'][0]['score']['goals']
        row['q2Behinds'] = score[team[0]]['periodScore'][1]['score']['behinds']
        row['q2Goals'] = score[team[0]]['periodScore'][1]['score']['goals']
        row['q3Behinds'] = score[team[0]]['periodScore'][2]['score']['behinds']
        row['q3Goals'] = score[team[0]]['periodScore'][2]['score']['goals']
        row['q4Behinds'] = score[team[0]]['periodScore'][3]['score']['behinds']
        row['q4Goals'] = score[team[0]]['periodScore'][3]['score']['goals']
        
        try:
            row['leftBehinds'] = score[team[1]]['leftBehinds']
            row['rightBehinds'] = score[team[1]]['rightBehinds']
            row['rightPosters'] = score[team[1]]['rightPosters']
            row['leftPosters'] = score[team[1]]['leftPosters']
            row['touchedBehinds'] = score[team[1]]['touchedBehinds']
        except:
            row['leftBehinds'] = None
            row['rightBehinds'] = None
            row['rightPosters'] = None
            row['leftPosters'] = None
            row['touchedBehinds'] = None
        
        rows.append(row)
    
    return rows

def get_stats_rows(game):
    lists = game[1]['lists']
    rows = []
    
    for team_list in lists:
        row = flatten(team_list['stats']['totals'])
        row['teamId'] = team_list['team']['teamId']
        row['matchId'] = game[0]['match']['matchId']
        
        if 'interchangeCounts' in row and row['interchangeCounts'] == None:
            row.pop('interchangeCounts', None)
            
        rows.append(row)
    
    return rows
    
def insert_into_db(table_name, dic, cursor):
    keys, values = zip(*dic.items())
    insert_str =   "INSERT INTO " + table_name + " (%s) values (%s)" % (",".join(keys),",".join(['?']*len(keys)))
    cursor.execute(insert_str,values)
    
    
def insert_game_into_db(game, con):
    tbl_rows = get_table_rows(game)
            
    with con:
        cursor = con.cursor()
        
        for key in tbl_rows:
            rows = tbl_rows[key]
        
            if type(rows) != list:
                rows = [rows]
                
            for row in rows:
                if row is not None:
                    insert_into_db(key, row, cursor)

def is_number(s):
    if s is None:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


scraper = aflcomau_scraper()
seasons = scraper.get_season_ids()
rounds = scraper.get_round_ids(seasons[1])
con = sql.connect('aflcomauStats.sqlite')

with con:
    cursor = con.cursor()
    cursor.execute("SELECT matchId from matches")
    rows = cursor.fetchall()
    
matchIds = [row[0] for row in rows]

with con:
    cursor = con.cursor()
    cursor.execute("SELECT roundId, COUNT(*) AS num FROM matches GROUP BY roundId")
    rows = cursor.fetchall()

skipRounds = [row[0] for row in rows if row[1] == 9]

for season in seasons:
    rounds = scraper.get_round_ids(season)
    
    for roundd in rounds:
        if (roundd[0] in skipRounds):
            print "Skipped round:" + roundd[0]
            continue
            
        games = scraper.get_games(season, roundd)
        
        for game in games:
            matchId = game[0]['match']['matchId']
            
            if (matchId not in matchIds and matchId != "CD_M20110140207"):
                insert_game_into_db(game, con)
                print "Inserted " + matchId 
            else:
                print "Skipped match:" + matchIdhhhh
