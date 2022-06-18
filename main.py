from classes import * 
import os

def version_updater():
    global status 
    global version 
    global champions

    status = Api()
    version = status.lol_version
    champions = status.champ_dict
    

version_updater()

import db_setup     # database setup

# multithreading calls per region
#status.threading_region(status.player_list, status.region)

"""
playground
"""
#m = Match("KR_5964220985",server="asia")
#print(m.data)
#champ = m.match_fetch()[0]
#print(champ,champ.get_name(status))

try:
    status.threading_region(status.player_list, status.region, "player list")
except Exception as e:
    print(e)