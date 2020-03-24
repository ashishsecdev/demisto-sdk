# STD python packages
from pathlib import Path
from typing import List
import os
# Third party packages
# Local imports

excluded_files = ["CommonServerPython.py", "demistomock.py", "CommonServerUserPython.py", "conftest.py", "venv"]


def build_flake8_command(files: List[Path]) -> str:
    """ Build command for executing flake8 lint check
        https://flake8.pycqa.org/en/latest/user/invocation.html
    Args:
        files(List[Path]): files to execute lint

    Returns:
        str: flake8 command
    """
    max_line_len = 130
    # Ignoring flake specific errors https://flake8.pycqa.org/en/latest/user/error-codes.html
    errors_ignoring = ["W293", "W504", "W291", "W605", "F405", "F403", "E999", "W503", "F841", "E302", "C901", "F821",
                       "E402"]
    command = "python3 -m flake8"
    # Max allowed line lenth in python modules
    command += f" --max-line-length {max_line_len}"
    # Ignoring flake8 specific errors https://flake8.pycqa.org/en/latest/user/error-codes.html
    command += f" --ignore={','.join(errors_ignoring)}"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # Generating file pattrens - path1,path2,path3,..
    files = [str(file) for file in files]
    command += ' ' + ' '.join(files)

    return command


def build_bandit_command(files: List[Path]) -> str:
    """ Build command for executing bandit lint check
        https://github.com/PyCQA/bandit
    Args:
        files(List(Path)):  files to execute lint

    Returns:
        str: bandit command
    """
    command = "python3 -m bandit"
    # Only reporting on the high-severity issues
    command += " -lll"
    # report only issues of a given confidence level HIGH
    command += " -iii"
    # Aggregate output by filename
    command += " -a file"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # only show output in the case of an error
    command += f" -q"
    # Generating path pattrens - path1,path2,path3,..
    files = [str(item) for item in files]
    command += f" -r {','.join(files)}"

    return command


def build_mypy_command(files: List[Path], version: float) -> str:
    """ Build command to execute with mypy module
        https://mypy.readthedocs.io/en/stable/command_line.html
    Args:
        files(List[Path]): files to execute lint
        version(float): python varsion X.Y (3.7, 2.7 ..)

    Returns:
        str: mypy command
    """
    command = "python3 -m mypy"
    # Define python versions
    command += f" --python-version {version}"
    # This flag enable type checks the body of every function, regardless of whether it has type annotations.
    command += " --check-untyped-defs"
    # This flag makes mypy ignore all missing imports.
    command += " --ignore-missing-imports"
    # This flag adjusts how mypy follows imported modules that were not explicitly passed in via the command line
    command += " --follow-imports=silent"
    # This flag will add column offsets to error messages.
    command += " --show-column-numbers"
    # This flag will precede all errors with “note” messages explaining the context of the error.
    command += " --show-error-codes"
    # Use visually nicer output in error messages
    command += " --pretty"
    # This flag enables redefinion of a variable with an arbitrary type in some contexts.
    command += " --allow-redefinition"
    # Disable cache creation
    command += " --cache-dir=/dev/null"
    # Generating path pattrens - file1 file2 file3,..
    files = [str(item) for item in files]
    command += " " + " ".join(files)

    return command


def build_vulture_command(files: List[Path], pack_path: Path, version: float) -> str:
    """ Build command to execute with pylint module
        https://github.com/jendrikseipp/vulture
    Args:
        files(List[Path]): files to execute lint
        pack_path(Path): Package path

    Returns:
       str: vulture command
    """
    if version < 3:
        version = ""
    else:
        version = 3
    command = f"python{version} -m vulture"
    # Excluded files
    command += f" --min-confidence {os.environ.get('VULTURE_MIN_CONFIDENCE_LEVEL', '100')}"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # Whitelist vulture
    whitelist = Path(pack_path) / '.vulture_whitelist.py'
    if whitelist.exists():
        command += f" {whitelist}"
    files = [str(item) for item in files]
    command += " " + " ".join(files)

    return command


def build_pylint_command(files: List[Path]) -> str:
    """ Build command to execute with pylint module
        https://docs.pylint.org/en/1.6.0/run.html#invoking-pylint
    Args:
        files(List[Path]): files to execute lint

    Returns:
       str: pylint command
    """
    command = "python -m pylint"
    # Excluded files
    command += f" --ignore={','.join(excluded_files)}"
    # Prints only errors
    command += " -E"
    # Disable specific errors
    command += " -d duplicate-string-formatting-argument"
    # Message format
    command += " --msg-template='{path} ({line}): {msg}'"
    # List of members which are set dynamically and missed by pylint inference system, and so shouldn't trigger
    # E1101 when accessed.
    command += " --generated-members=requests.packages.urllib3,requests.codes.ok"
    # Generating path pattrens - file1 file2 file3,..
    files = [file.name for file in files]
    command += " " + " ".join(files)

    return command


def build_pytest_command(test_xml: str = "", json: bool = False) -> str:
    """ Build command to execute with pytest module
        https://docs.pytest.org/en/latest/usage.html
    Args:
        test_xml(str): path indicate if required or not
        json(bool): Define json creation after test

    Returns:
        str: pytest command
    """
    command = "python -m pytest"
    # Generating junit-xml report - used in circle ci
    if test_xml:
        command += f" --junitxml=/devwork/report_pytest.xml"
    # Generating json report
    if json:
        command += f" --json=/devwork/report_pytest.json"

    return command


def build_pwsh_analyze_command(files: List[Path]) -> str:
    """ Build command for powershell analyze

    Args:
        files(List[Path]): files to execute lint

    Returns:
       str: pylint command
    """
    command = "Invoke-ScriptAnalyzer"
    # Return exit code when finished
    command += " -EnableExit"
    # Files to analyze
    files = [file.name for file in files]
    command += f" -Path={' '.join(files)}"
    # Wrap with quotes
    command = f'\"{command}\"'

    return command


def build_pwsh_test_command() -> str:
    """ Build command for powershell test

    Returns:
       str: pylint command
    """
    command = "Invoke-Pester"
    # Return exit code when finished
    command += " -EnableExit"
    # Wrap with quotes
    command = f'\"{command}\"'

    return command