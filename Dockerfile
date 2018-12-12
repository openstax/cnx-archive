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

RUN python -m pip install --no-cache-dir -e .


ARG PORT
ENV PORT ${PORT:-6543}
EXPOSE $PORT

ENV ARCHIVE_APP_INI /src/docker.ini

USER archive

CMD pserve $ARCHIVE_APP_INI
