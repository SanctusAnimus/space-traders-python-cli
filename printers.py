from datetime import datetime, timezone, timedelta
from typing import Iterable

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from space_traders_api_client.models.agent import Agent
from space_traders_api_client.models.contract import Contract
from space_traders_api_client.models.ship import Ship
from space_traders_api_client.models.ship_nav import ShipNavStatus
from space_traders_api_client.models.waypoint import Waypoint, Unset

SUCCESS_PREFIX = f"\[[green b u]Success[/]] | "  # noqa
FAIL_PREFIX = f"\[[red b u]Fail[/]] | "  # noqa


def __duration_str(d1: datetime, d2: datetime) -> str:
    td = d1 - d2
    if td < timedelta(0):
        return f"-{-td}"
    return str(td)


def print_contracts(console: Console, contracts: Iterable[Contract]):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="white bold")
    table.add_column("Deadline")
    table.add_column("Deliver")
    table.add_column("Status")

    for contract in contracts:
        deliver = "\n".join(
            f"[bold u]{deliver_target.trade_symbol}[/] to {deliver_target.destination_symbol}\n"
            f"{deliver_target.units_fulfilled} / {deliver_target.units_required}"
            for deliver_target in contract.terms.deliver
        )
        table.add_row(
            contract.id,
            str(contract.terms.deadline.replace(microsecond=0)),
            deliver,
            "Fulfilled" if contract.fulfilled else "Accepted" if contract.accepted else f"Pending\n{contract.expiration.replace(microsecond=0)}"
        )
    console.print(table)


def print_ships(console: Console, ships: Iterable[Ship]):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Nav")
    table.add_column("Fuel")

    current_time = datetime.now(tz=timezone.utc)

    for ship in ships:
        nav_data = f"[u]{ship.nav.status}[/] - {ship.nav.waypoint_symbol}"
        if ship.nav.status == ShipNavStatus.IN_TRANSIT:
            remaining_time = ship.nav.route.arrival - current_time
            nav_data = f"[u]{ship.nav.status}[/] {ship.nav.route.departure.symbol} => {ship.nav.route.destination.symbol}\n" \
                       f"Arrives at {ship.nav.route.arrival.replace(microsecond=0)} (in {remaining_time})"
        table.add_row(
            ship.symbol, ship.registration.role,
            nav_data,
            f"{ship.fuel.current} / {ship.fuel.capacity}"
        )
    console.print(table)


def print_waypoints(console: Console, waypoints: Iterable[Waypoint]):
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("Symbol")
    table.add_column("Type")
    table.add_column("Coords", style="green")
    table.add_column("Orbitals")
    table.add_column("Traits")
    table.add_column("Chart")

    for waypoint in waypoints:
        orbitals = "\n".join(orbital.symbol for orbital in waypoint.orbitals)
        traits = "\n".join(trait.symbol for trait in waypoint.traits)
        chart = "Known" if not isinstance(waypoint.chart, Unset) else "Unset"

        table.add_row(
            waypoint.symbol,
            str(waypoint.type),
            f"{waypoint.x} : {waypoint.y}",
            orbitals,
            traits,
            chart
        )

    console.print(table)


def print_agent(console: Console, agent: Agent):
    console.print(f"""
[bold magenta]Agent[/]: [b]{agent.symbol} | {agent.symbol}[/]
[bold magenta]Credits[/]: [b]{agent.credits_}[/]
    """.strip())


def print_ship(console: Console, ship: Ship):
    current_time = datetime.now(tz=timezone.utc)
    route = ship.nav.route

    extra_string = ""

    dock_string = f" at [u]{ship.nav.waypoint_symbol}[/]"
    if ship.nav.status == ShipNavStatus.IN_TRANSIT:
        dock_string = f"\n\t[u]{route.departure.symbol}[/] ({route.departure.type})" \
                      f"\n\t=> [u]{route.destination.symbol}[/] ({route.destination.type})"

    if (cooldown := ship.additional_properties.get("cooldown", None)) and cooldown.expiration > current_time:
        extra_string += f"\n[bold red]ON COOLDOWN[/]: till [u]{cooldown.expiration.replace(microsecond=0)}[/] " \
                        f"(in [u]{__duration_str(cooldown.expiration, current_time)}[/])"

    nav_string = f"""
[bold magenta]Fuel[/]: {ship.fuel.current} / [green]{ship.fuel.capacity}[/]
[bold magenta]Status[/]: [u]{ship.nav.status}[/]{dock_string}
[bold magenta]Departure[/]: [green]{route.departure_time.replace(microsecond=0)}[/]
[bold magenta]Arrives[/]: [green]{route.arrival.replace(microsecond=0)}[/] (in [green]{__duration_str(route.arrival, current_time)}[/]){extra_string}
    """.strip()

    cargo_items = "\n".join(f"[b]{item.symbol}[/]: [green]{item.units}[/]" for item in ship.cargo.inventory)
    cargo_string = f"[bold magenta]Capacity[/]: [bold]{ship.cargo.capacity}, {ship.cargo.units}[/]\n\n{cargo_items}"

    content = [
        Panel(nav_string, title="Nav", expand=False),
        Panel(cargo_string, title="Cargo", expand=False),
    ]

    ship_panel = Panel(Columns(content), title=f"Ship [bold]{ship.symbol}[/] \[{ship.registration.role}]", expand=False)
    console.print(ship_panel)


def print_waypoint(console: Console, waypoint: Waypoint):
    pass
