from classes import * 
import db_setup

def version_updater():
    global status 
    global version 
    global champions

    status = Api()
    version = status.lol_version
    champions = status.champ_dict
    

version_updater()
#db_setup.db_setup()

# multithreading calls per region
#status.threading_region(status.player_list, status.region, "player list")
#status.threading_region(status.match_list, status.region, "match list")
#status.matches_fetch() #TODO: with multithreading
"""
playground
"""

#m = Match("EUW1_5934435453")
#print(m.data)
#champ = m.match_fetch()
#for c in champ:
#    print(c,c.get_name(status))

#db_setup.db_setup_only_champ()
#status.match_list()
status.matches_fetch()
