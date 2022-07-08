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
    
    def get_mythic_list(self) -> bool:
        item_list = self.request(self.item_url(),"mythic list")
        for itemId in item_list["data"]:
            if "rarityMythic" in item_list["data"][itemId]["description"]:
                db["champions"].update_one({"_id":"mythics"},{"$addToSet":{"values":itemId}})

    def player_list(self,region="euw1",*args,**kwargs):
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
        """
        populate db with matchIds
        """
        region = self.convert_region(reg)

        players = db[region].find_one({"_id":"players"})["values"]
        for p in players:
            player = Player(p[0],reg,p[1],p[2])
            player.insert_match_list()  
            
    def matches_fetch(self,reg="euw1",*args,**kwargs):
        region = self.convert_region(reg)

        matches = db[region].find_one({"_id":"matches"})["not-fetched"]
        for m in matches[:6]:       #FIXME: remove matches range
            match = Match(m,region)
            if not match.check_version(self.lol_version):
                #TODO valuta se mettere una funzione unica
                db[region].update_one({"_id":"players"}, {"$addToSet":{"discarded":m}})
                db[region].update_one({"_id":"players"}, {"$pull":{"not-fetched":m}})
                continue
            for c in match.match_fetch():
                print(c) # FIXME
                c.insert()
            #quit()  # FIXME: still in development


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
        db[region].update_one({"_id":"players"}, {"$addToSet":{"values":(self.account_id,self.account_id,self.puuid)}})

    def insert_match_list(self):      # 10 games per player
        region = self.convert_region(self.region)
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puuid}/ids?type=ranked&start=0&count=10&api_key={key}"
        data = self.request(url, f"match list from player in region {region}")
        for m_id in data:
            db[region].update_one({"_id":"matches"},{"$addToSet":{"not-fetched":m_id}})
        


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
        self.id = str(_id)
        self.build = build
        self.runes = runes
        self.stat_runes = stat_runes
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

    def isMythic(self,itemId):
        if db["champions"].find_one({"_id":"mythics","values":{"$in":[str(itemId)]}}) is not None:
            return True
        return False

    def repr_list(self,l:list) -> str:
        final = ""
        for item in l:
            final += str(item) + ":"
        return final.rstrip(':')

    def repr_list_sorted(self,l:list) -> str:
        final = ""
        l.sort()
        for item in l:
            final += str(item) + ":"
        return final.rstrip(':')

    def add_game(self): # updates games, roles count and wins
        db['champions'].update_one({'_id':self.id},{'$inc':{'games':1,f"role.{self.role.lower()}":1}})
        if self.win:
            db['champions'].update_one({'_id':self.id},{'$inc':{'wins':1}})
        
    def item_logic(self,mythic, items):
        # check the existence of the mythic
        db["champions"].update_one({"_id":self.id,f'build.{mythic}': {'$exists' : False}}, {'$set': {f'build.{mythic}.count': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.count':1}})

        already_present = db["champions"].find_one({"_id":self.id, f'build.{mythic}.path':{'$exists' : True}})

        if already_present is None:
            db["champions"].update_one({"_id":self.id}, {'$set': {f'build.{mythic}.path.{items}': 1}})
            return
        
        paths = already_present["build"][mythic]["path"]
        for path in paths:
            if items in path:
                db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.path.{path}':1}})
            elif path in items:
                db["champions"].update_one({'_id':self.id,f'build.{mythic}.path.{items}': {'$exists' : False}}, {'$set': {f'build.{mythic}.path.{items}': 0}})
                db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.path.{items}':1}})
                #TODO remove the shortest


    def add_items(self): #aggiungi la lista degli itmes
        items = self.build
        tr = items.pop(-1)
        
        mythic = "0"
        for i in items:
            item = str(i)
            if self.isMythic(item):
                mythic = item
                
        all_items = self.repr_list(items)

        db["champions"].update_one({'_id':self.id,f'.trinket.{tr}': {'$exists' : False}}, {'$set': {f'trinket.{tr}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'trinket.{tr}':1}})

        #TODO: Item logic: advantage longer builds
        self.item_logic(mythic, all_items)
        
        return  #FIXME
        
        
        db["champions"].update_one({f'{self.id}.build.{mythic}': {'$exists' : False}}, {'$set': {f'{self.id}.build.{mythic}.count': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.count':1}})

        db["champions"].update_one({f'{self.id}.build.{mythic}.path.{all_items}': {'$exists' : False}}, {'$set': {f'{self.id}.build.{mythic}.path.{all_items}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.path.{all_items}':1}})

        
    
    def add_runes(self):
        rn = self.repr_list(self.stat_runes)
        db["champions"].update_one({'_id':self.id,f'stat_runes.{rn}': {'$exists' : False}}, {'$set': {f'stat_runes.{rn}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'stat_runes.{rn}':1}})

        key_rune = self.runes[0][0]
        all_runes = self.repr_list(self.runes[0]) + "+" + self.repr_list(self.runes[1])
        db["champions"].update_one({'_id':self.id,f'runes.{key_rune}': {'$exists' : False}}, {'$set': {f'runes.{key_rune}.count': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'runes.{key_rune}.count':1}})

        db["champions"].update_one({'_id':self.id,f'runes.{key_rune}.path.{all_runes}': {'$exists' : False}}, {'$set': {f'runes.{key_rune}.path.{all_runes}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'runes.{key_rune}.path.{all_runes}':1}})



    def add_summs(self):
        summ = self.repr_list_sorted(self.summ)
        db["champions"].update_one({'_id':self.id,f'summ.{summ}': {'$exists' : False}}, {'$set': {f'summ.{summ}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'summ.{summ}':1}})

    def add_skill(self):
        skill = self.repr_list(self.skill_order)
        db["champions"].update_one({'_id':self.id,f'skill.{skill}': {'$exists' : False}}, {'$set': {f'skill.{skill}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'skill.{skill}':1}})

    def add_starter(self):
        starters = self.repr_list_sorted(self.starters)
        if starters != "":
            db["champions"].update_one({'_id':self.id,f'starters.{starters}': {'$exists' : False}}, {'$set': {f'starters.{starters}': 0}})
            db['champions'].update_one({'_id':self.id},{'$inc':{f'starters.{starters}':1}})

    def insert(self):
        #TODO: da finire, raggruppa gli altri
        self.add_game()
        self.add_summs()
        self.add_skill()
        self.add_starter()
        self.add_items()
        self.add_runes()

        # aggiungi build e rune
        

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
    
    def remove_match(self):
        #TODO: valuta se scrivere una funzione apposta
        pass

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
            build = [self.data["info"]["participants"][p][f"item{i}"] for i in range(7)]    #TODO take this from the timeline
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
        df = self.item_table()
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
    def item_table(self):
        l=[]
        frames = self.timeline["info"]["frames"]
        for frame in frames:
            for event in frame["events"]:
                if event["type"] == "ITEM_PURCHASED":
                    l.append(event)
            df = pd.DataFrame(l)
        return df