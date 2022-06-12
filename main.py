from classes import * 

def version_updater():
    global status 
    status = Api()
    global version 
    version = status.lol_version

version_updater()

#m = Match("EUW1_5915462428")
#print(m.match_fetch()[0])