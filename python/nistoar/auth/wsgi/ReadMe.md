### NIST SAML Service Provider 

This is a SAML based authentication service which is used to connect to NIST SSO.
The main library used here is 
https://github.com/SAML-Toolkits/python3-saml


## Following is the directory structure and files:

1. flaskauth.py 
    This is most of the authentication service code. It has various service endpoint defined.

2. saml
    This folder contains all the required settings, keys and certs to make this communication possible. 
    certs/ folder contain
        idp.crt  - Cert provided by SSO Identity provider 
        sp.crt  -  Cert generated for our service provider/ this authentication API
        sp.key - Key generated for this service provider/this authentication API
    Make sure not to change the names of these files and folder, if using default settings.
    To genrate local certs etc used 
    
    ''
    openssl req -new -x509 -days 3652 -nodes -out sp.crt -keyout sp.key
    ''

2. configs
    configParams.py     This file contains setters and getters for variables used in flaskauth.py
    odiconfig.py   Reading configserver or use default values to populate configParams.




## Running locally on Mac/Linux OS:

This is a flask api developed to provide SAML based authentication API.
This authentication service connects to single sign on provided by NIST.

Following are reuirements to be installed before running this package

Pip3 install –r flask=1.0 

Following are some libraries needed to run everything locally.
pip3 install pyopenssl(only needed in testing for creating ssl context) 

pip3 install -U rdflib 

pip3 install xmlsec 

pip3 install Flask Jinja2 (only needed if this gives error or the libraries are not getting installed properly) 

pip3 install python3-saml

#only if needed
pip3 install --force-reinstall --no-binary lxml lxml
