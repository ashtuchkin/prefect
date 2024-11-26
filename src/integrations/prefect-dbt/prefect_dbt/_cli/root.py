"""
`prefect-dbt` command-line application
"""

import asyncio
import platform
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as import_version

import typer

import prefect
import prefect.context
import prefect.settings
import prefect_dbt
from prefect.cli._types import PrefectTyper, SettingsOption
from prefect.cli._utilities import with_cli_exception_handling
from prefect.cli.root import display
from prefect.logging.configuration import setup_logging
from prefect.settings import (
    PREFECT_CLI_WRAP_LINES,
    PREFECT_TEST_MODE,
)

app = PrefectTyper(add_completion=True, no_args_is_help=True)


def version_callback(value: bool):
    if value:
        print(prefect.__version__)
        raise typer.Exit()


def is_interactive():
    return app.console.is_interactive


@app.callback()
@with_cli_exception_handling
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        # A callback is necessary for Typer to call this without looking for additional
        # commands and erroring when excluded
        callback=version_callback,
        help="Display the current version.",
        is_eager=True,
    ),
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="Select a profile for this CLI run.",
        is_eager=True,
    ),
    prompt: bool = SettingsOption(
        prefect.settings.PREFECT_CLI_PROMPT,
        help="Force toggle prompts for this CLI run.",
    ),
):
    if profile and not prefect.context.get_settings_context().profile.name == profile:
        # Generally, the profile should entered by `enter_root_settings_context`.
        # In the cases where it is not (i.e. CLI testing), we will enter it here.
        settings_ctx = prefect.context.use_profile(
            profile, override_environment_variables=True
        )
        try:
            ctx.with_resource(settings_ctx)
        except KeyError:
            print(f"Unknown profile {profile!r}.")
            exit(1)

    # Configure the output console after loading the profile
    app.setup_console(soft_wrap=PREFECT_CLI_WRAP_LINES.value(), prompt=prompt)

    if not PREFECT_TEST_MODE:
        # When testing, this entrypoint can be called multiple times per process which
        # can cause logging configuration conflicts. Logging is set up in conftest
        # during tests.
        setup_logging()

    # When running on Windows we need to ensure that the correct event loop policy is
    # in place or we will not be able to spawn subprocesses. Sometimes this policy is
    # changed by other libraries, but here in our CLI we should have ownership of the
    # process and be able to safely force it to be the correct policy.
    # https://github.com/PrefectHQ/prefect/issues/8206
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@app.command()
async def version():
    """Get the current prefect-dbt version"""

    version_info = {
        "Version": prefect_dbt.__version__,
        "Prefect version": prefect.__version__,
        "Python version": platform.python_version(),
        "OS/Arch": f"{sys.platform}/{platform.machine()}",
        "Profile": prefect.context.get_settings_context().profile.name,
    }

    try:
        pydantic_version = import_version("pydantic")
    except PackageNotFoundError:
        pydantic_version = "Not installed"

    version_info["Pydantic version"] = pydantic_version

    display(version_info)
