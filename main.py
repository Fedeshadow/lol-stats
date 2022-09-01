from classes import * 
import db_setup

def version_updater():
    global status 
    global version 
    global champions

    status = Api()
    version = status.lol_version
    champions = status.champ_dict
    
if __name__ == "__main__":
    version_updater()
    db_setup.db_setup()

    # multithreading calls per region
    status.threading_region(status.player_list, status.region, "player list")
    status.threading_region(status.match_list, status.region, "match list")
    status.threading_region(status.matches_fetch, status.region, "matches analysis")
    for l in status.languages:
        status.result_maker(l)
        print(f"{l} results json created")
