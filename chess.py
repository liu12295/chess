from bs4 import BeautifulSoup
import requests
import os, csv, json, re, sys
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
ctrl = {}
test = ""
#test = "chess.html"


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
    player = {
        "Name" : name,
        "Id" : id,
        "Events" : []
    }

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

        prev_games = len(player["Events"]);

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
                player["Events"].append(event)

        # We are done if no new entry is added
        new_games = len(player["Events"]) - prev_games;
        if new_games == 0 or test:
            break

        print player["Name"], ":", new_games, "games are imported from", url


    # Write data to chess.csv
    write2csv(player)
    
    return player

#
# Dump whatever we have got for this player
#
def dump(players, verbose = False):
    linestyles = ['rD', 'g^', 'bo', 'b*', 'y^', 'b^', 'ro']
    idx = 0
    plot_last_games = 8000

    for player in players:
        if player["Events"]:
            plot_last_games = min(len(player["Events"]), plot_last_games)
            
    for player in players:
        if not player["Events"]:
            continue
        
        print player["Name"], "(", player["Id"], ")", len(player["Events"]), "games"
        if verbose:
            for event in player["Events"]:
                print event["Date"], event["Score"]

        sys.stdout.flush()

        # Plot setup
        scores = [event["Score"] for event in player["Events"]][:plot_last_games]
        scores.reverse()
        games = range(len(scores))
        plt.plot(games, scores, linestyles[idx], label=player["Name"]+":"+player["Id"])

        idx += 1

    # Plot
    plt.legend(loc='lower right', shadow=True)
    plt.ylabel('Score')
    plt.xlabel('Game')
    plt.title("Most Recent " + str(plot_last_games) + " Games");
    plt.show()
    
    return

#
# Import events from file
#
def ImportPlayerHist(player):
    fname = player["Id"] + ".csv"
    if not os.path.isfile(fname):
        return False

    print "Import records from", fname

    with open(fname, 'rb') as f:
        r = csv.DictReader(f)
        for row in r:
            # Append a new entry
            player["Events"].append(row)
            
    return True

#
# Write data to chess_<id>.csv file for player
#
def write2csv(player):
    if not player["Name"] or not player["Events"]:
        return
    
    fname = player["Id"] + ".csv"
    print "Create", fname

    with open(fname, 'wb') as f:
        w = csv.DictWriter(f, player["Events"][0].keys())
        w.writeheader()
        for event in player["Events"]:
            w.writerow(event)

    return

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
    players.append(CollectPlayerHist(p["id"], p["name"]))


# Visualize the data
dump(players, verbose=False)

