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

## Contents

```
python       --> Python source code for the metadata and preservation
                  services
scripts      --> Tools for running the services and running all tests
oar-build    --> general oar build system support (do not customize)
metadata     --> The base nistoar Python source code, provided as a git
                  submodule
docker/      --> Docker containers for building and running tests
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

In addition to oar-metadata and its prerequisites, this package requires
the following third-party packages:

 * python3-saml

Furhter, testing and development optionally requires:

 * pySAML2

### Acquiring prerequisites via Docker

As an alternative to explicitly installing prerequisites to run
the tests, the `docker` directory contains scripts for building a
Docker container with these installed.  Running the `docker/run.sh`
script will build the containers (caching them locally), start the
container, and put the user in a bash shell in the container.  From
there, one can run the tests or use the `jq` and `validate` tools to
interact with metadata files.

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

The Python build tool, `setup.py`, is used to build and test the
software.  To build, type while in this directory:

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

The `makedist` script (in [../scripts](../scripts)) will package up an
installed version of the software into a zip file, writing it out into
the `../dist` directory.  Unpacking the zip file into a directory is
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

## Running the services

The [scripts](scripts) directory contains
[WSGI applications](https://docs.python.org/3/library/wsgiref.html) scripts.

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

