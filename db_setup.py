import pymongo
from pymongo import MongoClient
from classes import Api
from config import db

def champ_dict(champ_id,champ_name):
    c = {
        "_id": champ_id,
        "name":champ_name,
        "games":0,
        "build":{},
        "role":{"top":0,
                "mid":0,
                "jung":0,
                "supp":0,
                "adc":0},
        "runes":{},
        "summ":{},
        "skill":{},
        "starters":{}
    }
    return c


status = Api()
champ_list = status.get_champ_list()


db['champions'].drop()
db['europe'].drop()
db['asia'].drop()
db['america'].drop()


players = {
    "_id":"players",
    "values":[]
}
matches = {
    "_id":"matches",
    "fetched":[],
    "not-fetched":[],
    "discarded":[]      # not the right patch
}

for champ in champ_list.keys():
    db["champions"].insert_one(champ_dict(champ, champ_list[champ]))
db["europe"].insert_many([players,matches])
db["america"].insert_many([players,matches])
db["asia"].insert_many([players,matches])

""" Database layout
mydatabase
|-- champions
|   |-- [ id, name, games, build, role, runes, summ, skill, starters]
|-- europe
|   |-- players
|   |-- matches[ fetched, not-fetched, discarded ]
|-- asia
|   |-- players
|   |-- matches[ fetched, not-fetched, discarded ]
|-- america
|   |-- players
|   |-- matches[ fetched, not-fetched, discarded ]
"""

print("db setup done")