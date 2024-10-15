# Authentication and Identity Services for OAR Data Systems

The Open Access to Research (OAR) initiave at NIST provides capabilities for
publishing data and code resulting from NIST research.  This repository provids
Python components that implement authentication and identity services for an
environment of OAR microservices.

A key service provided by this repository is an authentication broker service.
It integrates with the institution's (SAML-base) identity provider to log users
into the OAR environment.  For an authenticated client/user, it can provide a
JSON Web Token (JWT) which the client uses to connect to other OAR backend
services. 

## Repository Contents

```
python       --> Python source code for the metadata and preservation
                  services
idp          --> An implementation of a SAML IDP Login service that
                  can be used in lieu of an external one for
                  development and testing
scripts      --> Tools for running the services and running all tests
oar-build    --> general oar build system support (do not customize)
metadata     --> The base nistoar Python source code, provided as a git
                  submodule
docker       --> Docker containers for building and running tests
```

## Prerequisites

The code requires Python 3.9 or later.

The oar-metadata package is a prerequisite which is configured as git
sub-module of this package.  This means after you clone the oar-pdr git
repository, you should use `git submodule` to pull in the oar-metadata
package into it:
```
git submodule update --init
```

See oar-metadata/README.md for a list of its prerequisites.

In addition to oar-metadata and its prerequisites, this package relies on
a few OS packages and third-party python packages.  In particular,
this software requires xmlsec, which is best installed via the OS
package manager.  Be sure to include libraries that include openssl
and development support (with .h files).  For example, under
Debian/Ubuntu,
```
  apt-get install xmlsec1 libxmlsec1-openssl libxmlsec1-dev 
```

While not required to build, the Authentication Service provides
support for launching it via `uwsgi`, so it is recommended that it be
installed via the OS package manager as well.

The following python packages are also required.

 * python3-saml
 * flask
 * pyjwt
 * xmlsec
 * isodate

These can installed via pip:
```
  pip install -r requirements.txt
```

Further, testing and development optionally requires some additional packages:

 * pySAML2
 * mako
 * cherrypy

Install these via pip:
```
  pip install -r idp/requirements.txt
```

### Acquiring prerequisites via Docker

As an alternative to explicitly installing prerequisites to run
the tests, the `docker` directory contains scripts for building a
Docker container with these installed.  Running the `docker/run.sh`
script will build the containers (caching them locally), start the
container, and put the user in a bash shell in the container.  From
there, one can run the tests or run python interactively.

# Building and Testing the software

This repository currently provides one specific software product:
  *  `auth-py` -- the authentication broker service

## Simple Building with `makedist`

As a standard OAR repository, the software products can be built by simply via
the `makedist` script, assuming the prerequisites are installed: 

```
  scripts/makedist
```

The built products will be written into the `dist` subdirectory
(created by the `makedist`); each will be written into a zip-formatted
file with a name formed from the product name and a version string.  

The individual products can be built separately by specifying the
product name as arguments, e.g:

```
  scripts/makedist auth-py
```

Additional options are available; use the `-h` option to view the
details:

```
  scripts/makedist -h
```

### Simple Testing with `testall`

Assuming the prerequisites are installed, the `testall` script can be
used to execute all unit and integration tests:

```
  scripts/testall
```

Like with `makedist`, you can run the tests for the different products
separately by listing the desired product names as arguments to
`testall`.  Running `testall -h` will explain available command-line
options.

### Building and Testing Using Native Tools

The Python build tool, `setup.py`, within the `python` subdirectory,
is used to build and test the software.  To build, type while in this
directory: 

```
  python setup.py build
```

This will create a `build` subdirectory and compile and install the
software into it.  To install it into an arbitrary location, type

```
  python setup.py --prefix=/oar/home/path install
```

where _/oar/home/path_ is the path to the base directory where the
software should be installed.

The `makedist` script (in [scripts](scripts)) will package up an
installed version of the software into a zip file, writing it out into
the `dist` directory.  Unpacking the zip file into a directory is
equivalent to installing it there.

To run the unit tests, type:

```
  python setup.py test
```

### Building and Testing Using Docker

Like all standard OAR repositories, this repository supports the use
of Docker to build the software and run its tests.  (This method is
used at NIST in production operations.)  The advantage of the Docker
method is that it is not necessary to first install the
prerequisites; this are installed automatically into Docker
containers.

To build the software via a docker container, use the
`makedist.docker` script: 

```
  scripts/makedist.docker
```

Similarly, `testall.docker` runs the tests in a container:

```
  scripts/testall.docker
```

Like their non-docker counterparts, these scripts accept product names
as arguments.

## About the Services

The primary service provided by this repository is the OAR
Authentication Broker service.  Its job is to help the OAR system's
browser-based applications login and interact with other backend
services.  It works with a SAML-based IDP Login service (typically
provided by the hosting institution) to manage the login process.
After a user is successfully logged in, it can provide a front-end
application with a JWT authentication token that the latter uses to
connect securely to backend services requiring authentication.

A second service is also provided for development and testing: an
SAML IDP Login service that can be used in lieu of an external one.
This service (located in the `idp` subdirectory) is _not_ included
in the exportable products produced by `makedist` as described
above.

### Running the Services

#### In production

The Authentication Broker is implemented as a WSGI compliant
application.  It can be launched using `uwsgi` via the
[scripts/authservice-uwsgi.py](scripts/authservice-uwsgi.py).  (See
[docker/authserver/entrypoint.sh](docker/authserver/entrypoint.sh) for
an example.

Like all OAR services, it is designed to pull its configuration from a
central configuration server; however, it can be fed its configuration
via a static file.  See
[authservice-config.yml](docker/authserver/authservice-config.yml) as
an example.  The configuration parameters are defined in the [in-line
python documentation](python/nistoar/auth/wsgi/flask.py).

### For Developement and Interactive Testing

The Authentication Broker service and the Login Service can be run
together easily via Docker by typing:
```
   docker/authserver/run.sh -I --bg
```

The first time this is run, all the code and Docker images are built
automatically.  No installing of prerequisites nor building of
products is required first.  The command then starts both services in
the background.  The Authentication service will listen on port 9095,
and the login service, on 8088.

You can excercise that login process by visiting 
https://localhost:9095/sso/saml/login?redirectTo=https://localhost:9095/sso/auth/_tokeninfo.
When you see the login screen, you can enter "upper" and "crust" as
the username and password, respectively.  After successful login, the
browser should display user attributes and a JWT token in JSON format;
this is an example of data that OAR front-end applications retrieve.

To stop the services, type:
```
   docker/authserver/run.sh -I stop
```

Type `docker/authserver/run.sh -h` and consult the [Docker container
README](docker/authserver) for more information on running and
configuring the services.  

To test locally you can use local identity provider service instead of 
connecting to your organizational IDP. 
To run standalone local IDP read and follow the instructions [IDP
ReadMe](idp/README.md)

## License and Disclaimer

This software was developed by employees and contractors of the
National Institute of Standards and Technology (NIST), an agency of
the Federal Government and is being made available as a public
service. Pursuant to title 17 United States Code Section 105, works of
NIST employees are not subject to copyright protection in the United
States.  This software may be subject to foreign copyright.
Permission in the United States and in foreign countries, to the
extent that NIST may hold copyright, to use, copy, modify, create
derivative works, and distribute this software and its documentation
without fee is hereby granted on a non-exclusive basis, provided that
this notice and disclaimer of warranty appears in all copies.

THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE
DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE
SOFTWARE WILL BE ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY
DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR
CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY
CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY,
CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY
PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS
SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE
SOFTWARE OR SERVICES PROVIDED HEREUNDER. 

