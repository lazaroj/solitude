# This is designed to be run from fig as part of a
# Marketplace development environment.

# NOTE: this is not provided for production usage.

FROM mozillamarketplace/centos-mysql-mkt:0.2

RUN mkdir -p /pip/{cache,build}
ADD requirements /pip/requirements
WORKDIR /pip
RUN pip install -b /pip/build --download-cache /pip/cache --no-deps -r /pip/requirements/dev.txt

EXPOSE 2602

ENV SOLITUDE_DATABASE mysql://root:@mysql:3306/solitude
ENV MEMCACHE_URL memcache:11211
