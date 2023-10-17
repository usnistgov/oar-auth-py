# import pandas as pd
import pdb
import argparse
import sys
import os
import traceback
import shutil
import requests
from pathlib import Path
from datetime import datetime
from . import configParams 

"""
Configuration values used by authentication service
"""

jwtsecret     = 'yeWAgVDfb$!MFn@MCJVN7uqkznHbDLR#'
jwtClaimName  = 'odiclaim'
jwtClaimValue = 'odivalue' 
redirectUrl   = "https://data.nist.gov, http://localhost:4200"
authport      =  8000

# Setter And Getter for configuration parameters  
cp = configParams.ConfigParams()
def get_auth_config():
    """read config url and get mongodb related information """
    try:
        configurl = os.getenv("CONFIG_URL")
        resp = requests.get(configurl)
        if resp.status_code >= 400:
            print("Exception reading config data:"+configurl)
        ct = resp.headers.get('content-type','')
        testconfig = resp.json()        
        cp.jwt_secret = testconfig['propertySources'][0]['source']['jwt.secret']
        cp.jwt_claimValue = testconfig['propertySources'][0]['source']['jwt.claimname']
        cp.jwt_claimName = testconfig['propertySources'][0]['source']['jwt.claimvalue']
        cp.redirect_url = testconfig['propertySources'][0]['source']['application.url']
        cp.auth_port = testconfig['propertySources'][0]['source']['saml.port']
    except:
        cp.jwt_secret = jwtsecret
        cp.jwt_claimValue = jwtClaimValue
        cp.jwt_claimName = jwtClaimName
        cp.redirect_url = redirectUrl
        cp.auth_port = authport
    return cp