import requests as rq
from config import key
from config import db
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, wait

class Utils:
    
    def request(self,url:str,use_case:str):
        req = rq.get(url)
        if req.status_code == 429:
            time.sleep(125)
            print(f"key limit exeeded in {use_case}, sleeping 130s")
            req = rq.get(url)
        if req.status_code == 403:
            print(f"key expired while {use_case}")
            quit()
        return req.json()
    
    def threading_region(self, func ,iterable:list, use_case:str):
        print(f"{use_case} started")
        t1 = time.time()
        with ThreadPoolExecutor() as executor:
            executor.map(func, iterable)
        t2 = time.time()
        print(f"{use_case} completed in {t2-t1} seconds")
    
    def convert_region(self,reg):
        if reg == "euw1":
            region = "europe"
        elif reg == "kr":
            region = "asia"
        elif reg == "na1":
            region = "americas"
        return region
        
class Api(Utils):
    def __init__(self):
        self.lol_version = self.get_lol_version()
        self.key = key
        self.champ_dict = self.get_champ_list()
        self.tier = ["PLATINUM","DIAMOND"]
        self.div = ["I","II","III","IV"]
        self.region = ["euw1","kr","na1"]

    def get_lol_version(self):
        return rq.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
    
    def item_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/item.json"
    
    def champ_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/champion.json"
    
    def rune_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/runesReforged.json"
    
    def summ_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/summoner.json"
    
    def player_url(self,region,tier,div, page):
        return f"https://{region}.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{div}?page={page}&api_key={self.key}"

    def get_boots_list(self):
        raw = rq.get(self.item_url()).json()
        boots = []
        for item in raw["data"].keys():
            if "Boots" in raw["data"][item]["tags"]:
                boots.append(item)
        return boots

    def get_champ_list(self) -> dict:
        d = {}
        raw = rq.get(self.champ_url()).json()
        for champ in raw["data"]:
            id, name = raw["data"][champ]["key"],raw["data"][champ]["name"]
            d[id] = name
        return d
    
    def player_list(self,region="euw1",limited=False,*args,**kwargs):
        for tier in self.tier:
            for div in self.div:
                for page in range(1,3):
                    url = self.player_url(region, tier, div, page)
                    player_list = self.request(url, f"player list region: {region}")

                    for p in player_list:
                        if not p["inactive"]:
                            player = Player(p["summonerId"],region)
                            player.insert()  

    
    def match_list(self,reg="euw1",*args,**kwargs):
        region = self.convert_region(reg)

        players = db[region].find_one({"_id":"players"})["values"]
        for p in players:
            player = Player(p[0],reg,p[1],p[2])
            player.insert_match_list()                        


class Player(Utils):
    def __init__(self,summoner_id,region,account_id=None,puuid=None):
        self.region = region
        self.summoner_id = summoner_id
        if account_id is None:
            self.account_id, self.puuid = self.get_account_id()
        else:
            self.account_id, self.puuid = account_id, puuid

    def get_account_id(self):
        url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/{self.summoner_id}?api_key={key}"
        data = self.request(url, f"account id region: {self.region}")
        return data["accountId"], data["puuid"]

    def insert(self):
        region = self.convert_region(self.region)

        # tuple with (summ_id, acc_id, puuid)
        db[region].update_one({"_id":"players"}, {"$push":{"values":(self.account_id,self.account_id,self.puuid)}})

    def insert_match_list(self):      # 10 games per player
        region = self.convert_region(self.region)
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puuid}/ids?type=ranked&start=0&count=10&api_key={key}"
        data = self.request(url, f"match list from player in region {region}")
        for m_id in data:
            db[region].update_one({"_id":"matches"},{"$push":{"not-fetched":m_id}})
        


class Item:
    def __init__(self,_id):
        self.id = _id
        #self.name = get_name()
    
    def get_name(self,language="en_US"):
        #TODO: prevedere il supporto alle lingue?
        pass

    def isTrinket(self):
        pass
    
    def isBoot(self): 
        pass

class Champion:
    def __init__(self, _id,role=None, win=None, build=None, runes=None, \
        stat_runes=None ,summ=None, skill_order=None, starters=None):
        
        self.role = role
        self.id = _id
        self.build = build
        self.runes = runes
        self.summ = summ
        self.win = win
        self.skill_order = skill_order
        self.starters = starters
    
    def __str__(self):
        return str(self.__dict__)
    
    def __repr__(self):
        return str(self.__dict__)    

    def get_name(self,status:Api):
        """
        takes the status as argument and returns the name
        """
        return status.champ_dict[str(self.id)]
    
    def add_win(self): #aggiungi una win 
        #TODO: aggiungi implementazione db
        pass
    def add_game(self): # +1 ai game
        #TODO: aggiungi implementazione db
        pass

    def add_item(self): #aggiungi la lista degli itmes
        #TODO: aggiungi implementazione db
        pass

class Rune:
    def __init__(self, _id):
        self.id = _id
        #self.name = get_name()

    def get_name(self,language="en_US"):
        pass

class Match(Utils):
    def __init__(self,match_id,server="europe"):
        self.id = match_id
        self.url = f"https://{server}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={key}"
        self.data = self.request(self.url, "match data")
        self.timeline_url = f"https://{server}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={key}"
        self.timeline = self.request(self.timeline_url, "timeline data")

    def check_version(self,version):
        v = "".join([i for i in version.split(".")[:2]])   # exctract current patch
        m_v = "".join([i for i in self.data["info"]["gameVersion"].split(".")[:2]])   # exctratct game patch
        if v != m_v:
            return False
        return True
    
    def add_match(self):
        #TODO: aggiungi implementazione db che aggiunge l'id alla lista 
        # di quelli buoni
        pass

    # returns the list of Champions
    def match_fetch(self) -> list:   
        champ_list = []
        for p in range(10):
            champ = self.data["info"]["participants"][p]["championId"]
            win = self.data["info"]["participants"][p]["win"]
            build = [self.data["info"]["participants"][p][f"item{i}"] for i in range(7)]
            stat_perks_raw = self.data["info"]["participants"][p]['perks']["statPerks"]
            stat_perks = [stat_perks_raw[i] for i in stat_perks_raw.keys()]
            role = self.data["info"]["participants"][p]["teamPosition"]
            summ =  [self.data["info"]["participants"][p][f"summoner{i}Id"] for i in range(1,3)]

            # Runes reforged 
            perks_raw = self.data["info"]["participants"][p]['perks']["styles"]
            prim_raw = perks_raw[0]["selections"]
            sub_raw = perks_raw[1]["selections"]

            prim = [prim_raw[i]["perk"] for i in range(4)]
            sub = [sub_raw[i]["perk"] for i in range(2)]
            runes = (prim,sub)

            # starters and runes from timeline
            p_id = self.data["info"]["participants"][p]["participantId"]
            skill_order, starters = self.timeline_fetch(p_id)

            # append final Champion object result
            champ_list.append(Champion(champ,role=role,win=win,build=build,runes=runes,\
                stat_runes=stat_perks,summ=summ, skill_order=skill_order, starters=starters))

        return champ_list
    
    def timeline_fetch(self, participant_id):
        # skill order 

        df = self.skill_table()
        df_p = df[(df["participantId"]==participant_id) & (df["skillSlot"]!=4)]     # filters the skill_table by participant and remmove skillSlot 4 (R)

        maxed = df_p.groupby("skillSlot").max("timestamp").sort_values("timestamp")     # find max timestamps for each skill and order them
        skill_order = maxed.axes[0].to_list()       # extract ordered skills (skillSlot is the firts Axis)
        
        # items
        df = self.item_tabe()
        df_p = df[(df["participantId"]==participant_id) & (df["timestamp"]<=40000)]     # starters are generally bought before 40'000
        starters = df_p["itemId"].to_list()
        
        return skill_order, starters

    # returns a DataFrame with participantId, skillSlot, timestamp
    def skill_table(self):
        l = []
        frames = self.timeline["info"]["frames"]
        for frame in frames:
            for event in frame["events"]:
                if event["type"] == "SKILL_LEVEL_UP":
                    l.append(event)
            df = pd.DataFrame(l)
        return df
    
    # returns a DataFrame with itemId, participantId, timestamp
    def item_tabe(self):
        l=[]
        frames = self.timeline["info"]["frames"]
        for frame in frames:
            for event in frame["events"]:
                if event["type"] == "ITEM_PURCHASED":
                    l.append(event)
            df = pd.DataFrame(l)
        return df