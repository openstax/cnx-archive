FROM python:2.7-jessie

RUN addgroup --system archive \
    && adduser --system --group archive

# Install archive dependencies
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    git \
    make \
    pkg-config \
    gcc \
    zlib1g-dev \
    wget \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY . /src/
WORKDIR /src/
RUN chown -R archive:archive /src/

ARG APP_INI
ENV APP_INI ${APP_INI:-.dockerfiles/archive.ini}
ENV ARCHIVE_APP_INI /etc/cnx/archive/app.ini
RUN mkdir -p $(dirname $ARCHIVE_APP_INI)
COPY $APP_INI $ARCHIVE_APP_INI

ARG ARCHIVE_REQUIREMENTS
ENV ARCHIVE_REQUIREMENTS ${ARCHIVE_REQUIREMENTS:-https://raw.githubusercontent.com/Connexions/cnx-deploy/master/environments/vm/files/archive-requirements.txt}
RUN wget -O archive-requirements.txt $ARCHIVE_REQUIREMENTS

USER archive
# See also https://github.com/pypa/pip/issues/5221
RUN wget -O get-pip.py https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py --user \
    && rm get-pip.py
RUN python -m pip install --no-cache-dir --user -r archive-requirements.txt
RUN python -m pip install --no-cache-dir --user -e .

ENV PATH $PATH:/home/archive/.local/bin

ARG PORT
ENV PORT ${PORT:-6543}
EXPOSE $PORT

CMD pserve $ARCHIVE_APP_INI
