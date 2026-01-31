"""CLI entry point (Click)."""
import click
from .commands.create_project import create_project
from .commands.create_task import create_task
from .commands.get_board import get_board
from .commands.get_gantt import get_gantt
from .commands.get_task import get_task
from .commands.list_blockers import list_blockers
from .commands.update_task import update_task
from .commands.move_task import move_task
from .commands.add_dependency import add_dependency
from .commands.remove_dependency import remove_dependency
from .commands.mark_done import mark_done
from .commands.serve import serve


@click.group()
@click.option("--json", "json_output", is_flag=True, help="Prefer JSON output for all commands")
@click.pass_context
def cli(ctx, json_output):
    ctx.ensure_object(dict)
    ctx.obj["json_output"] = json_output


cli.add_command(create_project)
cli.add_command(create_task)
cli.add_command(get_board)
cli.add_command(get_gantt)
cli.add_command(get_task)
cli.add_command(list_blockers)
cli.add_command(update_task)
cli.add_command(move_task)
cli.add_command(add_dependency)
cli.add_command(remove_dependency)
cli.add_command(mark_done)
cli.add_command(serve)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
