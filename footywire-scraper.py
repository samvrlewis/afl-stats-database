import urllib2
import re
from bs4 import BeautifulSoup
import requests
import sqlite3 as sql
from dateutil import parser
import sys
import time
import matplotlib.pyplot as plt
import numpy as np

stats = ['Kicks', 'Handballs', 'Disposals', 'Marks',
        'Tackles', 'Hitouts', 'Frees For', 'Frees Against',
        'Goals Kicked', 'Behinds Kicked', 'Rushed Behinds',
        'Scoring Shots', 'Inside 50s',
        '% In50s Score', '% In50s Goal']
        
statsToSql = {'Kicks': 'kicks', 'Handballs' : 'handballs', 'Disposals' : 'disposals', 'Marks' : 'marks',
        'Tackles': 'tackles', 'Hitouts': 'hitouts', 'Frees For' : 'frees_for', 'Frees Against' : 'frees_against',
        'Goals Kicked' : 'goals_kicked', 'Behinds Kicked' : 'behinds_kicked', 'Rushed Behinds': 'behinds_rushed',
        'Scoring Shots' : 'scoring_shots', 'Inside 50s' : 'inside_50s',
        '% In50s Score' : 'in50s_score',  '% In50s Goal': 'in50s_goal'}

                
start_time = time.mktime(time.gmtime()) 

def update_progress(progress, max_time, starting_time=start_time):
    """ Pretty prints a progress bar """
    
    percent = float(progress)/float(max_time)
    int_percent = int(percent*100)
    elapsed_min = (time.mktime(time.gmtime())-starting_time)/60.0
    if percent > 0:
        eta_min = int(round(elapsed_min/percent))
    else:
        eta_min = '?'
    sys.stdout.write( '\r[{0}{2}] {1}% ({3}) Elapsed:{4}min ETA:{5}min'.format('#'*(int_percent), int_percent,' '*(100-(int_percent)), progress, int(elapsed_min), eta_min))
    sys.stdout.flush()


class Footywire_Scraper:
    def __init__(self):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Referer":"http://www.google.com.au","Cache-Control":"max-age=0"}
        self.baseURL = "http://www.footywire.com/afl/footy/ft_match_statistics?mid="
        
    def remove_long_names(self, team_str):
        """Avoid having to deal with two word names by converting them all to one word"""
        long_names = {'Western Bulldogs': 'Bulldogs', 'West Coast': 'Eagles',
                      'St Kilda': 'Saints', 'North Melbourne' : 'North',
                      'Port Adelaide': 'Port', 'Gold Coast' : 'Suns'}
                      
        for key in long_names:
            team_str = team_str.replace(key, long_names[key])
            
        return team_str
        
    def get_games(self, start_game_id, end_game_id):
        """
        Returns a list of games from start_game_id to end_game_id (inclusive)
        
        Can get the game ids from here: http://www.footywire.com/afl/footy/ft_match_list
        """
        games = []
        
        num_games = end_game_id - start_game_id + 1
        
        for game_id in range(start_game_id, end_game_id + 1):
            try:
                game = self.get_game(game_id)
                games.append(game)
            except:
                print 'game_id =', game_id, 'failed'
                
            time.sleep(0.4)
            
            update_progress(game_id - start_game_id + 1, num_games)
        
        return games
        
    def get_game(self, game_id):
        """Parses footywire HTML to get an individual game"""
        
        session = requests.session()
        response = session.get(self.baseURL + str(game_id), headers=self.headers)
        soup = BeautifulSoup(response.text)
        
        #get teams
        defeated_by = False 
        game_header = soup.find_all(text=re.compile('defeats'))
        
        if len(game_header) == 0:
            game_header = soup.find_all(text=re.compile('defeated by'))
                            
            if (len(game_header)) == 0:
                game_header = soup.find_all(text=re.compile('defeat'))
                
                if (len(game_header)) == 0:
                    game_header = soup.find_all(text=re.compile('drew'))
                    defeated_by = True 
            else:
                defeated_by = True   

        if defeated_by: 
            teams = self.remove_long_names(game_header[1]).replace('\n', '')
            home_team = teams.split(' ')[0]
            away_team = teams.split(' ')[3]
        else:
            teams = self.remove_long_names(game_header[1]).replace('\n', '')
            home_team = teams.split(' ')[0]
            away_team = teams.split(' ')[2]
        
        date_string = game_header[0].split(' ')
        date_string_find = [date.lower() for date in date_string]
        
        venue = date_string[date_string_find.index('at') + 1]
        
        #get round
        round_num = None
        
        try:
            date_string_find.remove('')
        except:
            pass
        
        try:
            round_num = int(date_string[date_string_find.index('round') + 1])
        except:
            try:
                round_num = date_string_find[date_string_find.index('final') - 1] + ' final'
            except:
                round_num = date_string_find[date_string_find.index('semi-final')]
            
        date = date_string[-3:]
        date = ' '.join(date)  
        date = parser.parse(date)
        
        #get attendance
        attend = soup.find_all(text=re.compile('Attendance'))
        attendance = 0
        
        if (len(attend) > 3):
            attendance = int(attend[1].split(' ')[-1])
        
        #get stats       
        away_stats = {}
        home_stats = {}
                
        for stat in stats:
            stat_row = soup.find_all('td', text=stat)[0].find_parent('tr')
            elements = stat_row.find_all('td')
            
            if elements[0].text == '-':
                home_stats[stat] = None
            else:
                home_stats[stat] = elements[0].text
            
            if elements[0].text == '-':
                away_stats[stat] = None
            else:
                away_stats[stat] = elements[2].text
                
        return Game(game_id, home_team, away_team, venue, round_num, date, attendance, home_stats, away_stats)
        
class Game:
    def __init__(self, game_id, home_team, away_team, venue, round_num, date, attendance, home_stats, away_stats):
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.venue = venue
        self.round_num = round_num
        self.date = date
        self.attendance = attendance
        self.home_stats = home_stats
        self.away_stats = away_stats
    
class ConnectionManager:
    def __init__(self, sqlString):
        self.con = sql.connect(sqlString)
        self.con.row_factory = sql.Row
        self.teams = self.get_teams()
        self.venues = self.get_venues()
    
    def commit_games_to_db(self, games):
        """ Commits list of games to DB """
        print ' '
        
        num_games = len(games)
        game_num = 0
        
        for game in games:
            update_progress(game_num, num_games)
            game_num += 1
            self.add_game(game)
            self.add_stats(game)
        
    def get_teams(self):
        teams = {}
        
        with self.con:
            
            cursor = self.con.cursor()
            cursor.execute("SELECT * FROM teams")

            rows = cursor.fetchall()
            
            for row in rows:
                teams[row['team_name']] = row['team_id']
                
        return teams
        
    def get_venues(self):
        
        venues = {}
        
        with self.con:
            cursor = self.con.cursor()
            cursor.execute("SELECT * FROM venues")

            rows = cursor.fetchall()
            
            for row in rows:
                venues[row['venue_name']] = row['venue_id']
                
        return venues
        
    def add_team(self, team_name):
        
        if (team_name in self.teams):
            raise NameError(team_name + " already in DB")
        
        with self.con:
            cursor = self.con.cursor()
            cursor.execute("INSERT INTO teams(team_name) VALUES(?)", [team_name])
            
            self.teams[team_name] = cursor.lastrowid

    def add_venue(self, venue_name):
        if (venue_name in self.venues):
            raise NameError(venue_name + " already in DB")
        
        with self.con:
            cursor = self.con.cursor()
            cursor.execute("INSERT INTO venues(venue_name) VALUES(?)", [venue_name])
            
            self.venues[venue_name] = cursor.lastrowid
            
    def add_game(self, game):
        if game.home_team not in self.teams:
            self.add_team(game.home_team)
        
        if game.away_team not in self.teams:
            self.add_team(game.away_team)
            
        if game.venue not in self.venues:
            self.add_venue(game.venue)
        
        with self.con:
            cursor = self.con.cursor()
            
            queryString = "INSERT INTO games(game_id, date, round, home_team_id, away_team_id, venue_id, attendance) "
            queryString += "VALUES(?, ?, ?, ?, ?, ?, ?)"
            
            homeID = self.teams[game.home_team]
            awayID = self.teams[game.away_team]
            venueID = self.venues[game.venue]
            
            values = [game.game_id, game.date, game.round_num, homeID, awayID, venueID, game.attendance]
            
            cursor.execute(queryString, values)
 
    def add_stats(self, game):
        """Assumes game already been inserted"""
        with self.con:
            cursor = self.con.cursor()
            queryString = "INSERT INTO stats(game_id, team_id"
            homeValueString = " VALUES(?, ?"
            awayValueString = homeValueString
            
            homeValues = [game.game_id, self.teams[game.home_team]]
            awayValues = [game.game_id, self.teams[game.away_team]]
            
            for key in game.home_stats:

                queryString += ', '
                awayValueString += ', '
                homeValueString += ', '
                    
                homeValueString += '?'
                awayValueString += '?'
                
                homeValues.append(game.home_stats[key])
                awayValues.append(game.away_stats[key])
                    
                queryString += statsToSql[key]
                           
            queryString += ')'
            homeValueString += ')' 
            awayValueString += ')'
            
            
            cursor.execute(queryString + homeValueString, homeValues)
            cursor.execute(queryString + awayValueString, awayValues)
            

scraper = Footywire_Scraper()
games = scraper.get_games(5820, 5963)
con = ConnectionManager('C:\\Users\\Sam\\Dropbox\\Programming projects\\afl_stats\\AFL_games.sqlite')
con.commit_games_to_db(games)
