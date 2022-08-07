from pymongo import MongoClient

key = "your_lol_API_key_goes_here"
mongo_username = "your_username_goes_here"
mongo_pswd = "your_pass_goes_here"

cluster = MongoClient(f"mongodb+srv://{mongo_username}:{mongo_pswd}@cluster0.m8wsbhe.mongodb.net/?retryWrites=true&w=majority")
db = cluster['mydatabase']