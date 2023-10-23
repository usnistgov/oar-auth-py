#########################################################################
#
# OAR Authentication broker service
#
# This container launches the services via scripts/authservice-uwsgi.py
#
#########################################################################
FROM oar-auth-py/pyenv

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod a+rx /usr/local/bin/entrypoint.sh

VOLUME /app/dist

RUN mkdir -p /dev/oar-auth-py /app && chmod a+rwx /app
WORKDIR /dev/oar-auth-py

ENV PYTHONPATH /dev/oar-auth-py/python/dist/oarauth/lib/python:/app/dist/oarauth/lib/python

ARG devuser=developer
USER $devuser
EXPOSE 9095
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
