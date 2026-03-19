import sqlite3
import json
import os
import sys
PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'Contact.sqlite3')
class SQLiteClient:
    def __init__(self, db_path=PATH, table_name="entries"):
        self.conn = sqlite3.connect(db_path,check_same_thread=False)
        self.table_name = table_name
        self._create_table()

    def _create_table(self):
        creating_table_string=f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            domain TEXT PRIMARY KEY,
            url TEXT,
            emails TEXT,
            phones TEXT,
            instagram TEXT,
            facebook TEXT,
            youtube TEXT,
            linkedin TEXT,
            twitter TEXT,
            pinterest TEXT,
            tiktok TEXT,
            whatsapp TEXT
        )
        """
        self.conn.execute(creating_table_string)
        self.conn.commit()
    def _close_connection(self):
        self.conn.close()
    def find_entry(self, domain):
        cursor = self.conn.execute(
            f"SELECT domain, url, emails, phones, instagram, facebook, youtube, linkedin, twitter, pinterest, tiktok, whatsapp FROM {self.table_name} WHERE domain = ?",
            (domain,)
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            return {
                "domain": row[0],
                "url": row[1],
                "emails": json.loads(row[2]),
                "phones": json.loads(row[3]),
                "instagram": json.loads(row[4]),
                "facebook": json.loads(row[5]),
                "youtube": json.loads(row[6]),
                "linkedin": json.loads(row[7]),
                "twitter": json.loads(row[8]),
                "pinterest": json.loads(row[9]),
                "tiktok": json.loads(row[10]),
                "whatsapp": json.loads(row[11]),
            }
        return None

    def insert_entry(self, data):
        self.conn.execute(f"""
        INSERT OR REPLACE INTO {self.table_name} (domain, url, emails, phones, instagram, facebook, youtube, linkedin, twitter, pinterest, tiktok, whatsapp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["domain"],
            data.get("url"),
            json.dumps(data.get("emails", [])),
            json.dumps(data.get("phones", [])),
            json.dumps(data.get('instagram', [])),
            json.dumps(data.get('facebook', [])),
            json.dumps(data.get('youtube', [])),
            json.dumps(data.get('linkedin', [])),
            json.dumps(data.get('twitter', [])),
            json.dumps(data.get('pinterest', [])),
            json.dumps(data.get('tiktok', [])),
            json.dumps(data.get('whatsapp', []))


        ))
        self.conn.commit()

    def delete_entry(self, domain):
        self.conn.execute(f"DELETE FROM {self.table_name} WHERE domain = ?", (domain,))
        self.conn.commit()
    