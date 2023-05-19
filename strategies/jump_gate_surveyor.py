# strategy for probe to survey learn systems in the jump gate;
# ideally should be done when persistence is set up to store system data not in the damned json;
# aimed at discovering markets for cross-system trade and shipyards for other ship types

class JumpGateSurveyor:
    def __init__(self, starting_system: str):
        self.starting_system = starting_system
        self.starting_jump_gate = None

    def assign_probe(self, ship_symbol: str):
        pass
