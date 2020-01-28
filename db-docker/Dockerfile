FROM mariadb

ENV MYSQL_DATABASE=room1 \
    MYSQL_ROOT_PASSWORD=mysql_password

ADD schema.sql /docker-entrypoint-initdb.d

EXPOSE 3306
