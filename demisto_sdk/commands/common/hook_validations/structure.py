"""Structure Validator for Demisto files

Module contains validation of schemas, ids and paths.
"""
import json
import os
import re
import logging

from typing import Optional

import yaml
from pykwalify.core import Core

from demisto_sdk.commands.common.constants import Errors, ACCEPTED_FILE_EXTENSIONS, FILE_TYPES_PATHS_TO_VALIDATE, \
    SCHEMA_TO_REGEX
from demisto_sdk.commands.common.tools import get_remote_file, get_matching_regex, print_error
from demisto_sdk.commands.common.configuration import Configuration


class StructureValidator:
    """Structure validator is designed to validate the correctness of the file structure we enter to content repo.

        Attributes:
            file_path (str): the path to the file we are examining at the moment.
            is_valid (bool): the attribute which saves the valid/in-valid status of the current file. will be bool only
                             after running is_file_valid.
            scheme_name (str): Name of the yaml scheme need to validate.
            file_type (str): equal to scheme_name if there's a scheme.
            current_file (dict): loaded json.
            old_file: (dict) loaded file from git.
        """
    SCHEMAS_PATH = "schemas"

    FILE_SUFFIX_TO_LOAD_FUNCTION = {
        '.yml': yaml.safe_load,
        '.json': json.load,
    }

    def __init__(self, file_path, is_new_file=False, old_file_path=None, predefined_scheme=None,
                 configuration=Configuration()):
        # type: (str, Optional[bool], Optional[str], Optional[str], Configuration) -> None
        self.is_valid = True
        self.file_path = file_path.replace('\\', '/')
        self.scheme_name = predefined_scheme or self.scheme_of_file_by_path()
        self.file_type = self.get_file_type()
        self.current_file = self.load_data_from_file()
        if is_new_file or predefined_scheme:
            self.old_file = {}
        else:
            self.old_file = get_remote_file(old_file_path if old_file_path else file_path)
        self.configuration = configuration

    def is_valid_file(self):
        # type: () -> bool
        """Checks if given file is valid

        Returns:
            (bool): Is file is valid
        """
        answers = [
            self.is_valid_file_path(),
            self.is_valid_scheme(),
            self.is_file_id_without_slashes(),
        ]

        if self.old_file:  # In case the file is modified
            answers.append(not self.is_id_modified())
            answers.append(self.is_valid_fromversion_on_modified())

        return all(answers)

    def scheme_of_file_by_path(self):
        # type:  () -> Optional[str]
        """Running on given regexes from `constants` to find out what type of file it is

        Returns:
            (str): Type of file by scheme name
        """

        for scheme_name, regex_list in SCHEMA_TO_REGEX.items():
            if get_matching_regex(self.file_path, regex_list):
                return scheme_name

        pretty_formatted_string_of_regexes = json.dumps(SCHEMA_TO_REGEX, indent=4, sort_keys=True)

        print_error(f"The file {self.file_path} does not match any scheme we have please, refer to the following list"
                    f" for the various file name options we have in our repo {pretty_formatted_string_of_regexes}")
        return None

    def is_valid_scheme(self):
        # type: () -> bool
        """Validate the file scheme according to the scheme we have saved in SCHEMAS_PATH.

        Returns:
            bool. Whether the scheme is valid on self.file_path.
        """
        if self.scheme_name in [None, 'image', 'readme', 'changelog']:
            return True
        try:
            # disabling massages of level INFO and beneath of pykwalify such as: INFO:pykwalify.core:validation.valid
            log = logging.getLogger('pykwalify.core')
            log.setLevel(logging.WARNING)
            path = os.path.normpath(
                os.path.join(__file__, "..", "..", self.SCHEMAS_PATH, '{}.yml'.format(self.scheme_name)))
            core = Core(source_file=self.file_path,
                        schema_files=[path])
            core.validate(raise_exception=True)
        except Exception as err:
            try:
                print_error(self.parse_error_msg(err))
            except Exception:
                print_error('Failed: {} failed.\nin {}'.format(self.file_path, str(err)))
            self.is_valid = False
            return False
        return True

    @staticmethod
    def get_file_id_from_loaded_file_data(loaded_file_data):
        # type: (dict) -> Optional[str]
        """Gets a dict and extracting its `id` field

        Args:
            loaded_file_data: Data to find dict

        Returns:
            (str or None): file ID if exists.
        """
        try:
            file_id = loaded_file_data.get('id')
            if not file_id:
                # In integrations/scripts, the id is under 'commonfields'.
                file_id = loaded_file_data.get('commonfields', {}).get('id', '')
            if not file_id:
                # In layout, the id is under 'layout'.
                file_id = loaded_file_data.get('layout', {}).get('id', '')

            return file_id
        except AttributeError:
            return None

    def is_file_id_without_slashes(self):
        # type: () -> bool
        """Check if the ID of the file contains any slashes ('/').

        Returns:
            bool. Whether the file's ID contains slashes or not.
        """
        file_id = self.get_file_id_from_loaded_file_data(self.current_file)
        if file_id and '/' in file_id:
            self.is_valid = False
            print_error(Errors.file_id_contains_slashes())
            return False

        return True

    def is_id_modified(self):
        # type: () -> bool
        """Check if the ID of the file has been changed.


        Returns:
            (bool): Whether the file's ID has been modified or not.
        """
        if not self.old_file:
            return False

        old_version_id = self.get_file_id_from_loaded_file_data(self.old_file)
        new_file_id = self.get_file_id_from_loaded_file_data(self.current_file)
        if not (new_file_id == old_version_id):
            print_error(f"The file id for {self.file_path} has changed from {old_version_id} to {new_file_id}")
            return True

        # False - the id has not changed.
        return False

    def is_valid_fromversion_on_modified(self):
        # type: () -> bool
        """Check that the fromversion property was not changed on existing Content files.

        Returns:
            (bool): Whether the files' fromversion as been modified or not.
        """
        if not self.old_file:
            return True

        from_version_new = self.current_file.get("fromversion") or self.current_file.get("fromVersion")
        from_version_old = self.old_file.get("fromversion") or self.old_file.get("fromVersion")

        if from_version_old != from_version_new:
            print_error(Errors.from_version_modified(self.file_path))
            self.is_valid = False
            return False

        return True

    def load_data_from_file(self):
        # type: () -> dict
        """Loads data according to function defined in FILE_SUFFIX_TO_LOAD_FUNCTION
        Returns:
             (dict)
        """
        file_extension = os.path.splitext(self.file_path)[1]
        if file_extension in ACCEPTED_FILE_EXTENSIONS:
            if file_extension in self.FILE_SUFFIX_TO_LOAD_FUNCTION:
                load_function = self.FILE_SUFFIX_TO_LOAD_FUNCTION[file_extension]
                with open(self.file_path, 'r') as file_obj:
                    loaded_file_data = load_function(file_obj)  # type: ignore
                    return loaded_file_data

            # Ignore loading image and markdown
            elif file_extension in ['.png', '.md']:
                return {}

        print_error(Errors.wrong_file_extension(file_extension, self.FILE_SUFFIX_TO_LOAD_FUNCTION.keys()))
        return {}

    def get_file_type(self):
        # type: () -> Optional[str]
        """Gets file type based on regex or scheme_name

        Returns:
            str if valid filepath, else None
        """
        # If scheme_name exists, already found that the file is in the right path
        if self.scheme_name:
            return self.scheme_name

        for file_type, regexes in FILE_TYPES_PATHS_TO_VALIDATE.items():
            for regex in regexes:
                if re.search(regex, self.file_path, re.IGNORECASE):
                    return file_type
        return None

    def is_valid_file_path(self):
        """Returns is valid filepath exists.

        Can be only if file_type or scheme_name exists (runs from init)

        Returns:
            True if valid file path else False
        """
        is_valid_path = bool(self.scheme_name or self.file_type)
        if not is_valid_path:
            print_error(Errors.invalid_file_path(self.file_path))
        return is_valid_path

    def parse_error_msg(self, err) -> str:
        """A wrapper which runs the print error message for a list of errors in yaml
        Returns:
            parsed error message from pykwalify
        """
        if ".\n" in str(err):
            for error in str(err).split('.\n'):
                return self.parse_error_line(error)
        else:
            return self.parse_error_line(str(err))

    def parse_error_line(self, err) -> str:
        """Returns a parsed error message from pykwalify
        Args: an schema error message from pykwalify
        """
        # err example: '<SchemaError: error code 2: Schema validation failed:
        #  - Cannot find required key \'description\'. Path: \'\''
        step_1 = str(err).split('Path: ')
        # step_1 example: ["<SchemaError: error code 2: Schema validation failed:\n - Cannot find required key
        # 'description'. ", "'/script/commands/0/outputs/20'.: ", "'/'>"]
        step_2 = step_1[1]
        # step_2 example: '\'/script/commands/0/outputs/20\'.: '
        step_3 = step_2[2:-4]
        # step_3 example: 'script/commands/0/outputs/20'
        error_path = step_3.split('/')
        # error_path example: ['script', 'commands', '0', 'outputs', '20']

        # check if the Path from the error is '' :
        if isinstance(error_path, list) and error_path[0]:
            curr = self.current_file
            key_from_error = str(err).split('key')[1].split('.')[0].replace("'", '-').split('-')[1]
            key_list = []
            for single_path in error_path:
                if type(curr) is list:
                    curr = curr[int(single_path)]
                    # if the error is from arguments of file
                    if curr.get('name'):
                        key_list.append(curr.get('name'))
                    # if the error is from outputs of file
                    elif curr.get('contextPath'):
                        key_list.append(curr.get('contextPath'))
                else:
                    curr = curr.get(single_path)
                    key_list.append(single_path)

            # if the error is from arguments of file
            if curr.get('name'):
                return ('Failed: {} failed.\nMissing {} in {}, Path: {}'.format(self.file_path, str(key_from_error),
                                                                                str(curr.get('name')),
                                                                                str(key_list).strip('[]').replace(
                                                                                    ',', '->')))
            # if the error is from outputs of file
            elif curr.get('contextPath'):
                return ('Failed: {} failed.\nMissing {} in {}, Path: {}'.format(self.file_path, str(key_from_error),
                                                                                str(curr.get('contextPath')),
                                                                                str(key_list).strip('[]').replace(
                                                                                    ',', '->')))
            # if the error is from neither arguments , outputs nor root
            else:
                return (
                    'Failed: {} failed.\nMissing {} in {}, Path: {}'.format(self.file_path, str(key_from_error),
                                                                            str(curr),
                                                                            str(key_list).strip('[]').replace(',',
                                                                                                              '->')))
        else:
            if 'key' in str(err):
                key_from_error = str(err).split('key')[1].split('.')[0].replace("'", '-').split('-')[1]
            else:
                key_from_error = str(err).split('Key')[1].split('.')[0].replace("'", '-').split('-')[1]
            return (
                'Failed: {} failed.\nMissing {} in {}'.format(self.file_path, str(key_from_error), "root",
                                                              ))
