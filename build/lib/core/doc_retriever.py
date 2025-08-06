import subprocess
import requests
from requests import RequestException


def get_man_page(command: str) -> str | None:
    """
    Executes `man <command>` and captures the output.

    Args:
        command: The command to get the man page for.

    Returns:
        The man page as a string, or None if not found.
    """
    try:
        result = subprocess.run(
            ["man", command],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_help_output(command: str) -> str | None:
    """
    Executes `<command> --help` or `<command> -h` and captures the output.

    Args:
        command: The command to get the help output for.

    Returns:
        The help output as a string, or None if not found.
    """
    for flag in ["--help", "-h"]:
        try:
            result = subprocess.run(
                [command, flag],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


def get_online_docs(url: str) -> str | None:
    """
    Fetches online documentation from a URL.

    Args:
        url: The URL to fetch the documentation from.

    Returns:
        The documentation as a string, or None if there was an error.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
    except RequestException:
        return None
        return None


def format_documentation(title: str, content: str) -> str:
    """
    Formats the retrieved documentation for display.

    Args:
        title: The title for the documentation.
        content: The documentation content.

    Returns:
        The formatted documentation.
    """
    return f"--- {title} ---\n\n{content}"


class DocRetriever:
    def __init__(self, config):
        self.config = config

    def get_documentation(self, command: str) -> str:
        man_page = get_man_page(command)
        if man_page:
            return format_documentation(f"Man page for {command}", man_page)

        help_output = get_help_output(command)
        if help_output:
            return format_documentation(f"Help for {command}", help_output)

        return f"No documentation found for {command}"
