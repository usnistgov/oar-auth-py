#########################################################################
#
# PDR Python base environment
# 
# This container provides the common python environment required by
# other containers needed in the docker directory
# 
# This Dockerfile creates a Linux container with Python 3 installed 
# along with all required python libraries.
#
#########################################################################
FROM oar-metadata/mdenv

RUN apt-get update && apt-get install -y python3-yaml curl wget less sudo zip   \
                                         p7zip-full ca-certificates git xmlsec1 \
                                         pkg-config build-essential libssl-dev  \
                                         uwsgi-src python3-dev

# Need to build uwsgi with xmlsec1 support; OS-version does not provide that
#
# Note: projects.unbit.it is the official distribution site for uwsgi, but
# it currently has an expired site cert
# RUN pip install https://projects.unbit.it/downloads/uwsgi-lts.tar.gz
#
# At this time lts is 2.0.20; latest is 2.0.28
# (DO NOT USE UWSGI_VERSION as env var name!)
ENV UWSGI_VERS=2.0.28
RUN curl -L -o /tmp/uwsgi-${UWSGI_VERS}.tar.gz \
    https://github.com/unbit/uwsgi/archive/refs/tags/${UWSGI_VERS}.tar.gz
RUN pip install /tmp/uwsgi-${UWSGI_VERS}.tar.gz
RUN mkdir -p /usr/local/share/uwsgi/conf
COPY pipinstalled.ini /usr/local/share/uwsgi/conf/python.ini
ENV OAR_UWSGI_OPTS="--ini /usr/local/share/uwsgi/conf/python.ini"

# RUN pip install --upgrade pip setuptools
RUN apt-get update && apt-get install -y libxmlsec1 libxmlsec1-dev
RUN pip install --force-reinstall --no-binary lxml lxml
RUN pip install funcsigs 'fs>=2.0.21' pyjwt python3-saml flask

# Create the user that container operations should run as.  Normally,
# this is set to match identity information of the host user that is
# launching the container.
#
RUN sed --in-place -e '/CREATE_MAIL_SPOOL/ s/=yes/=no/' /etc/default/useradd
ARG devuser=developer
ARG devuid=1000
RUN grep -qs :${devuid}: /etc/group || \
    groupadd --gid $devuid $devuser
RUN grep -Pqs ":${devuid}:\d+:" /etc/passwd || \
    useradd -m --comment "OAR Developer" --shell /bin/bash \
            --gid $devuid --uid $devuid $devuser
RUN echo $devuser "ALL=(ALL)" NOPASSWD:ALL > /etc/sudoers.d/90-developers

CMD ["bash"]

