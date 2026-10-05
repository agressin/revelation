"""Cli tool to handle revelation commands"""

import glob
import os
import shutil
import sys
import webbrowser
from functools import partial

import click
from geventwebsocket import Resource, WebSocketServer
from werkzeug.debug import DebuggedApplication

import revelation
from revelation import PresentationReloader, Revelation
from revelation.utils import (
    REVEAL_VERSION,
    install_reveal_plugin,
    install_revealjs,
    make_presentation,
    PLUGINS_URL
)
from revelation.convert_config import convert_config

REVEALJS_FOLDER = os.path.join(
    os.path.join(os.path.dirname(revelation.__file__), "static"), "revealjs"
)

# Hostnames that keep the server private to this machine
LOCAL_HOSTNAMES = ("localhost", "127.0.0.1", "::1")

# DRY form for echoing errors
error_echo = partial(click.secho, err=True, fg="red", bold=True)


def warn_if_py_config_newer(py_config, toml_config):
    """Warn when config.py was modified after config.toml

    config.toml always wins when both exist, so recent edits made in
    config.py would be silently ignored.
    """
    if not (os.path.isfile(py_config) and os.path.isfile(toml_config)):
        return False
    if os.path.getmtime(py_config) <= os.path.getmtime(toml_config):
        return False
    # Same values (e.g. both saved together): nothing is lost, stay quiet.
    # config.py is parsed with ast, never executed here.
    try:
        from pathlib import Path
        from revelation.config import Config
        from revelation.convert_config import extract_config_from_python
        py_values = extract_config_from_python(Path(py_config))
        toml_values = Config(toml_config)
        if all(
            toml_values.get(key) == value
            for key, value in py_values.items()
            if key in Config.ALLOWED_CONFIG_KEYS
        ):
            return False
    except Exception:
        pass  # unreadable file: warn anyway
    click.secho(
        f"⚠️  Warning: {py_config} is newer than {toml_config}.\n"
        f"   config.toml is used, changes made in config.py are ignored.\n"
        f"   If config.py is the up-to-date one, regenerate the TOML file "
        f"(overwrites it):\n"
        f"   $ revelation convertconfig {py_config} --force\n",
        err=True, fg="yellow",
    )
    return True


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, default=False)
@click.pass_context
def cli(ctx, version):
    """Base command function, it gets the context and passes it to
    its subcommands"""
    if not ctx.invoked_subcommand and version:
        click.echo(revelation.__version__)
        ctx.exit()
    elif not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@cli.command("installreveal", help="Install or upgrade reveal.js dependency")
@click.option(
    "--url",
    "-u",
    help="Reveal.js download url (npm .tgz). Default: npm registry, pinned version"
)
@click.option(
    "--version", "-v", default=REVEAL_VERSION, show_default=True,
    help="Reveal.js version"
)
def installreveal(url, version):
    """Reveal.js installation command

    Downloads the pinned reveal.js npm package (dist/ and plugin/), checks its
    integrity, and installs it flat into revelation/static/revealjs.
    Run heig/install.sh afterwards to add the HEIG theme, logos and plugins.
    """
    click.echo(f"Downloading reveal.js {version}...")
    try:
        install_revealjs(REVEALJS_FOLDER, version=version, url=url)
    except RuntimeError as e:
        error_echo(str(e))
        raise SystemExit(1)
    click.echo("Installed reveal.js to " + REVEALJS_FOLDER)
    click.echo("Next: heig/install.sh (HEIG theme, logos, plugins)")


@cli.command("installrevealplugin", help="Install or upgrade reveal.js plugin")
@click.option(
    "--plugin",
    "-p",
    help="Choose plugin ("+", ".join(PLUGINS_URL)+")"
    + " or all to install all available plugins"
)
@click.option(
    "--url",
    "-u",
    help="Reveal.js plugin download url (link to zip or tar.gz)"
)
def installrevealplugin(url, plugin):
    """Reveal.js plugin installation command

    Receives the download url to install from a specific version or
    downloads the latest version if noting is passed
    """

    if plugin == "all":
        click.echo("Downloading ALL reveal.js plugin...")
        for plugin in PLUGINS_URL:
            click.echo(plugin)
            install_reveal_plugin(url, plugin, REVEALJS_FOLDER)
    else:
        click.echo("Downloading reveal.js plugin...")
        install_reveal_plugin(url, plugin, REVEALJS_FOLDER)

    click.echo("Installation completed!")


@cli.command("mkpresentation", help="Create a new revelation presentation")
@click.argument("presentation")
@click.pass_context
def mkpresentation(ctx, presentation):
    """Make presentation project boilerplate"""

    if os.path.exists(presentation):
        error_echo("Error: '{}' already exists.".format(presentation))
        ctx.exit(1)

    click.echo("Starting a new presentation...")

    make_presentation(presentation)


@cli.command("mkstatic", help="Make a static presentation")
@click.argument("presentation", default=os.getcwd())
@click.option("--config", "-c", default=None, help="Custom configuration file")
@click.option("--media", "-m", default=None, help="Custom media folder")
@click.option("--theme", "-t", default=None, help="Custom theme folder")
@click.option(
    "--style-override-file",
    "-s",
    "style",
    default=None,
    help="Custom css file to override reveal.js styles",
)
@click.option(
    "--output-folder",
    "-o",
    default="output",
    help="Folder where the static presentation will be generated",
)
@click.option(
    "--output-file",
    "-f",
    default="index.html",
    help="File name of the static presentation",
)
@click.option(
    "--force", "-r", is_flag=True, help="Overwrite the output folder if exists"
)
@click.pass_context
def mkstatic(
    ctx,
    presentation,
    config,
    media,
    theme,
    output_folder,
    output_file,
    force,
    style,
):
    """Make static presentation"""

    # Check if reveal.js is installed: no silent download at start
    if not os.path.exists(os.path.join(REVEALJS_FOLDER, "reveal.js")):
        error_echo(f"reveal.js not found in {REVEALJS_FOLDER}")
        error_echo("Run heig/bootstrap.sh (or: revelation installreveal && heig/install.sh)")
        ctx.exit(1)

    output_folder = os.path.realpath(output_folder)

    # Check for style override file
    if os.path.isfile(output_folder):
        error_echo(
            "Error: '{}' already exists and is a file.".format(output_folder)
        )
        ctx.exit(1)

    # Check for presentation file
    if os.path.isfile(presentation):
        path = os.path.dirname(presentation)
    elif os.path.isdir(presentation):
        path = presentation
    else:
        error_echo("Error: Presentation file / dir not found.")
        ctx.exit(1)

    if style and (not os.path.isfile(style) or not style.endswith(".css")):
        click.echo("Error: Style is not a css file or does not exists.")
        ctx.exit(1)

    if os.path.isdir(output_folder):
        if force:
            shutil.rmtree(output_folder)
        else:
            error_echo(
                (
                    "Error: '{}' already exists, use --force to override it."
                ).format(output_folder)
            )
            ctx.exit(1)

    staticfolder = os.path.join(output_folder, "static")

    # make the output path
    os.makedirs(output_folder)

    # if has override style copy
    if style:
        shutil.copy(
            style, os.path.join(output_folder, os.path.basename(style))
        )

    shutil.copytree(REVEALJS_FOLDER, os.path.join(staticfolder, "revealjs"))

    # Check for media root
    if not media:
        media = os.path.realpath(os.path.join(path, "media"))
    else:
        media = os.path.realpath(media)

    if not os.path.isdir(media):
        # Running without media folder
        media = None
        click.echo("Media folder not detected, running without media.")
    else:
        shutil.copytree(media, os.path.join(output_folder, "media"))

    # Check for theme root
    if not theme:
        theme = os.path.join(path, "theme")

    if not os.path.isdir(theme):
        # Running without theme folder
        theme = None
        click.echo("Theme not detected, running without custom theme.")
    else:
        shutil.copytree(theme, os.path.join(output_folder, "theme"))

    # Check for configuration file (prefer TOML over Python)
    if not config:
        toml_config = os.path.join(path, "config.toml")
        py_config = os.path.join(path, "config.py")

        if os.path.isfile(toml_config):
            config = toml_config
            warn_if_py_config_newer(py_config, toml_config)
        elif os.path.isfile(py_config):
            config = py_config
            click.echo("\n⚠️  Note: Using deprecated Python config. Consider converting to TOML.")
            click.echo(f"   Run: revelation convertconfig {py_config}\n")
        else:
            config = None
            click.echo("Configuration file not detected, running with defaults.")

    click.echo("Generating static presentation...")

    # instantiating revelation app
    app = Revelation(presentation, config, media, theme, style)

    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    output_file = os.path.join(output_folder, output_file)

    with open(output_file, "wb") as f:
        f.write(
            app.dispatch_request(None).get_data(as_text=True).encode("utf-8")
        )

    click.echo(
        "Static presentation generated in {}".format(
            os.path.realpath(output_folder)
        )
    )


@cli.command("convertconfig", help="Convert Python config to TOML format")
@click.argument("python_config")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output TOML file (default: same name with .toml extension)"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite output file if it exists"
)
@click.pass_context
def convertconfig(ctx, python_config, output, force):
    """Convert Python config file to secure TOML format"""
    from pathlib import Path

    python_file = Path(python_config)
    output_file = Path(output) if output else None

    if not python_file.exists():
        error_echo(f"Error: Config file not found: {python_config}")
        ctx.exit(1)

    click.echo(f"Converting {python_config} to TOML format...")

    if convert_config(python_file, output_file, force):
        click.echo("Conversion completed successfully!")
    else:
        error_echo("Conversion failed. See error messages above.")
        ctx.exit(1)


@cli.command("start", help="Start the revelation server")
@click.argument("presentation", default=os.getcwd())
@click.option("--port", "-p", default=4000, help="Presentation server port")
@click.option("--config", "-c", default=None, help="Custom configuration file")
@click.option("--media", "-m", default=None, help="Custom media folder")
@click.option("--theme", "-t", default=None, help="Custom theme folder")
@click.option(
    "--style-override-file",
    "-s",
    "style",
    default=None,
    help="Custom css file to override reveal.js styles",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    default=False,
    help="Run the revelation server on debug mode",
)
@click.option("--hostname", "-h", default="localhost", help="Presentation server hostname")
@click.option(
    "--no-browser",
    "no_browser",
    is_flag=True,
    default=False,
    help="Do not open the presentation in a web browser",
)
@click.pass_context
def start(ctx, presentation, port, config, media, theme, style, debug, hostname,
          no_browser):
    """Start revelation presentation command"""
    # Check if reveal.js is installed: no silent download at start
    if not os.path.exists(os.path.join(REVEALJS_FOLDER, "reveal.js")):
        error_echo(f"reveal.js not found in {REVEALJS_FOLDER}")
        error_echo("Run heig/bootstrap.sh (or: revelation installreveal && heig/install.sh)")
        ctx.exit(1)

    # Check for presentation file
    if os.path.isfile(presentation):
        path = os.path.dirname(presentation)
        if not presentation.endswith('.md'):
            click.echo(f"\n⚠️  Warning: File '{presentation}' does not have .md extension.")
            click.echo("   Revelation expects markdown files with .md extension.\n")
    elif os.path.isdir(presentation):
        path = presentation
        # Check if directory contains any .md files
        md_files = glob.glob(os.path.join(presentation, "*.md"))
        if not md_files:
            error_echo(f"\n✗ Error: No markdown files (.md) found in '{presentation}'")
            click.echo("\nTo create a new presentation:")
            click.echo(f"  $ revelation mkpresentation {os.path.basename(presentation)}\n")
            ctx.exit(1)
    else:
        error_echo(f"\n✗ Error: Presentation not found: '{presentation}'")
        click.echo("\nThe path must be either:")
        click.echo("  • A markdown file (.md)")
        click.echo("  • A directory containing .md files")
        click.echo("\nTo create a new presentation:")
        click.echo(f"  $ revelation mkpresentation my_presentation\n")
        ctx.exit(1)

    # Check for style override file
    if style:
        if not os.path.isfile(style):
            error_echo(f"\n✗ Error: Style file not found: '{style}'")
            ctx.exit(1)
        if not style.endswith(".css"):
            error_echo(f"\n✗ Error: Style file must be a .css file, got: '{style}'")
            ctx.exit(1)

    # Check for media root
    if not media:
        media = os.path.join(path, "media")

    if not os.path.isdir(media):
        # Running without media folder
        media = None

        click.echo("Media folder not detected, running without media")

    # Check for theme root
    if not theme:
        theme = os.path.join(path, "theme")

    if not os.path.isdir(theme):
        # Running without theme folder
        theme = None

    # Check for configuration file (prefer TOML over Python)
    if not config:
        toml_config = os.path.join(path, "config.toml")
        py_config = os.path.join(path, "config.py")

        if os.path.isfile(toml_config):
            config = toml_config
            warn_if_py_config_newer(py_config, toml_config)
        elif os.path.isfile(py_config):
            config = py_config
            # Suggest conversion from Python to TOML
            click.echo("\n⚠️  WARNING: Python config files are deprecated!")
            click.echo("   For security reasons, please convert to TOML format.")
            click.echo(f"\n   Quick conversion:")
            click.echo(f"   $ revelation convertconfig {py_config}\n")

            # Only ask when someone can answer: a non-interactive launch
            # (script, editor, background) keeps the default (no conversion)
            if sys.stdin.isatty() and click.confirm(
                "Would you like to convert now?", default=False
            ):
                from pathlib import Path
                if convert_config(Path(py_config), Path(toml_config), force=False):
                    click.echo(f"\n✓ Converted to {toml_config}")
                    click.echo("  Using new TOML config...\n")
                    config = toml_config
                else:
                    click.echo("\n✗ Conversion failed, using Python config")
        else:
            config = None
            click.echo("Configuration file not detected, running with defaults.")

    click.echo("Starting revelation server...")

    # instantiating revelation app
    try:
        app = Revelation(presentation, config, media, theme, style, True)
    except Exception as e:
        error_echo(f"\n✗ Error initializing presentation: {e}")
        click.echo("\nPlease check:")
        click.echo("  • Presentation files are valid markdown")
        click.echo("  • Configuration file syntax is correct")
        click.echo("  • All paths are accessible\n")
        ctx.exit(1)

    if debug:
        # Interactive debugger: never expose it beyond localhost
        app = DebuggedApplication(app)

    PresentationReloader.tracking_path = os.path.abspath(path)

    server_url = f"http://{hostname}:{port}"
    click.echo(f"\n✓ Server starting at {server_url}")
    click.echo(f"  Press Ctrl+C to stop\n")

    if hostname not in LOCAL_HOSTNAMES:
        click.secho(
            f"⚠️  Warning: listening on '{hostname}', the presentation (and its "
            "folder) is reachable from the network.",
            err=True, fg="yellow",
        )
        if debug:
            click.secho(
                "   --debug exposes an interactive debugger (code execution) "
                "to the network!",
                err=True, fg="red", bold=True,
            )
        click.secho("   Use -h localhost to keep it local.\n", err=True, fg="yellow")

    # Try to open browser, but don't fail if it doesn't work
    if not no_browser:
        try:
            webbrowser.open(server_url, new=2)
        except Exception as e:
            click.echo(f"⚠️  Could not open browser automatically: {e}")
            click.echo(f"   Please open {server_url} manually\n")

    try:
        WebSocketServer(
            (hostname, port),
            Resource(
                [
                    ("^/reloader.*", PresentationReloader),
                    ("^/.*", app),
                ]
            ),
        ).serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            error_echo(f"\n✗ Error: Port {port} is already in use")
            click.echo(f"\nTry using a different port:")
            click.echo(f"  $ revelation start {presentation} --port {port + 1}\n")
        else:
            error_echo(f"\n✗ Server error: {e}\n")
        ctx.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n✓ Server stopped gracefully")
        ctx.exit(0)
