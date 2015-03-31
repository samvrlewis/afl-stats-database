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

session = requests.session()

headers = {"Accept" : "application/json, text/javascript", 
			"Accept-Encoding" : "gzip, deflate, sdch", 
			"Connection" : "keep-alive",
			"Referer" : "http://www.afl.com.au/stat",
			"Host" : "www.afl.com.au",
			"User-Agent" : "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
			"X-Requested-With": "XMLHttpRequest", 
			"X-media-mis-token" : "1ad4456de8b7110699ff63f25e6194d0"}

query_string = "http://www.afl.com.au/api/cfs/afl/statsCentre/teams?competitionId=CD_S2014014&roundId=CD_R201401401&matchId=CD_M20140140101"
response = session.get(query_string, headers=headers)
match_json = respon.json()

collingwood_stats = response.json()['lists'][0]
freo_stats = response.json()['lists'][1]

#find number of freo centre clearances -- cool!!
print freo_stats['stats']['totals']['clearances']['stoppageClearances']
