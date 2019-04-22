# AquaTelegramBot
Requires Python 3 and MySQL/MariaDB  
Python packages required:   
*  mysqlclient
*  python-telegram-bot
*  emoji
*  python-dotenv

## Setting up a dev environment
1.  Install [Docker](https://www.docker.com/get-started)
2.  If you're using Linux, [install Docker Compose](https://docs.docker.com/compose/install/) (macOS and Windows installations of Docker come with Compose)
3.  Install git if you haven't already
3.  Clone this repository
4.  `cd` to this repositories directory
5.  `cp .env.example .env`
6.  Edit .env with your Telegram bot's API
7.  Edit the bottom of schema.sql inside the db-docker folder to use your Telegram username
8.  Run `sudo docker-compose up --build`
9.  That's it! Happy coding.

For production, you'll need to map a volume to store mariadb data in or setup a different MariaDB/MySQL server, but that's about the only change you'll need to make.
