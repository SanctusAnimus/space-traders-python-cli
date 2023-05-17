from datetime import datetime, timezone, timedelta
from typing import Iterable

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from console import console
from space_traders_api_client.models import Survey
from space_traders_api_client.models.agent import Agent
from space_traders_api_client.models.contract import Contract
from space_traders_api_client.models.market import Market
from space_traders_api_client.models.ship import Ship
from space_traders_api_client.models.ship_nav import ShipNavStatus
from space_traders_api_client.models.shipyard import Shipyard
from space_traders_api_client.models.waypoint import Waypoint, Unset

SUCCESS_PREFIX = f"[white on green]Success[/] ┃ "  # noqa
FAIL_PREFIX = f"[black on red]Fail[/] ┃ "  # noqa

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def __duration_str(d1: datetime, d2: datetime) -> str:
    td = d1 - d2
    if td < timedelta(0):
        return f"-{-td}"
    return str(td)


def print_contracts(contracts: Iterable[Contract]):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="white bold")
    table.add_column("Deadline")
    table.add_column("Deliver")
    table.add_column("Status")

    for contract in contracts:
        deliver = "\n".join(
            f"[resource]{deliver_target.trade_symbol}[/] to [waypoint]{deliver_target.destination_symbol}[/]\n"
            f"[cyan]{deliver_target.units_fulfilled}[/] / [cyan]{deliver_target.units_required}[/]"
            for deliver_target in contract.terms.deliver
        )
        table.add_row(
            contract.id,
            contract.terms.deadline.strftime(TIME_FORMAT),
            deliver,
            "[green]Fulfilled[/]" if contract.fulfilled else "[yellow]Accepted[/]" if contract.accepted else
            f"[red]Pending[/]\n{contract.expiration.replace(microsecond=0)}"
        )
    console.print(table)


def print_ships(ships: Iterable[Ship]):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="ship")
    table.add_column("Role")
    table.add_column("Nav")
    table.add_column("Fuel")

    current_time = datetime.now(tz=timezone.utc)

    for ship in ships:
        nav_data = f"[ship_status]{ship.nav.status}[/] - [waypoint]{ship.nav.waypoint_symbol}[/]"
        # TODO: if we are in transit, but arrival is in the past, display special state (as unconfirmed IN_ORBIT)
        if ship.nav.status == ShipNavStatus.IN_TRANSIT:
            route = ship.nav.route
            remaining_time = route.arrival - current_time

            nav_data = f"[ship_status]{ship.nav.status}[/] " \
                       f"[waypoint]{route.departure.symbol}[/] => [waypoint]{route.destination.symbol}[/]\n" \
                       f"Arrives at {route.arrival.strftime(TIME_FORMAT)} (in [duration]{remaining_time}[/])"
        table.add_row(
            ship.symbol, ship.registration.role,
            nav_data,
            f"{ship.fuel.current} / {ship.fuel.capacity}"
        )
    console.print(table)


def print_waypoints(waypoints: Iterable[Waypoint]):
    table = Table(header_style="custom_table_header", show_lines=True)
    table.add_column("Symbol", style="waypoint")
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


def print_agent(agent: Agent):
    console.print(f"""
[bold magenta]Agent[/]: [agent]{agent.symbol} | {agent.symbol}[/]
[bold magenta]Credits[/]: [b]{agent.credits_}[/]
    """.strip())


def print_ship(ship: Ship):
    current_time = datetime.now(tz=timezone.utc)
    route = ship.nav.route

    extra_string = ""

    dock_string = f" at [u]{ship.nav.waypoint_symbol}[/]"
    if ship.nav.status == ShipNavStatus.IN_TRANSIT:
        dock_string = f"\n\t[u]{route.departure.symbol}[/] ({route.departure.type})" \
                      f"\n\t=> [u]{route.destination.symbol}[/] ({route.destination.type})"

    if (cooldown := ship.additional_properties.get("cooldown", None)) and cooldown.expiration > current_time:
        extra_string += f"\n[bold red]ON COOLDOWN[/]: till [cooldown]{cooldown.expiration.replace(microsecond=0)}[/] " \
                        f"(in [u]{__duration_str(cooldown.expiration, current_time)}[/])"

    nav_string = f"""
[bold magenta]Fuel[/]: {ship.fuel.current} / [green]{ship.fuel.capacity}[/] | In [u]{ship.nav.flight_mode}[/]
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

    ship_panel = Panel(Group(*content), title=f"Ship [bold]{ship.symbol}[/] \[{ship.registration.role}]", expand=False)
    console.print(ship_panel)


def print_waypoint(waypoint: Waypoint):
    pass


def print_market(market: Market):
    trade_goods = Table(title="Trade Goods", header_style="custom_table_header")
    trade_goods.add_column("Name", style="resource")
    trade_goods.add_column("Supply")
    trade_goods.add_column("Volume", style="cyan")
    trade_goods.add_column("Price B / S")
    for trade_good in market.trade_goods:
        trade_goods.add_row(
            trade_good.symbol,
            str(trade_good.supply),
            str(trade_good.trade_volume),
            f"${trade_good.purchase_price} / ${trade_good.sell_price}"
        )

    exchanges_data = "\n".join(f"[resource]{exchange.symbol}[/]" for exchange in market.exchange)
    exchanges = Panel(exchanges_data, title="Exchanges", expand=False)

    imports_data = "\n".join(f"[resource]{import_.symbol}[/]" for import_ in market.imports)
    imports = Panel(imports_data, title="Imports", expand=False)

    exports_data = "\n".join(f"[resource]{export.symbol}[/]" for export in market.exports)
    exports = Panel(exports_data, title="Exports", expand=False)

    transactions = Table(title="Transactions", header_style="custom_table_header")
    transactions.add_column("Date")
    transactions.add_column("Ship", style="ship")
    transactions.add_column("Item", style="resource")
    transactions.add_column("Action")
    transactions.add_column("Units", style="cyan")
    transactions.add_column("Price T / 1")
    for transaction in market.transactions:
        transactions.add_row(
            transaction.timestamp.strftime(TIME_FORMAT),
            transaction.ship_symbol,
            transaction.trade_symbol,
            str(transaction.type),
            str(transaction.units),
            f"${transaction.total_price} / ${transaction.price_per_unit}"
        )

    columns_data = [
        trade_goods,
        transactions
    ]
    if exchanges_data:
        columns_data.append(exchanges)
    if imports_data:
        columns_data.append(imports)
    if exports_data:
        columns_data.append(exports)

    group = Columns(columns_data)
    panel = Panel(group, title=f"Market [waypoint]{market.symbol}[/]")
    console.print(panel)


def print_shipyard(shipyard: Shipyard):
    ship_types = "\n".join([ship_type.type for ship_type in shipyard.ship_types])
    sold_ship_types = Panel(ship_types, title=f"Ship types")

    ships = Table(title=f"Ships", header_style="custom_table_header")
    ships.add_column("Name", style="ship")
    ships.add_column("Type")
    ships.add_column("Parts")
    ships.add_column("Mounts")
    ships.add_column("Modules")
    ships.add_column("Price")
    for ship in shipyard.ships:
        parts = "\n".join(part.name for part in [ship.frame, ship.engine, ship.reactor])
        mounts = "\n".join(mount.name for mount in ship.mounts)
        modules = "\n".join(module.name for module in ship.modules)
        ships.add_row(
            ship.name,
            ship.type,
            parts,
            mounts,
            modules,
            str(ship.purchase_price)
        )

    transactions = Table(title="Transactions", header_style="custom_table_header")
    transactions.add_column("Date")
    transactions.add_column("Agent", style="agent")
    transactions.add_column("Ship", style="ship")
    transactions.add_column("Price")
    for transaction in shipyard.transactions:
        transactions.add_row(
            transaction.timestamp.strftime(TIME_FORMAT),
            transaction.agent_symbol,
            transaction.ship_symbol,
            str(transaction.price)
        )

    group = Columns([
        sold_ship_types,
        ships,
        transactions
    ])
    panel = Panel(group, title=f"Shipyard [waypoint]{shipyard.symbol}[/]")
    console.print(panel)


def print_surveys(surveys: list[Survey]):
    pass
