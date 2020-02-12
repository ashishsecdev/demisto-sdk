# STD python packages

# Third party packages

# Local imports

excluded_files = ["CommonServerPython.py", "demistomock.py", "CommonServerUserPython.py", "conftest.py", "venv"]


def build_flak8_command(files: str) -> str:
    """
        Build command for executing flake8 lint check
    Args:
        files

    Returns:
        flake8 command
    """
    max_line_len = 130
    # Ignoring flake specific errors https://flake8.pycqa.org/en/latest/user/error-codes.html
    errors_ignoring = ["W293", "W504", "W291", "W605", "F405", "F403", "E999", "W503", "F841", "E302", "C901", "F821"]
    command = "flake8"
    # Max allowed line lenth in python modules
    command += f" --max-line-length {max_line_len}"
    # Ignoring flake8 specific errors https://flake8.pycqa.org/en/latest/user/error-codes.html
    command += f" --ignore={','.join(errors_ignoring)}"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # Format
    command += "--format '%(file)s:%(row)d:%(col)d: %(code)s %(text)s'"
    # Generating file pattrens - path1,path2,path3,..
    command += f" {files}"

    return command


def build_bandit_command(files: str) -> str:
    """
        Build command for executing bandit lint check
    Args:

    Returns:
        bandit command
    """
    command = "bandit"
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
    # # Create html report if specified
    # if report_dir:
    #     command += f" --format=html --o {os.path.join(report_dir, f'lints/bandit/index.html')}"
    # Generating path pattrens - path1,path2,path3,..
    command += f" -r {files}"

    return command


def build_mypy_command(files: str, version) -> str:
    """
        Build command to execute with mypy module
        https://mypy.readthedocs.io/en/stable/command_line.html
    Args:
        files: list of pkgs to run flake8
        version

    Returns:
        mypy command
    """
    command = "mypy"
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
    # Generating path pattrens - file1 file2 file3,..
    command += f" {files}"

    return command


def build_pylint_command(files) -> str:
    """
        Build command to execute with pylint module
        https://docs.pylint.org/en/1.6.0/features.html
    Args:
        files: list of files to run pylint

    Returns:
        pylint command
    """
    command = "python -m pylint"
    # Excluded files
    command += f" --ignore={','.join(excluded_files)}"
    # Prints only errors
    command += " -E "
    # Disable specific errors
    command += " -d duplicate-string-formatting-argument"
    # Message format
    command += " --msg-template='{path} ({line}): {msg}'"
    # List of members which are set dynamically and missed by pylint inference system, and so shouldn't trigger
    # E1101 when accessed.
    command += " --generated-members=requests.packages.urllib3,requests.codes.ok"
    # Generating path pattrens - file1 file2 file3,..
    command += f" {files}"

    return command


def build_pytest_command() -> str:
    """
        Build command to execute with pytest module
        https://docs.pytest.org/en/latest/usage.html

    Returns:
        pytest command
    """
    command = "pytest"
    # One line per failure
    command += " -q --tb=line"
    # Generating path pattrens - file1 file2 file3,..
    command += f""

    return command
