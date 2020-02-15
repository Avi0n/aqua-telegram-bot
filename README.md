# AquaTelegramBot
This bot is a fun little karma system for Telegram groups. The bot re-posts any picture you send to the chat room with inline emojis which you can use to vote with. 👍 is 1 point, 👌 is 2 points, and ❤️ is 3 points. Here are a couple pictures to give you a feel for what it does:   
![image1](https://i.imgur.com/7BzYRvE.png)   
Sample of a photo with inline buttons attached. The Votes button shows which users have voted on the photo and how many points they gave.   
![image2](https://i.imgur.com/B0k74du.png)   
If you send /karma to the bot, it will tell you the current totals for each user in the chatroom.


Why is it called Aqua? Because this bot was originally thought to be pretty useless, just like the goddess from KonoSuba. 

I used this project to learn more about API's and Python so the code is messy and I probably did a lot of dumb stuff. If you want to fix something or add a feature, I'm open to pull requests!   

Requires Docker, Docker Compose, and Python 3.
Python dependencies are managed by pip in requirements.txt   
At the moment, Aqua supports up to 3 different Telegram rooms. This was a conscious design decision because I did not want my instance of the bot to be shared and used by unauthorized rooms.

Aqua currently supports the following commands:
*  /karma: Shows the current number of points users in the group chat have
*  /repost_check: Checks to see if the photo has been posted in the last 30 days
*  /delete: Deletes the photo that /delete was used on
*  /source: Finds the source of an image/gif (currently only works with images drawn in the anime style)
*  /addme: Adds user's personal chat ID to the database so that Aqua can send them PMs   

## Getting Started
This short guide will use git, Docker, and docker-compose. You can set this bot up without using Docker, but this guide will not cover how to do that.
1.  Install [Docker](https://docs.docker.com/install)
2.  If you're using Linux, [install Docker Compose](https://docs.docker.com/compose/install/) (macOS and Windows installations of Docker come with Compose)
3.  Clone this repo by running `git clone https://gitlab.com/Avi0n/aqua-telegram-bot.git`
4.  Using the Telegram bot [@BotFather](https://t.me/BotFather), create a new bot and disable Group Privacy. Copy the API Token of your new bot
5.  (Optional) Go to [SauceNao.com](https://saucenao.com/user.php) and create a new user account. Create a new API key
6.  Copy .env.example and rename it to .env
7.  Edit .env to include your bot API token, Telegram group chat names, and your SauceNao token.
8.  (Optional) If you want to use MySQL/MariaDB, setup the corresponding variables
8.  (Optional) Edit docker-compose.yml to your liking
9.  (Optional) If you're using MySQL, edit schema.sql to edit the database names to your liking
10.  Run `sudo docker-compose up -d --build`
11.  Add your new bot to the group chat and make it an admin (The only required privilege is "Delete messages")
12.  Have fun!
