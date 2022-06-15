from classes import * 

def version_updater():
    global status 
    global version 
    global champions

    status = Api()
    version = status.lol_version
    champions = status.champ_dict
    

version_updater()

#print(status.champ_dict)
#m = Match("EUW1_5915462428")
#champ = m.match_fetch()[0]
#print(champ,champ.get_name(status))

print(status.player_list())