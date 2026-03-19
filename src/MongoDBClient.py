from pymongo import MongoClient

class MongoDBClient:
    connection_string = 'mongodb+srv://ahmedsamyallban2000:CQyv6ybNe8P%3A_pG@contact-scraper.pzpxn.mongodb.net/?retryWrites=true&w=majority&appName=Contact-Scraper'

    def __init__(self, db_name, collection_name):
        self.client = MongoClient(self.connection_string)
        self.collection = self.client[db_name][collection_name]

    def find_entry(self, domain):
        return self.collection.find_one({'domain': domain}, {'_id': 0})

    def insert_entry(self, data):
        return self.collection.insert_one(data)

    def delete_entry(self, domain):
        return self.collection.delete_one({'domain': domain})
