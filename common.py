from __future__ import print_function
import os, pyrax, sys
import pyrax.exceptions as pexc
from termcolor import colored
import ConfigParser
import subprocess
import datetime
import json

path = os.path.dirname(os.path.realpath(__file__))
config_file = path + "/config.ini"

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
  
  try: 
    log("INFO", "Authenticating with cached token")
    token_file = open(path + '/.token_cache', 'r')
    identity = json.load(token_file)
    token_file.close()

    expiry = datetime.datetime.strptime(identity['expires'], '%Y-%m-%d %H:%M:%S')
    present = datetime.datetime.now()
    expires_in = expiry - present
    if expires_in.total_seconds() < 600:
      log('INFO', 'Token expires soon or is already expired, re-authenticating')
      raise Exception('Token Expired')

    pyrax.auth_with_token(identity['token'], tenant_id=identity['tenant_id'], tenant_name=identity['username'])
    pyrax.identity.region = dc

  except:
    log("INFO", "Authenticating with API Key")
    
    try:
      pyrax.set_credential_file(config_file, region=dc)
     
      try: 
        token_file = open(path + '/.token_cache', 'w')
        identity = {}
        for attr in ['token', 'tenant_id', 'username', 'region']:
          identity[attr] = getattr(pyrax.identity, attr)
  
        identity['expires'] = str(pyrax.identity.expires)
        json.dump(identity, token_file, indent=4)
      except:
        log('ERROR', 'Unable to write token cache')
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

def get_machine_uuid():
  name = subprocess.Popen(['xenstore-read name'], shell=True, stdout=subprocess.PIPE).communicate()[0]
  id = name.strip()
  return id[9:]
