# Stand-alone Identity Provider server

This is an adaptation of the pysaml2 (https://pysaml2.readthedocs.io/) example
IDP server (example/idp2/idp.py; see LICENSES/pysaml2-license.txt).  It is
provided to facilite testing of the OAR authentication broker service provided
by this repository.

This repository support running this server via a Docker container; from the
repository's top directory, just type:
```
docker/idpserver/run.sh
```

Running via the container negates the need to install any dependencies.  The
rest of this README document discusses running the server directly without the
use of Docker.

## Dependencies

This set-up assumes the use of python 3.8 or later.  (While pysaml2 supports
2.7, this adaptation has not been tested with it.)

Like authentication broker service, this test server relies on xmlsec which are
best installed via the OS package manager.  Be sure to include libraries that
include openssl and development support (with .h files).  For example, under
Debian/Ubuntu,

```
  apt-get install xmlsec1 libxmlsec1-openssl libxmlsec1-dev 
```

In addition, relies on a few python packages, which can be installed with pip:

```
  pip install xmlsec lxml isodate pysaml2 mako cherrypy
```

## Configuring the server

This server comes configured to run assuming it will be the IDP for the
authentication broker service (as well as for the sample SP service that comes
with the python3-saml package).  The configuration is encapsulated in the
`idp_conf.py` file; see the [pysaml2
documentation](https://pysaml2.readthedocs.io/) for more information.  

### Adding Identities for Testing

It is helpful for development to add identities to the server.

_(under construction)_

## Running the server

To run the server, type:

```
python idp.py idp_conf.py
```

The server will run in the foreground, writing its messages to the terminal,
and its endpoints will be available on localhost, port 8088.

## Key Endpoints

IDP metadata:
   https://localhost:8088/idp.xml

Authentication Request (which displays login page):
   https://localhost:8088/sso/redirect

Logout Request
   https://localhost:8088/slo/redirect

