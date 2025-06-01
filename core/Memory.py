import sqlite3
import numpy as np
import faiss

class MemoryStore:
    def __init__(self):
        self.db = sqlite3.connect('memory.db')
        self.index = faiss.IndexFlatL2(384)
        self._init_db()

    def _init_db(self):
        self.db.execute('''CREATE TABLE IF NOT EXISTS arguments
                          (id INTEGER PRIMARY KEY, text TEXT, embedding BLOB)''')

    def add(self, text: str, embedding: np.ndarray):
        self.db.execute("INSERT INTO arguments (text, embedding) VALUES (?, ?)",
                       (text, embedding.tobytes()))
        self.index.add(embedding.reshape(1, -1))
