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

class ConfigParams(object):
    def __init__(self):
        self._jwt_secret = None
        self._redirect_url = None
        self._jwt_claimName = None
        self._jwt_claimValue = None
        self._auth_port = None

    @property
    def jwt_secret(self):
        return self._jwt_secret
    
    @jwt_secret.setter
    def jwt_secret(self, value):
        self._jwt_secret = value
        
    @jwt_secret.deleter
    def jwt_secret(self):
        del self._jwt_secret
        
        
    @property
    def redirect_url(self):
        return self._redirect_url
    
    @redirect_url.setter
    def redirect_url(self, value):
        self._redirect_url = value
        
    @redirect_url.deleter
    def redirect_url(self):
        del self._redirect_url

        
    @property
    def jwt_claimName(self):
        return self._jwt_claimName
    
    @jwt_claimName.setter
    def jwt_claimName(self, value):
        self._jwt_claimName = value
        
    @jwt_claimName.deleter
    def jwt_claimName(self):
        del self._jwt_claimName
        
        
    @property
    def jwt_claimValue (self):
        return self._jwt_claimValue 
    
    @jwt_claimValue .setter
    def jwt_claimValue (self, value):
        self._jwt_claimValue  = value
        
    @jwt_claimValue .deleter
    def jwt_claimValue (self):
        del self._jwt_claimValue 
        
    @property
    def auth_port(self):
        return self._auth_port
    
    @auth_port.setter
    def auth_port(self, value):
        self._auth_port = value
        
    @auth_port.deleter
    def auth_port(self):
        del self._auth_port