from classes import * 

def version_updater():
    global status 
    global version 
    global champions

    status = Api()
    version = status.lol_version
    champions = status.champ_dict
    

version_updater()


m = Match("KR_5964220985",server="asia")
#print(m.data)
champ = m.match_fetch()[0]
print(champ,champ.get_name(status))


# multithreading calls per region
# status.threading_list(status.player_region, status.region)
