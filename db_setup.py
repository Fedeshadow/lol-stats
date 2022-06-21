import pymongo
from pymongo import MongoClient
from classes import Api
from config import db

# scrivi delle funzioni in maniera tale da poter scegliere come eliminare i dati

global status
global champ_list

status = Api()
champ_list = status.get_champ_list()


def champ_dict(champ_id,champ_name):
    c = {
        "_id": champ_id,
        "name":champ_name,
        "games":0,
        "wins":0,
        "build":{},
        "role":{"top":0,
                "middle":0,
                "jungle":0,
                "utility":0,
                "bottom":0},
        "runes":{},
        "summ":{},
        "skill":{},
        "starters":{}
    }
    return c

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
|-- americas
|   |-- players
|   |-- matches[ fetched, not-fetched, discarded ]
"""

def db_setup():
    db['champions'].drop()
    db['europe'].drop()
    db['asia'].drop()
    db['americas'].drop()


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
    db["americas"].insert_many([players,matches])
    db["asia"].insert_many([players,matches])
    print("db setup done")


def db_setup_no_player():
    """
    does not drop player db
    """
    db['champions'].drop()
    db['europe'].delete_one({"_id":"matches"})
    db['asia'].delete_one({"_id":"matches"})
    db['americas'].delete_one({"_id":"matches"})

    matches = {
        "_id":"matches",
        "fetched":[],
        "not-fetched":[],
        "discarded":[]      # not the right patch
    }

    for champ in champ_list.keys():
        db["champions"].insert_one(champ_dict(champ, champ_list[champ]))
    db["europe"].insert_one(matches)
    db["americas"].insert_one(matches)
    db["asia"].insert_one(matches)
    print("db setup without deleting players done")

def db_setup_only_champ():
    db['champions'].drop()
    for champ in champ_list.keys():
        db["champions"].insert_one(champ_dict(champ, champ_list[champ]))