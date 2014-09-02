from __future__ import print_function
import os, pyrax, sys
import pyrax.exceptions as pexc
from termcolor import colored
import ConfigParser

config_file = "config.ini"

def log(level, message):
  if level == 'OK':
    print(colored('[  OK  ]', 'green'), "\t", message, file=sys.stderr)
  elif level == 'INFO':
    print(colored('[ INFO ]', 'blue'), "\t", message, file=sys.stderr)
  elif level == 'ERROR':
    print(colored('[ FAIL ]', 'red'), "\t", message, file=sys.stderr)
  else:
    print(message)

def authenticate(dc):
  pyrax.set_setting("identity_type", "rackspace")

  log("INFO", "Authenticating")

  try:
    pyrax.set_credential_file(config_file, region=dc)
  except pexc.AuthenticationFailed:
    log('ERROR', 'Authentication Failure')
  
  log('OK', 'Authentication Successful')

def get_config(group):
  config = ConfigParser.ConfigParser()
  config.read(config_file)
  if config.has_section(group):
    return config
  else:
    raise Exception('Unknown config section') 
