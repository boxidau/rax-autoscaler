from __future__ import print_function
import os, pyrax, sys
import pyrax.exceptions as pexc
from termcolor import colored
import ConfigParser
import subprocess
import datetime
import json

def check_file(fname):
  file_abspath = os.path.abspath(fname)
  if os.path.isfile(file_abspath) and os.access(file_abspath, os.R_OK):
    return file_abspath 
  else:
    #Either file is missing or is not readable
    return

def log(level, message):
  if level == 'OK':
    print(colored('[  OK  ]', 'green'), "\t", message, file=sys.stderr)
  elif level == 'INFO':
    print(colored('[ INFO ]', 'blue'), "\t", message, file=sys.stderr)
  elif level == 'ERROR':
    print(colored('[ FAIL ]', 'red'), "\t", message, file=sys.stderr)
  else:
    print(message)

def get_config(config_file, group):
  config = ConfigParser.ConfigParser()
  config.read(config_file)
  if config.has_section(group):
    return config
  else:
    raise Exception('Unknown config section') 

def get_machine_uuid():
  name = subprocess.Popen(['xenstore-read name'], shell=True, stdout=subprocess.PIPE).communicate()[0]
  id = name.strip()
  return id[9:]

def get_user_value(args, config, key):
  if args[key] is None:
    try:
      value = config.get('rackspace_cloud', key)
    except:
      raise Exception("Invalid config, '" + key + "' key not found in rackspace_cloud section")
  else:
      value = args[key]
  return value 

