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

"""
playground
"""
#m = Match("KR_5964220985",server="asia")
#print(m.data)
#champ = m.match_fetch()[0]
#print(champ,champ.get_name(status))

db['champions'].drop()

