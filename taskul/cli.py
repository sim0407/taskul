"""CLI entry point (Click)."""
import click
from .commands.create_task import create_task
from .commands.create_project import create_project


@click.group()
@click.option("--json", "json_output", is_flag=True, help="Prefer JSON output for all commands")
@click.pass_context
def cli(ctx, json_output):
    ctx.ensure_object(dict)
    ctx.obj["json_output"] = json_output


cli.add_command(create_task)
cli.add_command(create_project)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
