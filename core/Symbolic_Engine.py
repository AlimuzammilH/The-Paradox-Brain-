class SymbolicEngine:
    RULES = {
        'capitalism': {
            'socialism': "Synthesis: Mixed economy with welfare safeguards",
            'environment': "Synthesis: Green capitalism with carbon pricing"
        }
    }

    def analyze(self, text: str) -> str:
        for concept, responses in self.RULES.items():
            if concept in text.lower():
                return responses.get(next(
                    (c for c in responses.keys() if c in text.lower()), 
                    "Insufficient data for synthesis"
                )
        return "No symbolic rule matched"
