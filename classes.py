import json
import csv
import requests as rq
from config import key
from config import db
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, wait
import sys, os  # for debug


class Utils:
    
    def request(self,url:str,use_case:str):
        req = rq.get(url)
        if req.status_code == 429:
            time.sleep(122)
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
        self.languages = ["it_IT","en_US"]

    def get_lol_version(self):
        return rq.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
    
    def item_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/item.json"
    
    def champ_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/champion.json"
    
    def rune_url(self,language="en_US"):
        return f"https://ddragon.leagueoflegends.com/cdn/{self.lol_version}/data/{language}/runesReforged.json"
    
    def perk_url(self,language="en_US"):
        # FIXME didn't want to rely on external sources, but perks were too hard to find
        # every language_url must be added maually (actually does not work for language other than en_US)
        if language == "it_IT":
            return "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/it_it/v1/perks.json"
        if language == "en_US":
            return "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/perks.json" 

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
                db["champions"].update_one({"_id":"complete_items"},{"$addToSet":{"values":itemId}})
            elif "depth" in item_list["data"][itemId].keys() and item_list["data"][itemId]["depth"]==3:
                db["champions"].update_one({"_id":"complete_items"},{"$addToSet":{"values":itemId}})
            elif "Boots" in item_list["data"][itemId]["tags"]:
                db["champions"].update_one({"_id":"complete_items"},{"$addToSet":{"values":itemId}})

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
        for m in matches:
            try:
                match = Match(m,region)
                if not match.check_version(self.lol_version):
                    #TODO valuta se mettere una funzione unica
                    db[region].update_one({"_id":"matches"}, {"$addToSet":{"discarded":m}})
                    db[region].update_one({"_id":"matches"}, {"$pull":{"not-fetched":m}})
                    continue
                for c in match.match_fetch():
                    
                    c.insert()
                # TODO must be tested
                db[region].update_one({"_id":"matches"}, {"$addToSet":{"fetched":m}})
                db[region].update_one({"_id":"matches"}, {"$pull":{"not-fetched":m}})
                #quit()  # FIXME: still in development
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(e, exc_type, fname, exc_tb.tb_lineno)
    
    def names_list_converter(self,list_type:str,itr:str,language="en_US"):
        """Takes the iterable string and return the names"""
        final_list = []
        if list_type == "items":
            url = self.item_url(language)
            data = self.request(url,"item names list")["data"]
            for item in itr.split(":"):
                if item != "0":
                    n = data[item]["name"]
                    final_list.append(n)
            return ",".join(final_list)
        if list_type == "runes":    # + and - are used to split runes paths later
            final_list = []
            url = self.rune_url(language)
            data = self.request(url,"item names list")

            def find_item(item,data):   # helps with all the loops to parse the runes page
                for rune_path in range(len(data)):
                    path_name = data[rune_path]["name"]
                    for layer in range(len(data[rune_path]["slots"])):
                        for rune in  range(len(data[rune_path]["slots"][layer]["runes"])):
                            if str(data[rune_path]["slots"][layer]["runes"][rune]["id"]) == item:
                                name = data[rune_path]["slots"][layer]["runes"][rune]["name"]
                                return path_name, name
            for s in itr.split("+"):
                for item in s.split(":"):
                    path, name = find_item(item, data)
                    if path+"-" not in final_list:
                        final_list.append(path+"-")
                    final_list.append(name)
                final_list.append("+")  
            final_list.pop(-1)                 
            return ",".join(final_list)
        if list_type == "perks":
            final_list = []
            url = self.perk_url(language)
            data = self.request(url, "perk names list")
            for perk in itr.split(":"):
                for p in data:
                    if str(p["id"]) == perk:
                        final_list.append(p["name"])
                        break
            return ",".join(final_list)
        if list_type == "summ":
            url = self.summ_url(language)
            data = self.request(url,"item names list")["data"]
            for item in itr.split(":"):
                for s in data:
                    if data[s]["key"]== item:
                        final_list.append(data[s]["name"])
            return ",".join(final_list)
        if list_type == "skill":
            new = itr.replace(":",",").replace("1"," q").replace("2"," w").replace("3"," e")
            return new


    def result_maker(self,language="en_US"):      #TODO stat perks name  
        result = {"_id":f"results_{language}","version":self.lol_version,"data":{}}
        for c in self.champ_dict:
            try:
                result["data"][c] = {}
                champ = db["champions"].find_one({"_id":c})
                #build
                myth = max(champ["build"], key= lambda x: champ["build"][x]["count"])
                build = max(champ["build"][myth]["path"], key= lambda x: champ["build"][myth]["path"][x])
                result["data"][c]["build"]=self.names_list_converter("items",build,language)
                #runes
                main = max(champ["runes"], key= lambda x: champ["runes"][x]["count"])
                runes = max(champ["runes"][main]["path"], key= lambda x: champ["runes"][main]["path"][x])
                result["data"][c]["runes"]=self.names_list_converter("runes",runes,language)
                #role
                role = max(champ["role"], key= lambda x: champ["role"][x])
                result["data"][c]["role"] = role
                #trinket
                trinket = max(champ["trinket"], key= lambda x: champ["trinket"][x])
                result["data"][c]["trinket"] = self.names_list_converter("items",trinket,language)
                #stat_runes
                stat_runes = max(champ["stat_runes"], key= lambda x: champ["stat_runes"][x])
                result["data"][c]["stat_runes"]=self.names_list_converter("perks",stat_runes,language)
                #summ
                summ = max(champ["summ"], key= lambda x: champ["summ"][x])
                result["data"][c]["summ"] = self.names_list_converter("summ",summ,language)
                #skill
                skill = max(champ["skill"], key= lambda x: champ["skill"][x])
                result["data"][c]["skill"] = self.names_list_converter("skill",skill,language)
                #starters
                starters = max(champ["starters"], key= lambda x: champ["starters"][x])
                result["data"][c]["starters"] = self.names_list_converter("items",starters,language)
                #winrate
                result["data"][c]["winrate"] = round(champ["wins"]/champ["games"],4)
            except ValueError:
                print(f"no data for {c}")
        
        db["champions"].replace_one({"_id":f"results_{language}"},result,upsert=True)
        with open("champion.csv","w") as f:
            for k in self.champ_dict:
                f.write(self.champ_dict[k]+","+k+"\n")

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
        stat_runes=None ,summ=None, skill_order=None, starters=None, trinket=None):
        
        self.role = role
        self.id = str(_id)
        self.build = build
        self.runes = runes
        self.stat_runes = stat_runes
        self.summ = summ
        self.win = win
        self.skill_order = skill_order
        self.starters = starters
        self.trinket = trinket
    
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
    
    def isComplete(self,itemId):
        if db["champions"].find_one({"_id":"complete_items","values":{"$in":[str(itemId)]}}) is not None:
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
        for old in paths:
            #FIXME to be tested
            if items.partition(':0:')[0] in old:   # if the new one is the shorter version of the builds already presents
                db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.path.{old}':1}})
                

            elif old.partition(':0:')[0] in items: # if the new one is longer than a previous build
                m = db["champions"].find_one({'_id':self.id})["build"][mythic]["path"][old] #TODO to be tested
                db["champions"].update_one({'_id':self.id,f'build.{mythic}.path.{items}': {'$exists' : False}}, {'$set': {f'build.{mythic}.path.{items}': m}})
                db['champions'].update_one({'_id':self.id},{'$inc':{f'build.{mythic}.path.{items}':1}})
                #remove the short build
                db["champions"].update_one({'_id':self.id},{'$unset':{f'build.{mythic}.path.{old}':""}})
                
            else:
                
                db["champions"].update_one({'_id':self.id,}, {'$set': {f'build.{mythic}.path.{items}': 1}})


    def add_items(self): #aggiungi la lista degli itmes
        items = self.build
        tr = self.trinket
        
        for i in items:
            if not self.isComplete(i):
                items.remove(i)
        mythic = "0"
        for i in items:
            item = str(i)
            if self.isMythic(item):
                mythic = item
                break
        all_items = self.repr_list(items)

        db["champions"].update_one({'_id':self.id,f'.trinket.{tr}': {'$exists' : False}}, {'$set': {f'trinket.{tr}': 0}})
        db['champions'].update_one({'_id':self.id},{'$inc':{f'trinket.{tr}':1}})

        #Item logic: aggregate items and advantage longer builds
        self.item_logic(mythic, all_items)
        
        #return  #FIXME
        
        
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
        self.add_game()
        self.add_summs()
        self.add_skill()
        self.add_starter()
        self.add_items()
        self.add_runes()

        

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
    

    # returns the list of Champions
    def match_fetch(self) -> list:   
        champ_list = []
        for p in range(10):
            champ = self.data["info"]["participants"][p]["championId"]
            win = self.data["info"]["participants"][p]["win"]
            tr = self.data["info"]["participants"][p]["item6"]    #TODO could it be taken from the timeline? yes
            stat_perks_raw = self.data["info"]["participants"][p]['perks']["statPerks"]
            stat_perks = [stat_perks_raw[i] for i in stat_perks_raw.keys()]
            role = self.data["info"]["participants"][p]["teamPosition"]
            summ =  [self.data["info"]["participants"][p][f"summoner{i}Id"] for i in range(1,3)]

            # Build
            p_id = self.data["info"]["participants"][p]["participantId"]
            build = self.build_from_timeline(p_id)
            

            # Runes reforged 
            perks_raw = self.data["info"]["participants"][p]['perks']["styles"]
            prim_raw = perks_raw[0]["selections"]
            sub_raw = perks_raw[1]["selections"]

            prim = [prim_raw[i]["perk"] for i in range(4)]
            sub = [sub_raw[i]["perk"] for i in range(2)]
            runes = (prim,sub)

            # starters and runes from timeline
            #p_id = self.data["info"]["participants"][p]["participantId"]
            skill_order, starters = self.timeline_fetch(p_id)

            # append final Champion object result
            champ_list.append(Champion(champ,role=role,win=win,build=build,runes=runes,\
                stat_runes=stat_perks,summ=summ, skill_order=skill_order, starters=starters, trinket=tr))

        return champ_list
    
    def build_from_timeline(self,participant_id):
        frames = self.timeline["info"]["frames"]
        l = []
        plus = ["ITEM_PURCHASED"]
        minus = ["ITEM_DESTROYED","ITEM_SOLD","ITEM_UNDO"]
        for frame in frames:
                    for event in frame["events"]:
                        if event["type"] in plus or event["type"] in minus:
                            l.append(event)
        df = pd.DataFrame(l)

        sold = df[(df["participantId"]==participant_id) & ((df['type']=="ITEM_DESTROYED") | (df['type']=="ITEM_SOLD") | (df['type']=="ITEM_UNDO"))]
        build_raw = df[-df.itemId.isin(sold.itemId) & -df.itemId.isin(sold.beforeId) & (df["participantId"]==participant_id) & (df['type']=="ITEM_PURCHASED")]
        build = build_raw['itemId'].astype('int').astype('str').to_list()
        return build
        
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