import os
import os.path
import configparser
from typing import Optional

import boto3


class ConfigProvider:
    def __init__(self, config_file_path: str = "./config.ini"):
        self.ssm = boto3.client("ssm")
        self.config_parser = configparser.ConfigParser()
        self.local_file = os.path.isfile(config_file_path)

        if self.local_file:
            print("Using local config file")
            self.config_parser.read(config_file_path)

    def get_value(self, category: str, key: str, is_secret: bool = False) -> str:
        if self.local_file:
            return self.config_parser.get(category, key)
        else:
            parameter_name = f"/{category}/{key}"
            return self._get_ssm_parameter(parameter_name, is_secret)

    def _get_ssm_parameter(self, parameter_name: str, is_secret: bool) -> str:
        parameter_response = self.ssm.get_parameter(Name=parameter_name, WithDecryption=is_secret)
        return parameter_response["Parameter"]["Value"]