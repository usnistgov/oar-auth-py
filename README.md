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
  *  `pdr-publish` -- the publishing services 

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

## LICENSE

Each repository will contain a plain-text file named `LICENSE.md`
or `LICENSE` that is phrased in compliance with the Public Access
to NIST Research [*Copyright, Fair Use, and Licensing Statement
for SRD, Data, and Software*][nist-open], which provides
up-to-date official language for each category in a blue box.

- The version of [LICENSE.md](LICENSE.md) included in this
  repository is approved for use.
- Updated language on the [Licensing Statement][nist-open] page
  supersedes the copy in this repository. You may transcribe the
  language from the appropriate "blue box" on that page into your
  README.

If your repository includes any software or data that is licensed
by a third party, create a separate file for third-party licenses
(`THIRD_PARTY_LICENSES.md` is recommended) and include copyright
and licensing statements in compliance with the conditions of
those licenses.

## CODEOWNERS

This template repository includes a file named
[CODEOWNERS](CODEOWNERS), which visitors can view to discover
which GitHub users are "in charge" of the repository. More
crucially, GitHub uses it to assign reviewers on pull requests.
GitHub documents the file (and how to write one) [here][gh-cdo].

***Please update that file*** to point to your own account or
team, so that the [Open-Source Team][gh-ost] doesn't get spammed
with spurious review requests. *Thanks!*

## CODEMETA

Project metadata is captured in `CODEMETA.yaml`, used by the NIST
Software Portal to sort your work under the appropriate thematic
homepage. ***Please update this file*** with the appropriate
"theme" and "category" for your code/data/software. The Tier 1
themes are:

- [Advanced communications](https://www.nist.gov/advanced-communications)
- [Bioscience](https://www.nist.gov/bioscience)
- [Buildings and Construction](https://www.nist.gov/buildings-construction)
- [Chemistry](https://www.nist.gov/chemistry)
- [Electronics](https://www.nist.gov/electronics)
- [Energy](https://www.nist.gov/energy)
- [Environment](https://www.nist.gov/environment)
- [Fire](https://www.nist.gov/fire)
- [Forensic Science](https://www.nist.gov/forensic-science)
- [Health](https://www.nist.gov/health)
- [Information Technology](https://www.nist.gov/information-technology)
- [Infrastructure](https://www.nist.gov/infrastructure)
- [Manufacturing](https://www.nist.gov/manufacturing)
- [Materials](https://www.nist.gov/materials)
- [Mathematics and Statistics](https://www.nist.gov/mathematics-statistics)
- [Metrology](https://www.nist.gov/metrology)
- [Nanotechnology](https://www.nist.gov/nanotechnology)
- [Neutron research](https://www.nist.gov/neutron-research)
- [Performance excellence](https://www.nist.gov/performance-excellence)
- [Physics](https://www.nist.gov/physics)
- [Public safety](https://www.nist.gov/public-safety)
- [Resilience](https://www.nist.gov/resilience)
- [Standards](https://www.nist.gov/standards)
- [Transportation](https://www.nist.gov/transportation)

---

[usnistgov/opensource-repo][gh-osr] is developed and maintained
by the [opensource-team][gh-ost], principally:

- Gretchen Greene, @GRG2
- Yannick Congo, @faical-yannick-congo
- Trevor Keller, @tkphd

Please reach out with questions and comments.

<!-- References -->

[18f-guide]: https://github.com/18F/open-source-guide/blob/18f-pages/pages/making-readmes-readable.md
[cornell-meta]: https://data.research.cornell.edu/content/readme
[gh-cdo]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
[gh-mdn]: https://github.github.com/gfm/
[gh-nst]: https://github.com/usnistgov
[gh-odi]: https://odiwiki.nist.gov/ODI/GitHub.html
[gh-osr]: https://github.com/usnistgov/opensource-repo/
[gh-ost]: https://github.com/orgs/usnistgov/teams/opensource-team
[gh-rob]: https://odiwiki.nist.gov/pub/ODI/GitHub/GHROB.pdf
[gh-tpl]: https://github.com/usnistgov/carpentries-development/discussions/3
[li-bsd]: https://opensource.org/licenses/bsd-license
[li-gpl]: https://opensource.org/licenses/gpl-license
[li-mit]: https://opensource.org/licenses/mit-license
[nist-code]: https://code.nist.gov
[nist-disclaimer]: https://www.nist.gov/open/license
[nist-s-1801-02]: https://inet.nist.gov/adlp/directives/review-data-intended-publication
[nist-open]: https://www.nist.gov/open/license#software
[wk-rdm]: https://en.wikipedia.org/wiki/README
