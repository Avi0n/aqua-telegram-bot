# AquaTelegramBot
Requires Python 3 and MySQL/MariaDB  
Python packages are managed by pip in requirements.txt

## Setting up a dev environment
1.  Install [Docker](https://www.docker.com/get-started)
2.  If you're using Linux, [install Docker Compose](https://docs.docker.com/compose/install/) (macOS and Windows installations of Docker come with Compose)
3.  Install git if you haven't already
3.  Clone this repository
4.  `cd` to this repository's directory
5.  Copy .env.example and rename it to .env
6.  Edit .env to include your Telegram group chat names, database names, bot API token and your SauceNao token
7.  Run `sudo docker-compose up --build`
8.  That's it! Happy coding

## Setting up a prod environment
1.  In docker-compose.yml, map a volume to store mariadb data in or setup a different MariaDB/MySQL server
2.  Edit schema.sql with the database names of your choice
3.  Edit .env with your Telegram group chat and database names
