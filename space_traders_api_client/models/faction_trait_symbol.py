from enum import Enum


class FactionTraitSymbol(str, Enum):
    ADAPTABLE = "ADAPTABLE"
    AGGRESSIVE = "AGGRESSIVE"
    BOLD = "BOLD"
    BRUTAL = "BRUTAL"
    BUREAUCRATIC = "BUREAUCRATIC"
    CAPITALISTIC = "CAPITALISTIC"
    CLAN = "CLAN"
    COLLABORATIVE = "COLLABORATIVE"
    COMMERCIAL = "COMMERCIAL"
    COOPERATIVE = "COOPERATIVE"
    CURIOUS = "CURIOUS"
    DARING = "DARING"
    DEFENSIVE = "DEFENSIVE"
    DEXTEROUS = "DEXTEROUS"
    DISTRUSTFUL = "DISTRUSTFUL"
    DIVERSE = "DIVERSE"
    DOMINANT = "DOMINANT"
    DOMINION = "DOMINION"
    ENTREPRENEURIAL = "ENTREPRENEURIAL"
    ESTABLISHED = "ESTABLISHED"
    EXILES = "EXILES"
    EXPLORATORY = "EXPLORATORY"
    FLEETING = "FLEETING"
    FLEXIBLE = "FLEXIBLE"
    FORSAKEN = "FORSAKEN"
    FRAGMENTED = "FRAGMENTED"
    FREE_MARKETS = "FREE_MARKETS"
    FRINGE = "FRINGE"
    GUILD = "GUILD"
    IMPERIALISTIC = "IMPERIALISTIC"
    INDEPENDENT = "INDEPENDENT"
    INDUSTRIOUS = "INDUSTRIOUS"
    INESCAPABLE = "INESCAPABLE"
    INNOVATIVE = "INNOVATIVE"
    INTELLIGENT = "INTELLIGENT"
    ISOLATED = "ISOLATED"
    LOCALIZED = "LOCALIZED"
    MILITARISTIC = "MILITARISTIC"
    NOTABLE = "NOTABLE"
    PEACEFUL = "PEACEFUL"
    PIRATES = "PIRATES"
    PROGRESSIVE = "PROGRESSIVE"
    PROUD = "PROUD"
    RAIDERS = "RAIDERS"
    REBELLIOUS = "REBELLIOUS"
    RESEARCH_FOCUSED = "RESEARCH_FOCUSED"
    RESOURCEFUL = "RESOURCEFUL"
    SCAVENGERS = "SCAVENGERS"
    SECRETIVE = "SECRETIVE"
    SELF_INTERESTED = "SELF_INTERESTED"
    SELF_SUFFICIENT = "SELF_SUFFICIENT"
    SMUGGLERS = "SMUGGLERS"
    STRATEGIC = "STRATEGIC"
    TECHNOLOGICALLY_ADVANCED = "TECHNOLOGICALLY_ADVANCED"
    TREASURE_HUNTERS = "TREASURE_HUNTERS"
    UNITED = "UNITED"
    UNPREDICTABLE = "UNPREDICTABLE"
    VISIONARY = "VISIONARY"
    WELCOMING = "WELCOMING"

    def __str__(self) -> str:
        return str(self.value)