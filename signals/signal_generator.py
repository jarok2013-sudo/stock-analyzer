"""
signal_generator.py → końcowa decyzja (BUY/WATCH/AVOID).

# {
#     "signal": "BUY",
#     "confidence": 82,
#     "stop_loss": 66.80,
#     "target": 72.10,
#     "risk_reward": 2.9,
#     "reasons": [
#         "Silny trend",
#         "Cena nad EMA20",
#         "Blisko wsparcia"
#     ]
# }
"""


from config import (
    STRONG_BUY_QUALITY_SCORE,
    STRONG_BUY_ENTRY_SCORE,
    BUY_QUALITY_SCORE,
    BUY_ENTRY_SCORE,
    WATCH_ENTRY_SCORE,
    MIN_RR
)


class SignalGenerator:

    def __init__(self, analysis):

        self.analysis = analysis

   
    #def determine_signal(self):

       
    
    def generate(self):

        q = self.analysis.quality_score
        e = self.analysis.entry_score
        rr = self.analysis.risk_reward

        # Weryfikacja minimalnego poziomu R/R
        has_valid_rr = (rr is not None) and (rr >= MIN_RR)

        # 1. STRONG BUY - Wymaga wysokiej jakości, mocnego wejścia ORAZ bezpiecznego R/R
        if (
            q >= STRONG_BUY_QUALITY_SCORE
            and e >= STRONG_BUY_ENTRY_SCORE
            and has_valid_rr
        ):
            return "STRONG BUY"

        # 2. BUY - Sprawdzamy progi punktowe i wymóg MIN_RR
        if q >= BUY_QUALITY_SCORE and e >= BUY_ENTRY_SCORE and has_valid_rr:
            return "BUY"

        # 3. WATCH - Gdy punkty kwalifikują do BUY, ale R/R jest poniżej progu MIN_RR
        if q >= BUY_QUALITY_SCORE and e >= BUY_ENTRY_SCORE and not has_valid_rr:
            return "WATCH"

        if (
            q >= BUY_QUALITY_SCORE
            and
            e < BUY_ENTRY_SCORE
        ):
            return "WAIT"

        if e >= WATCH_ENTRY_SCORE:
            return "WATCH"

        return "AVOID"