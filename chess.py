from bs4 import BeautifulSoup
import requests
import os, csv, json, re, sys
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
import random

ctrl = {}
test = ""
#test = "chess.html"

#
# Event class
#

class Event(object):
    def __init__(self, Date, Event, URL, Score) :
        self.Date = Date
        self.Event = Event
        self.URL = URL
        self.Score = Score

#
# Player class
#
class Player(object):
    def __init__(self, id, name):
        self.Id = id
        self.Name = name
        self.Events = []

    def num_events(self) :
        return len(self.Events);

    def has_no_event(self) :
        return not self.Events

    def has_any_event(self) :
        return not self.has_no_event()

    def ranking(self) :
        if not self.Events:
            return 0
        else:
            return self.Events[0].Score

    def add_event(self, event) :
        self.Events.append(event)
        return len(self.Events)
    
    #
    # Write data to chess_<id>.csv file for player
    #
    def write2csv(self) :
        if not self.Name or self.has_no_event():
            return
    
        fname = self.Id + ".csv"
        print "Create", fname

        with open(fname, 'wb') as f:
            keys = self.Events[0].__dict__.keys()
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for event in self.Events:
                w.writerow(event.__dict__)

        return

#
# Extract player's name
#
def ExtractPlayerName(tbl, id):
    if hasattr(tbl.b, 'get_text'):
        a = tbl.b.get_text().split(':')
        if a[0].strip() == id:
            return a[1].strip()
        
    return ""

#
# Extract game records from input table
#
def ExtractRecords(tbl):
    records = []
    tbody = tbl.tbody
    if hasattr(tbody, 'table'):
        if hasattr(tbody.table, "next_siblings"):
            for sibling in tbody.table.next_siblings:
                if hasattr(sibling, 'tbody'):
                    if hasattr(sibling.tbody, 'tr'):
                        records = sibling.tbody.tr.find_next_siblings()
    return records


#
# Scrape the web...
#
def CollectPlayerHist(id, name):
    player = Player(id=id, name=name);

    # If we have the record already, then import it
    # directly to save time
    if ImportPlayerHist(player):
        return player

    for page in range(1, 20):

        if test and os.path.isfile(test):
            soup = BeautifulSoup(open(test), 'html5lib');
        else:
            url = ctrl["baseURL"] + id + "." + str(page)
            print "Visit", url
            sys.stdout.flush()
            # If timeout due to firewall, use "export HTTP_PROXY=..." to make it work.
            html = requests.get(url).text
            soup = BeautifulSoup(html, 'html5lib');

        # Dump it to see the hierarchy
        # print soup.prettify(formatter=None).encode('utf-8')

        prev_games = player.num_events()

        for tbl in soup.find_all("table"):
            for record in ExtractRecords(tbl):
                fields = record.find_all('td');
                # Each record will have 5 columns/fields, namely:
                # fields[0] - End Date
                # fields[1] - Event Name
                # fields[2] - Reg Rtg Before / After
                # fields[3] - Quick Rtg
                # fields[4] - Blitz Rtg

                # Filter out invalid entry
                #pprint(vars(fields[0]), indent=3)
                if len(fields) != 5 or not fields[1].a or not fields[2].b :
                    continue;
                
                event = {}
                # Forget about unicode for the easy of eyeballs
                event["Date"] = fields[0].text.encode('utf-8').strip()[:10];
                event["Event"] = fields[1].text.encode('utf-8').strip();
                event["URL"] = fields[1].a.get("href").encode('utf-8').strip();
                try:
                    event["Score"] = int(fields[2].b.text);
                except ValueError:
                    continue

                # Append a new entry
                this_event = Event(event["Date"], event["Event"], event["URL"], event["Score"])
                player.add_event(this_event)

        # We are done if no new entry is added
        new_games = player.num_events() - prev_games;
        if new_games == 0 or test:
            break

        print player.Name, ":", new_games, "games are imported from", url

    # Write data to chess.csv
    player.write2csv()
    
    return player

#
# Dump whatever we have got for this player
#
def dump(players, verbose = False):
    markers = ['o', 'v', '^', '<', '>', '1', '2', '3', '4', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', '|', '_']
    mfc = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
    ls = ['solid', 'dashed', 'dashdot', 'dotted']
    plot_last_games = 8000

    for player in players:
        if player.has_any_event():
            plot_last_games = min(player.num_events(), plot_last_games)


    # Sort players according to their latest ranking in descending order
    sorted_players = sorted(players, key=lambda player: player.ranking(), reverse=True)
    
    for player in sorted_players:
        if player.has_no_event():
            continue
        
        print player.Name, ":", "id", player.Id, "games", player.num_events(), "ranking", player.ranking()
        if verbose:
            for event in player.Events:
                print event.Date, event.Score

        sys.stdout.flush()

        # Plot setup
        scores = [event.Score for event in player.Events[:plot_last_games]]
        scores.reverse()
        games = range(len(scores))
        plt.plot(games, scores, ls=random.choice(ls), marker=random.choice(markers), markerfacecolor=random.choice(mfc), label=player.Name+":"+str(player.ranking()))

    # Plot
    plt.tick_params(axis='y', which='both', labelleft='on', labelright='on')
    plt.grid(b=True, which='both', color='0.65',linestyle='-')    
    plt.legend(loc='lower right', shadow=True)
    plt.ylabel('Ranking')
    plt.xlabel('Game')
    plt.title("Most Recent " + str(plot_last_games) + " Games");
    plt.show()
    
    return

#
# Import events from file
#
def ImportPlayerHist(player):
    fname = player.Id + ".csv"
    if not os.path.isfile(fname):
        return False

    with open(fname, 'rb') as f:
        r = csv.DictReader(f)
        for row in r:
            # Append a new entry
            this_event = Event(row["Date"], row["Event"], row["URL"], row["Score"])
            player.add_event(this_event)

    print player.Name, ":", player.num_events(), "games are imported from", fname
    return True

#
# main
#

players = []

try:
    with open('chess.json') as f:
        ctrl = json.load(f);
except IOError as e:
    sys.exit( "I/O error({0}): {1}".format(e.errno, e.strerror) + ": chess.json")

for p in ctrl["players"]:
    if not p["id"].startswith('-'):
        players.append(CollectPlayerHist(p["id"], p["name"]))
    else:
        print "Player", p['name'], "is skipped"


# Visualize the data
dump(players, verbose=False)

