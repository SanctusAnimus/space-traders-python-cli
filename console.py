from rich.console import Console
from rich.theme import Theme

traders_theme = Theme({
    "success": "bold u green on grey19",
    "fail": "bold u red on grey19",
    # specifics
    "ship": "bold magenta",
    "system": "bold u indian_red",
    "waypoint": "bold u orange_red1",
    "resource": "bold yellow",
    "survey": "bold u dodger_blue1",
    "contract": "bold green",
    "agent": "bold bright_cyan",

    "ship_status": "yellow u",
    "flight_mode": "yellow u",
    "custom_table_header": "bold chartreuse3",

    "cooldown": "red u",
    "duration": "green u"
})

console = Console(theme=traders_theme)
