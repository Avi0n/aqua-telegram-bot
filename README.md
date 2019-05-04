# AquaTelegramBot
Requires Python 3 and MySQL/MariaDB  
Python packages required:   
*  mysqlclient
*  python-telegram-bot
*  emoji
*  python-dotenv
*  requests
*  Pillow

## Setting up a dev environment
1.  Install [Docker](https://www.docker.com/get-started)
2.  If you're using Linux, [install Docker Compose](https://docs.docker.com/compose/install/) (macOS and Windows installations of Docker come with Compose)
3.  Install git if you haven't already
3.  Clone this repository
4.  `cd` to this repository's directory
5.  copy .env.example and rename it to .env
6.  Edit .env to include your Telegram bot's API token as well as your SauceNao token
7.  Edit the bottom of schema.sql inside the db-docker folder to use your Telegram username
8.  Run `sudo docker-compose up --build`
9.  That's it! Happy coding

## Setting up a prod environment
1.  In docker-compose.yml, map a volume to store mariadb data in or setup a different MariaDB/MySQL server
2.  Edit schema.sql to include all of the Telegram usernames in the channel that the bot will be running in
3.  In main.py, change "Debauchery Tea Party" to the name of your channel
