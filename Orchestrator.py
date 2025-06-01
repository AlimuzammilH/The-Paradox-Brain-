import torch
from collections import deque
from typing import Optional, Dict
from sentence_transformers import SentenceTransformer
from .contradiction_engine import ContradictionNet
from .symbolic_engine import SymbolicEngine
from .memory import MemoryStore
from .feedback import FeedbackSystem

class Orchestrator:
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        # Hardware setup
        self.device = device
        self.fp16 = True if "cuda" in device else False
        
        # Core modules (lazy-loaded)
        self._embedder = None
        self._contradiction_net = None
        self._symbolic = None
        self._memory = None
        self._feedback = FeedbackSystem()
        
        # Context tracking
        self.context = deque(maxlen=5)
        self.blend_weights = {"neural": 0.6, "symbolic": 0.4}
        
        # Load lightweight embedder first
        self._load_embedder()

    def _load_embedder(self):
        """CPU-only embedder for routing"""
        self._embedder = SentenceTransformer(
            "all-MiniLM-L6-v2", 
            device="cpu",
            cache_folder="./models"
        )

    def _load_contradiction_net(self):
        """GPU module for deep analysis"""
        if self._contradiction_net is None:
            self._contradiction_net = ContradictionNet().to(self.device)
            if self.fp16:
                self._contradiction_net = self._contradiction_net.half()
            self._contradiction_net.load_state_dict(
                torch.load("./models/contradiction.pt")
            )

    def _load_symbolic(self):
        """CPU-based rule engine"""
        if self._symbolic is None:
            self._symbolic = SymbolicEngine()

    def route(self, text: str) -> str:
        """Main orchestration flow"""
        # Track context
        self.context.append(text)
        
        # Step 1: Cheap CPU-based routing
        embedding = self._embed(text)
        route = self._decide_route(text, embedding)
        
        # Step 2: Activate specialized modules
        if route == "contradiction":
            self._load_contradiction_net()
            output = self._contradiction_net(text)
        elif route == "symbolic":
            self._load_symbolic()
            output = self._symbolic.analyze(text)
        else:
            output = self._hybrid_flow(text, embedding)
        
        # Step 3: Store interaction
        self._store_memory(text, embedding)
        return output

    def _decide_route(self, text: str, embedding: torch.Tensor) -> str:
        """Rule-based router"""
        if "vs" in text or "contradict" in text:
            return "contradiction"
        elif any(kw in text.lower() for kw in ["moral", "ethical", "should"]):
            return "symbolic"
        return "hybrid"

    def _hybrid_flow(self, text: str, embedding: torch.Tensor) -> str:
        """Blend neural and symbolic reasoning"""
        neural = self._neural_analysis(text) if torch.rand(1).item() > 0.3 else None
        symbolic = self._symbolic.analyze(text)
        return f"{neural}\n\n{symbolic}" if neural else symbolic

    def log_feedback(self, input_text: str, output_text: str, rating: int):
        """Public method for feedback"""
        self._feedback.log_feedback(input_text, output_text, rating)
        self._adjust_weights(rating)

    def _adjust_weights(self, rating: int):
        """Dynamic rebalancing"""
        delta = 0.1 * (rating - 3)  # -0.2 to +0.2
        self.blend_weights["neural"] = min(max(0.3, self.blend_weights["neural"] + delta), 0.9)

    # ... (helper methods _embed, _store_memory, etc.)
