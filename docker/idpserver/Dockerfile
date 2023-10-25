#########################################################################
#
# OAR Authentication broker service
#
# This container launches the services via scripts/authservice-uwsgi.py
#
#########################################################################
FROM oar-auth-py/pyenv

RUN pip install lxml isodate pysaml2 mako cherrypy

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
# COPY test.py /usr/local/bin/entrypoint.sh
RUN chmod a+rx /usr/local/bin/entrypoint.sh

RUN mkdir -p /dev/oar-auth-py /app/idp
WORKDIR /dev/oar-auth-py

ARG devuser=developer
USER $devuser
EXPOSE 8088
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
