import boto3
import configparser
import os.path

ssm = boto3.client('ssm')
config = configparser.ConfigParser()
local_file = False

if os.path.isfile('config.ini'):
  local_file = True
  config.read('config.ini')

  
def get_value(category, key, is_secret=False):
  if local_file:
    value = config[category][key]
    return value
  else:
    parameter_response = ssm.get_parameter(Name=f'/{category}/{key}', WithDecryption=is_secret)
    value = parameter_response['Parameter']['Value']
    return value
