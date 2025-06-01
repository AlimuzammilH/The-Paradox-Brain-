import sqlite3
import numpy as np
from datetime import datetime
from collections import defaultdict

class FeedbackSystem:
    def __init__(self):
        self.db = sqlite3.connect('feedback.db')
        self._init_db()
        self.rating_history = defaultdict(list)
        
    def _init_db(self):
        """Initialize feedback database"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                input_text TEXT,
                output_text TEXT,
                rating INTEGER,
                notes TEXT,
                timestamp DATETIME
            )
        """)
    
    def log_feedback(self, input_text: str, output_text: str, rating: int, notes: str = ""):
        """Store user feedback and trigger learning"""
        self.db.execute(
            "INSERT INTO feedback (input_text, output_text, rating, notes, timestamp) VALUES (?, ?, ?, ?, ?)",
            (input_text, output_text, rating, notes, datetime.now())
        )
        self.db.commit()
        
        # Update adaptive weights (simple moving average)
        self.rating_history[input_text[:50]].append(rating)
        self._adjust_models()
    
    def _adjust_models(self):
        """Lightweight model tuning based on feedback"""
        # Only runs if at least 5 ratings exist
        if sum(len(v) for v in self.rating_history.values()) < 5:
            return
            
        avg_rating = np.mean([r for v in self.rating_history.values() for r in v])
        
        # Simple heuristic: Boost symbolic if ratings are low
        if avg_rating < 3:
            from core.orchestrator import Orchestrator
            Orchestrator.blend_weights['symbolic'] = min(0.9, Orchestrator.blend_weights['symbolic'] + 0.1)
