from pathlib import Path
import os
from demisto_sdk.commands.common.tools import print_error, print_warning, run_command_os, get_content_path

NO_HTML = '<!-- NOT_HTML_DOC -->'
YES_HTML = '<!-- HTML_DOC -->'


class ReadMeValidator:
    """ReadMeValidator is a validator for readme.md files
        In order to run the validator correctly please make sure:
        - Node is installed on you machine
        - make sure that the module '@mdx-js/mdx', 'fs-extra', 'commander' are installed in node-modules folder.
            If not installed, the validator will print a warning with the relevant module that is missing.
            please install it using "npm install *missing_module_name*"
        - 'DEMISTO_README_VALIDATION' environment variable should be set to True.
            To set the environment variables, run the following shell commands:
            export DEMISTO_README_VALIDATION=True
    """

    def __init__(self, file_path: str):
        self.content_path = get_content_path()
        self.file_path = Path(file_path)
        self.pack_path = self.file_path.parent
        self.node_modules_path = self.content_path / Path('node_modules')

    def is_valid_file(self) -> bool:
        """Check whether the readme file is valid or not
        Returns:
            bool: True if env configured else Fale.
        """
        if os.environ.get('DEMISTO_README_VALIDATION') or os.environ.get('CI'):
            return self.is_mdx_file()
        else:
            return True

    def is_mdx_file(self) -> bool:
        html = self.is_html_doc()
        valid = self.are_modules_installed_for_verify()
        if valid and not html:
            mdx_parse = Path(__file__).parent.parent / 'mdx-parse.js'
            # add to env var the directory of node modules
            os.environ['NODE_PATH'] = str(self.node_modules_path) + os.pathsep + os.getenv("NODE_PATH", "")
            # run the java script mdx parse validator
            _, stderr, is_valid = run_command_os(f'node {mdx_parse} -f {self.file_path}', cwd=self.content_path, env=os.environ)
            if is_valid:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {stderr}')
                return False
        return True

    def are_modules_installed_for_verify(self) -> bool:
        """ Check the following:
            1. npm packages installed - see packs var for specific pack details.
            2. node interperter exists.
        Returns:
            bool: True If all req ok else False
        """
        missing_module = []
        valid = True
        # Check node exist
        stdout, stderr, exit_code = run_command_os('node -v', cwd=self.content_path)
        if exit_code:
            print_warning(f'There is no node installed on the machine, Test Skipped, error - {stderr}, {stdout}')
            valid = False
        else:
            # Check npm modules exsits
            packs = ['@mdx-js/mdx', 'fs-extra', 'commander']
            for pack in packs:
                stdout, stderr, exit_code = run_command_os(f'npm ls {pack}', cwd=self.content_path)
                if exit_code:
                    missing_module.append(pack)
        if missing_module:
            valid = False
            print_warning(f"The npm modules: {missing_module} are not installed, Test Skipped, use "
                          f"'npm install <module>' to install all required node dependencies")
        return valid

    def is_html_doc(self) -> bool:
        txt = ''
        with open(self.file_path, 'r') as f:
            txt = f.read()
        if txt.startswith(NO_HTML):
            return False
        if txt.startswith(YES_HTML):
            return True
        # use some heuristics to try to figure out if this is html
        return txt.startswith('<p>') or ('<thead>' in txt and '<tbody>' in txt)
