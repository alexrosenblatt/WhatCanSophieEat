import sqlite3

connection = sqlite3.connect('searches.db')
cursor = connection.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS Searches
              (id INTEGER PRIMARY Key AUTOINCREMENT NOT NULL,
              Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                name TEXT,
			   serving_unit TEXT,
			    serving_size_grams FLOAT,
				item TEXT,
				measure TEXT,
				quantity FLOAT,
				fructose_n FLOAT,
				glucose_n FLOAT,
				sucrose FLOAT)''')