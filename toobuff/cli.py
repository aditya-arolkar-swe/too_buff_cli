"""Main CLI entry point."""

import click

from toobuff.commands import init_command, checkin_command, data_command, goals_command, export_command


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Too Buff CLI - Track your fitness goals and daily check-ins."""
    pass


main.add_command(init_command, name="init")
main.add_command(checkin_command, name="checkin")
main.add_command(data_command, name="data")
main.add_command(goals_command, name="goals")
main.add_command(export_command, name="export")


if __name__ == "__main__":
    main()
