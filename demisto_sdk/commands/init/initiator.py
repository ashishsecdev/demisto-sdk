import os
import shutil
import yaml
import yamlordereddictloader
import json
from datetime import datetime
from typing import Dict
from distutils.dir_util import copy_tree

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.tools import print_error, print_color, LOG_COLORS, get_common_server_path, print_v
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, \
    INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR, PLAYBOOKS_DIR, LAYOUTS_DIR, TEST_PLAYBOOKS_DIR, CLASSIFIERS_DIR, \
    CONNECTIONS_DIR, DASHBOARDS_DIR, MISC_DIR, REPORTS_DIR, WIDGETS_DIR, PACK_INITIAL_VERSION, INTEGRATION_CATEGORIES, \
    PACK_SUPPORT_OPTIONS


class Initiator:
    """Initiator creates a new pack/integration/script.

       Attributes:
           output (str): The directory in which init will create the new pack/integration/script
           name (str): The name for the new pack/integration/script directory.
           id (str): The id for the created script/integration.
           integration (bool): Indicates whether to create an integration.
           script (bool): Indicates whether to create a script.
           full_output_path (str): The full path to the newly created pack/integration/script
    """

    def __init__(self, output: str, name: str = '', id: str = '', integration: bool = False, script: bool = False,
                 pack: bool = False, demisto_mock: bool = False, common_server: bool = False):
        self.output = output if output else ''
        self.id = id

        self.is_integration = integration
        self.is_script = script
        self.is_pack = pack
        self.demisto_mock = demisto_mock
        self.common_server = common_server
        self.configuration = Configuration()

        # if no flag given automatically create a pack.
        if not integration and not script and not pack:
            self.is_pack = True

        self.full_output_path = ''

        if name is not None and len(name) != 0:
            while ' ' in name:
                name = str(input("The directory and file name cannot have spaces in it, Enter a different name: "))

        self.dir_name = name
        self.is_pack_creation = not all([self.is_script, self.is_integration])

    HELLO_WORLD_INTEGRATION = 'HelloWorld'
    HELLO_WORLD_SCRIPT = 'HelloWorldScript'
    PACK_TEMPLATE_FOLDER = 'PackData'
    PACK_METADATA_TEMPLATE = 'metadata_template.json'
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    PACK_INITIAL_VERSION = "1.0.0"

    DIR_LIST = [INTEGRATIONS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
                PLAYBOOKS_DIR, LAYOUTS_DIR, TEST_PLAYBOOKS_DIR, CLASSIFIERS_DIR, CONNECTIONS_DIR, DASHBOARDS_DIR,
                MISC_DIR, REPORTS_DIR, WIDGETS_DIR]

    def init(self):
        """Starts the init command process.

        """
        if self.is_integration:
            self.get_created_dir_name(created_object="integration")
            self.get_object_id(created_object="integration")
            return self.integration_init()

        elif self.is_script:
            self.get_created_dir_name(created_object="script")
            self.get_object_id(created_object="script")
            return self.script_init()

        elif self.is_pack:
            self.get_created_dir_name(created_object="pack")
            return self.pack_init()

    def get_created_dir_name(self, created_object: str):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        while not self.dir_name or len(self.dir_name) == 0:
            self.dir_name = str(input(f"Please input the name of the initialized {created_object}: "))
            while ' ' in self.dir_name:
                self.dir_name = str(input("The directory name cannot have spaces in it, Enter a different name: "))

    def get_object_id(self, created_object: str):
        if not self.id:
            if self.is_pack_creation:  # There was no option to enter the ID in this process.
                use_dir_name = str(input(f"Do you want to use the directory name as an "
                                         f"ID for the {created_object}? Y/N "))
            else:
                use_dir_name = str(input(f"No ID given for the {created_object}'s yml file. "
                                         f"Do you want to use the directory name? Y/N "))

            if use_dir_name and use_dir_name.lower() in ['y', 'yes']:
                self.id = self.dir_name
            else:
                while not self.id:
                    self.id = str(input(f"Please enter the id name for the {created_object}: "))

    def pack_init(self) -> bool:
        """Creates a pack directory tree.

        Returns:
            bool. Returns True if pack was created successfully and False otherwise
        """
        # if an output directory given create the pack there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # content-descriptor file indicates we are in "content" repository
        # thus we will create the pack under Packs directory
        elif os.path.isfile('content-descriptor.json'):
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if non of the above conditions apply - create the pack in current directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False
        for directory in self.DIR_LIST:
            path = os.path.join(self.full_output_path, directory)
            os.mkdir(path=path)

        with open(os.path.join(self.full_output_path, 'CHANGELOG.md'), 'a') as fp:
            fp.write("## [Unreleased]")

        fp = open(os.path.join(self.full_output_path, 'README.md'), 'a')
        fp.close()

        fp = open(os.path.join(self.full_output_path, '.secrets-ignore'), 'a')
        fp.close()

        fp = open(os.path.join(self.full_output_path, '.pack-ignore'), 'a')
        fp.close()

        print_color(f"Successfully created the pack {self.dir_name} in: {self.full_output_path}", LOG_COLORS.GREEN)

        metadata_path = os.path.join(self.full_output_path, 'pack_metadata.json')
        with open(metadata_path, 'a') as fp:
            user_response = input("\nDo you want to fill pack's metadata file? Y/N ").lower()
            fill_manually = user_response in ['y', 'yes']

            pack_metadata = Initiator.create_metadata(fill_manually)
            json.dump(pack_metadata, fp, indent=4)

            print_color(f"Created pack metadata at path : {metadata_path}", LOG_COLORS.GREEN)

        create_integration = str(input("\nDo you want to create an integration in the pack? Y/N ")).lower()
        if create_integration in ['y', 'yes']:
            integration_init = Initiator(output=os.path.join(self.full_output_path, 'Integrations'),
                                         integration=True, common_server=self.common_server,
                                         demisto_mock=self.demisto_mock)
            return integration_init.init()

        return True

    @staticmethod
    def create_metadata(fill_manually):
        metadata = {
            'name': '## FILL OUT MANUALLY ##',
            'description': '## FILL OUT MANUALLY ##',
            'support': 'demisto',
            'serverMinVersion': '## FILL OUT MANUALLY #',
            'currentVersion': PACK_INITIAL_VERSION,
            'author': 'demisto',
            'url': 'https://www.demisto.com',
            'email': '',
            'categories': [],
            'tags': [],
            'created': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
            'updated': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
            'beta': False,
            'deprecated': False,
            'certification': 'certified',
            'useCases': [],
            'keywords': [],
            'price': '0',
            'dependencies': {},
        }

        if not fill_manually:
            return metadata

        metadata['name'] = input("\nDisplay name of the pack: ")
        metadata['description'] = input("\nDescription of the pack: ")
        metadata['support'] = Initiator.get_valid_user_input(options_list=PACK_SUPPORT_OPTIONS,
                                                             option_message="\nSupport type of the pack: \n")
        metadata['serverMinVersion'] = input("\nServer min version: ")
        metadata['author'] = input("\nAuthor of the pack: ")

        support_url = input("\nThe url of support, should represent your GitHub account (optional): ")
        while support_url and "http" not in support_url:
            support_url = input("\nIncorrect input. Please enter full valid url: ")
        metadata['url'] = support_url

        metadata['email'] = input("\nThe email in which you can be contacted in: ")
        metadata['categories'] = [Initiator.get_valid_user_input(options_list=INTEGRATION_CATEGORIES,
                                                                 option_message="\nPack category options: \n")]
        tags = input("\nTags of the pack, comma separated values: ")
        tags_list = [t.strip() for t in tags.split(',')]
        metadata['tags'] = tags_list

        price = input("\nThe price of the pack: ")
        metadata['price'] = price

        return metadata

    @staticmethod
    def get_valid_user_input(options_list, option_message):
        for index, option in enumerate(options_list, start=1):
            option_message += f"[{index}] {option}\n"
        option_message += "\nEnter option: "

        user_choice = input(option_message)

        invalid_input = True
        while invalid_input:
            try:
                user_choice = int(user_choice)

                if user_choice not in range(1, len(options_list) + 1):
                    user_choice = input(f"\nInvalid option {user_choice}, please enter valid choice: ")
                else:
                    invalid_input = False
            except ValueError:
                user_choice = input("\nThe option must be integer, please enter valid choice: ")

        return options_list[user_choice - 1]

    @staticmethod
    def get_yml_data_as_dict(file_path: str) -> Dict:
        """Converts YML file data to Dict.

        Args:
            file_path (str): The path to the .yml file

        Returns:
            Dict. Data from YML.
        """
        with open(file_path) as f:
            return yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    def integration_init(self) -> bool:
        """Creates a new integration according to a template.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        # if output directory given create the integration there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the integration under the Integrations directory of the pack
        elif os.path.isdir(INTEGRATIONS_DIR):
            self.full_output_path = os.path.join('Integrations', self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'init', 'templates',
                                                         self.HELLO_WORLD_INTEGRATION))

        copy_tree(str(hello_world_path), self.full_output_path)
        if self.id != self.HELLO_WORLD_INTEGRATION:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.HELLO_WORLD_INTEGRATION)
            self.yml_reformatting(current_suffix=self.HELLO_WORLD_INTEGRATION, integration=True)
            self.fix_test_file_import(name_to_change=self.HELLO_WORLD_INTEGRATION)

        self.copy_common_server_python()
        self.copy_demistotmock()

        print_color(f"Finished creating integration: {self.full_output_path}.", LOG_COLORS.GREEN)

        return True

    def script_init(self) -> bool:
        """Creates a new script according to a template.

        Returns:
            bool. True if the script was created successfully, False otherwise.
        """
        # if output directory given create the script there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the script under the Scripts directory of the pack
        elif os.path.isdir(SCRIPTS_DIR):
            self.full_output_path = os.path.join('Scripts', self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'init', 'templates',
                                                         self.HELLO_WORLD_SCRIPT))

        copy_tree(str(hello_world_path), self.full_output_path)
        if self.id != self.HELLO_WORLD_SCRIPT:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.HELLO_WORLD_SCRIPT)
            self.yml_reformatting(current_suffix=self.HELLO_WORLD_SCRIPT)
            self.fix_test_file_import(name_to_change=self.HELLO_WORLD_SCRIPT)

        self.copy_common_server_python()
        self.copy_demistotmock()

        print_color(f"Finished creating script: {self.full_output_path}", LOG_COLORS.GREEN)

        return True

    def yml_reformatting(self, current_suffix: str, integration: bool = False):
        """Formats the given yml to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
            integration (bool): Indicates if integration yml is being reformatted.
        """
        yml_dict = self.get_yml_data_as_dict(file_path=os.path.join(self.full_output_path, f"{current_suffix}.yml"))
        yml_dict["commonfields"]["id"] = self.id
        yml_dict['name'] = self.id
        if integration:
            yml_dict["display"] = self.id

        with open(os.path.join(self.full_output_path, f"{self.dir_name}.yml"), 'w') as f:
            yaml.dump(
                yml_dict,
                f,
                Dumper=yamlordereddictloader.SafeDumper,
                default_flow_style=False)

        os.remove(os.path.join(self.full_output_path, f"{current_suffix}.yml"))

    def rename(self, current_suffix: str):
        """Renames the python, description, test and image file in the path to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}.py"),
                  os.path.join(self.full_output_path, f"{self.dir_name}.py"))
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}_description.md"),
                  os.path.join(self.full_output_path, f"{self.dir_name}_description.md"))
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}_test.py"),
                  os.path.join(self.full_output_path, f"{self.dir_name}_test.py"))
        if self.is_integration:
            os.rename(os.path.join(self.full_output_path, f"{current_suffix}_image.png"),
                      os.path.join(self.full_output_path, f"{self.dir_name}_image.png"))

    def create_new_directory(self, ) -> bool:
        """Creates a new directory for the integration/script/pack.

        Returns:
            bool. True if directory was successfully created, False otherwise.
        """
        try:
            os.mkdir(self.full_output_path)

        except FileExistsError:
            to_delete = str(input(f"The directory {self.full_output_path} "
                                  f"already exists.\nDo you want to overwrite it? Y/N ")).lower()
            while to_delete != 'y' and to_delete != 'n':
                to_delete = str(input(f"Your response was invalid.\nDo you want to delete it? Y/N ").lower())

            if to_delete in ['y', 'yes']:
                shutil.rmtree(path=self.full_output_path, ignore_errors=True)
                os.mkdir(self.full_output_path)

            else:
                print_error(f"Pack not created in {self.full_output_path}")
                return False

        return True

    def fix_test_file_import(self, name_to_change: str):
        """Fixes the import statement in the _test.py file in the newly created initegration/script

        Args:
            name_to_change (str): The name of the former integration/script to replace in the import.
        """
        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'r') as fp:
            file_contents = fp.read()

        file_contents = file_contents.replace(f'.{name_to_change}', self.dir_name)

        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'w') as fp:
            fp.write(file_contents)

    def copy_common_server_python(self):
        """copy commonserverpython from the base pack"""
        if self.common_server:
            try:
                common_server_path = get_common_server_path(self.configuration.env_dir)
                shutil.copy(common_server_path, self.full_output_path)
            except Exception as err:
                print_v(f'Could not copy CommonServerPython: {str(err)}')

    def copy_demistotmock(self):
        """copy demistomock from content"""
        if self.demisto_mock:
            try:
                shutil.copy(f'{self.configuration.env_dir}/Tests/demistomock/demistomock.py', self.full_output_path)
            except Exception as err:
                print_v(f'Could not copy demistomock: {str(err)}')
