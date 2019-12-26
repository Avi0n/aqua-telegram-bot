# AquaTelegramBot
This bot is a fun little karma system for a Telegram group. The bot re-posts any picture you send to the chat room with inline emojis which you can use to vote with. 👍 is 1 point, 👌 is 2 points, and ❤️ is 3 points. Here are a couple pictures to give you a feel for what it does:   
https://imgur.com/a/aRS72Vf   
Why is it called Aqua? Because this bot was originally thought to be pretty useless, just like the goddess from KonoSuba. 

I used this project to learn more about API's and Python so the code is messy and I probably did a lot of dumb stuff. If you want to fix something or add a feature, I'm open to pull requests!   

Requires [PyPy 3](https://www.pypy.org/) and MySQL/MariaDB  
Python packages are managed by pip in requirements.txt   
At the moment, Aqua supports up to 3 different Telegram rooms. This was a conscious design decision because I did not want my instance of the bot to be shared and used by unauthorized rooms.

Aqua currently supports the following commands:
*  /karma: Shows the current number of points users in the group chat have
*  /delete: Deletes the photo that /delete was used on
*  /source: Finds the source of an image/gif (currently only works with images drawn in the anime style)
*  /addme: Adds user's personal chat ID to the database so that Aqua can send them PMs   

## Getting Started
You'll need git, Docker, and docker-compose
1.  Install [Docker](https://www.docker.com/get-started)
2.  If you're using Linux, [install Docker Compose](https://docs.docker.com/compose/install/) (macOS and Windows installations of Docker come with Compose)
3.  Clone this repo by running `git clone https://gitlab.com/Avi0n/aqua-telegram-bot.git`
4.  Using the Telegram bot [@BotFather](https://t.me/BotFather), create a new bot and disable Group Privacy. Copy the API Token of your new bot
5.  (Optional) Go to [SauceNao.com](https://saucenao.com/user.php) and create a new user account. Create a new API key
6.  Copy .env.example and rename it to .env
7.  Edit .env to include your bot API token, Telegram group chat names, and your SauceNao token. I also suggest changing the mysql root password.
8. (Optional) Edit docker-compose.yml to your liking
9.  Run `docker-compose up`
10.  Add your new bot to the group chat and have fun!
