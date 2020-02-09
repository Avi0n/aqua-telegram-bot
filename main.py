"""
Aqua Telegram Bot
Copyright (C) 2019  Nate Chung

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import asyncio
import logging
import os
import string
import sys

import aiomysql
import imagededup
from imagededup.methods import PHash
import imageio
import telegram.bot
from PIL import Image
from dotenv import load_dotenv
from emoji import emojize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CommandHandler, CallbackQueryHandler, Filters
from telegram.ext import messagequeue as mq
from telegram.ext.dispatcher import run_async
from telegram.utils.request import Request

from get_source import get_source

# Initialize dotenv
load_dotenv()

# Initialize logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.os.getenv("BOT_LOG_LEVEL"))

logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning("Update '%s' caused error '%s'", update, context.error)


# Flood limit class
class MQBot(telegram.bot.Bot):
    # A subclass of Bot which delegates send method handling to MQ
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        # Wrapped method would accept new 'queued' and 'isgroup' OPTIONAL arguments
        return super(MQBot, self).send_message(*args, **kwargs)


# Convert mp4 to gif. Copy paste from:
# https://gist.github.com/michaelosthege/cd3e0c3c556b70a79deba6855deb2cc8
class TargetFormat(object):
    GIF = ".gif"
    MP4 = ".mp4"
    AVI = ".avi"


def convert_media(inputpath, targetFormat):
    """Reference: http://imageio.readthedocs.io/en/latest/examples.html#convert-a-movie"""
    outputpath = "source" + targetFormat
    print("converting\r\n\t{0}\r\nto\r\n\t{1}".format(inputpath, outputpath))

    reader = imageio.get_reader(inputpath)
    fps = reader.get_meta_data()["fps"]

    writer = imageio.get_writer(outputpath, fps=fps)
    for i, im in enumerate(reader):
        sys.stdout.write("\rframe {0}".format(i))
        sys.stdout.flush()
        writer.append_data(im)
    print("\r\nFinalizing conversion...")
    writer.close()
    print("Done converting.")


# Respond to /start
def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Send /karma to see everyone's points.\nSend /addme to let me forward" +
                                  " photos that you " + emojize(":star:", use_aliases=True) + " to you!")


@run_async
# Allow user to delete their own photo
def delete(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Find room name and assign correct database
    if update.message.chat.title == os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif update.message.chat.title == os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")
    elif update.message.chat.title == os.getenv("GROUP3"):
        database = os.getenv("DATABASE3")

    username = update.message.reply_to_message.caption.split()
    delete_message_id = update.message.reply_to_message.message_id

    # Only allow original poster to delete their own message
    if username[-1] == update.message.from_user.username:
        try:
            points_to_delete = loop.run_until_complete(delete_row(database, delete_message_id, loop))
            loop.run_until_complete(update_user_karma(database, username[-1], "-", str(points_to_delete[0]), loop))
            # Remove message that user replied to
            context.bot.delete_message(chat_id=update.message.chat_id,
                                       message_id=delete_message_id)
            # Remove the "/delete" message the user sent to keep the chat clean
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        except Exception as e:
            context.bot.send_message(chat_id=update.message.chat_id, text="Error: " + str(e))
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="You can only delete your own posts.")


# Respond to /karma
@run_async
def karma(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Find out which database to use. If the chat is private, watch for user specified database
    if update.message.chat.type == "private":
        keyboard = [[InlineKeyboardButton(os.getenv("GROUP1"), callback_data="20"),
                     InlineKeyboardButton(os.getenv("GROUP2"), callback_data="21")],
                    [InlineKeyboardButton(os.getenv("GROUP3"), callback_data="22")]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Please choose a room.", reply_markup=reply_markup)

    else:
        # If not a private chat, check the room name to match to a database
        chat_type = "group"
        if update.message.chat.title == os.getenv("GROUP1"):
            database = os.getenv("DATABASE1")
        elif update.message.chat.title == os.getenv("GROUP2"):
            database = os.getenv("DATABASE2")
        elif update.message.chat.title == os.getenv("GROUP3"):
            database = os.getenv("DATABASE3")

        message = loop.run_until_complete(get_user_karma(database, chat_type, loop))

        context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode="Markdown", timeout=20)


@run_async
# Respond to /give
def give(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    database = ""
    # Find out which database to use
    if update.message.chat.title == os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif update.message.chat.title == os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")
    elif update.message.chat.title == os.getenv("GROUP3"):
        database = os.getenv("DATABASE3")

    # Check to see if user used the right command format
    if "@" in update.message.text:
        # Remove all punctuation (@) and split the string
        string_split = update.message.text.split()
        username = string_split[1].translate(str.maketrans("", "", string.punctuation))
        points = string_split[2]
        points_no_punc = points.translate(str.maketrans("", "", string.punctuation))
        from_username = update.message.from_user.username

        try:
            if username == from_username:
                context.bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                                                              " just tried to give themselves points.")
                context.bot.send_sticker(chat_id=update.message.chat_id,
                                         sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            elif int(points) == 0:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="pfft, you just tried to give someone 0 points.")
                context.bot.send_sticker(chat_id=update.message.chat_id,
                                         sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            elif int(points) < -20:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="Don't you think that's a tad too many points to be taking away?")
            elif -21 < int(points) < 0:
                loop.run_until_complete(update_user_karma(
                    database, username, "-", points_no_punc, loop))
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " took away " + points + " points from " + username + "!")
            elif 61 > int(points) > 0:
                loop.run_until_complete(update_user_karma(
                    database, username, "+", points_no_punc, loop))
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " gave " + username + " " + points + " points!")
            elif int(points) > 61:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="Don't you think that's a tad too many points?")
        except Exception as e:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="Error: " + str(e))
    else:
        string_split = update.message.text.split()
        username = string_split[1]
        points = string_split[2]
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="The correct format is '/give @" + username + " " + points + "'")


# Respond to /addme
def addme(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    chat_type = update.message.chat.type
    username = update.message.from_user.username
    chat_id = update.message.chat_id

    context.bot.send_message(chat_id=chat_id,
                             text=loop.run_until_complete(addme_async(chat_type, username, chat_id, loop)))


async def addme_async(chat_type, username, chat_id, loop):
    # Make sure the /addme command is being sent in a PM
    if chat_type == "private":
        # Set MySQL settings
        pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                          user=os.getenv("MYSQL_USER"),
                                          password=os.getenv("MYSQL_PASS"),
                                          db=os.getenv("DATABASE1"),
                                          loop=loop)
        # prepare a cursor object using cursor() method
        # cursor = await db.cursor()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = "SELECT * FROM user_chat_id WHERE username = '" + \
                      str(username) + "';"
                try:
                    # Execute the SQL command
                    await cur.execute(sql)
                    # Fetch all the rows in a list of lists.
                    result = await cur.fetchone()
                except Exception as e:
                    print("Error: " + str(e))
                if result is None:
                    # Add user's chat_id with Aqua to database
                    sql = "INSERT INTO user_chat_id VALUES (" + str(
                        chat_id) + ", '" + str(username) + "');"
                    try:
                        # Execute the SQL command
                        await cur.execute(sql)
                        # Commit your changes in the database
                        await conn.commit()
                        message = "Added! Now whenever you " + emojize(":star:", use_aliases=True) + \
                                  " a photo, I'll forward it to you here! " + \
                                  emojize(":smiley:", use_aliases=True)
                    except Exception as e:
                        # Rollback in case there is any error
                        await conn.rollback()
                        print("Adding user's chat_id failed. " + str(e))
                        message = "Error: " + str(e)
                    finally:
                        await cur.close()
                else:
                    message = "You've already been added! " + \
                              emojize(":star:", use_aliases=True) + " away :)"
        pool.close()
        await pool.wait_closed()
    else:
        message = "That doesn't work in here. Send me a PM instead " + \
                  emojize(":wink:", use_aliases=True)
    return message


# Respond to /check_repost
def repost_check(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Find room name and assign correct database
    if update.message.chat.title == os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif update.message.chat.title == os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")
    elif update.message.chat.title == os.getenv("GROUP3"):
        database = os.getenv("DATABASE3")

    result = loop.run_until_complete(compare_hash(update.message.reply_to_message.message_id, database, loop))
    print(str(result))
    # Check to see if more than 1 record was returned
    try:
        if str(result) != "()":
            if int(result[0][2]) > 1:
                message_text = "Yep, that's a repost. Here's the first time it was posted.\nIt's been posted " + \
                               str(result[0][2]) + " times in the last 30 days.\n"

            context.bot.send_message(chat_id=update.message.chat_id, reply_to_message_id=result[0][0],
                                     text=message_text)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Hmm... doesn't look like a repost to me.")
    except Exception as e:
        print("Error: " + str(e))
        context.bot.send_message(chat_id=update.message.chat_id, text=str(e))


# Respond to /sauce
def sauce(update, context):
    source(update, context)


# Respond to /source
def source(update, context):
    authorized_room = True
    media_id = None

    try:
        username = update.message.reply_to_message.from_user.username
    except Exception as e:
        print(str(e))
        username = None

    if authorized_room is True and username is not None:
        # Get media's file_id
        while True:
            try:
                media_id = update.message.reply_to_message.photo[1].file_id
                break
            except Exception as e:
                print("Not a photo")
            try:
                media_id = update.message.reply_to_message.document.file_id
                break
            except Exception as e:
                print("Not a document")
            try:
                media_id = update.message.reply_to_message.video.file_id
                break
            except Exception as e:
                print("Not a video")
            finally:
                break

        # Get the download link from Telegram
        file = context.bot.get_file(file_id=media_id)
        # Download the media (jpg, png, mp4)
        file.download(timeout=10)
        # If it's an mp4, convert it to gif
        for fname in os.listdir("."):
            if fname.endswith(".mp4"):
                convert_media(fname, TargetFormat.GIF)
                os.remove(fname)
                break

        context.bot.send_message(chat_id=update.message.chat_id, text=get_source(), parse_mode='Markdown',
                                 disable_web_page_preview=True)

    # If this else statement runs, the user is either not in an "authorized room", or they didn't reply to an image
    else:
        print("You're not authorized to use that command here.")
        context.bot.send_message(chat_id=update.message.chat_id, text="Did you forget to reply to an image?")

    # Cleanup downloaded media
    for fname in os.listdir("."):
        if fname.endswith(".gif"):
            os.remove("source.gif")
        elif fname.endswith(".jpg"):
            os.remove(fname)


# Retrieve user's karma from the database
async def get_user_karma(database, chat_type, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)
    # prepare a cursor object using cursor() method
    # cursor = await db.cursor()

    if database == os.getenv("DATABASE1"):
        groupname = os.getenv("GROUP1")
    if database == os.getenv("DATABASE2"):
        groupname = os.getenv("GROUP2")
    if database == os.getenv("DATABASE3"):
        groupname = os.getenv("GROUP3")

    # Add chat group name to the results of /karma
    if chat_type == "private":
        return_message = groupname + "\n"
    else:
        return_message = ""

    sql = "SELECT * FROM user_karma WHERE karma <> 0 ORDER BY username;"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                results = await cur.fetchall()

                return_message += "```\n"

                # Find length of longest username and karma
                longest_username_length = 0
                longest_karma_length = 0
                for row in results:
                    longest_username_length = max(longest_username_length, len(row[0]))
                    longest_karma_length = max(longest_karma_length, len(str(row[1])))

                # Add each user and karma as its own row
                for row in results:
                    username = row[0]
                    karma_points = row[1]
                    return_message += username + (" " * (longest_username_length - len(username))) + \
                                      "   " + (" " * (longest_karma_length - len(str(karma_points)))) + str(
                        karma_points) + "\n"

                return_message += "\n```" + emojize(":v:", use_aliases=True)

            except Exception as e:
                if "1046" in str(e):
                    return_message = "The database options are:  \n- DTP  \n- DJB  \n- DCR"
                else:
                    return_message += "Error: " + str(e)
                    print("get_user_karma() error: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return return_message


# Increment the total karma for a specific user
async def update_user_karma(database, username, plus_or_minus, points, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database, loop=loop)
    # prepare a cursor object using cursor() method
    # cur = await conn.cursor()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT * FROM user_karma WHERE username = '" + username + "';"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                result = await cur.fetchone()
                print(result)
            except Exception as e:
                print("Error: " + str(e))
            if result is None:
                # Add username to the database along with the points that were just added
                sql = "INSERT INTO user_karma VALUES ('" + username + "', " + points + ");"
                try:
                    # Execute the SQL command
                    await cur.execute(sql)
                    # Commit your changes in the database
                    await conn.commit()
                except Exception as e:
                    # Rollback in case there is any error
                    await conn.rollback()
                    print("update_karma error: " + str(e))
                finally:
                    await cur.close()
            else:
                sql = "UPDATE user_karma SET karma = karma" + plus_or_minus + points + " WHERE username = '" + \
                      username + "';"
                try:
                    # Execute the SQL command
                    await cur.execute(sql)
                    # Commit your changes in the database
                    await conn.commit()
                except Exception as e:
                    # Rollback in case there is any error
                    await conn.rollback()
                    print("update_karma error: " + str(e))
                finally:
                    await cur.close()
    pool.close()
    await pool.wait_closed()


"""
# Check the toggle state of an emoji
def check_for_previous_vote(message_id, username, emoji_symbol):
    # Set MySQL settings
    conn = pymysql.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    sql = "SELECT " + emoji_symbol + " FROM message_karma WHERE message_id = " + \
            str(message_id) + " AND username = '" + username + "';"
    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    finally:
        await cursor.close()
        db.close()
    if int(result) is not 0:
        return True
    else:
        return False
"""


async def update_message_karma(database, message_id, username, emoji_points, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)
    # prepare a cursor object using cursor() method
    # cursor = await db.cursor()

    thumb_points = 0
    ok_points = 0
    heart_points = 0
    # Figure out which column to update
    if int(emoji_points) == 1:
        emoji_symbol = "thumbsup"
        thumb_points = 1
    elif int(emoji_points) == 2:
        emoji_symbol = "ok_hand"
        ok_points = 2
    elif int(emoji_points) == 3:
        emoji_symbol = "heart"
        heart_points = 3

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT * FROM message_karma WHERE message_id = " + \
                  str(message_id) + " AND username = '" + username + "';"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                result = await cur.fetchone()
            except Exception as e:
                print("Error: " + str(e))
            if result is None:
                # Insert new row with message_id, username, and emoji point values
                sql = "INSERT INTO message_karma VALUES (" + str(message_id) + ", '" + username + \
                      "', " + str(thumb_points) + ", " + str(ok_points) + \
                      ", " + str(heart_points) + ");"
                try:
                    # Execute the SQL command
                    await cur.execute(sql)
                    # Commit your changes in the database
                    await conn.commit()
                except Exception as e:
                    # Rollback in case there is any error
                    await conn.rollback()
                    print("update_message_karma insert error: " + str(e))
                finally:
                    await cur.close()
            else:
                # Update emoji points that user has given a specific message_id
                sql = "UPDATE message_karma SET " + emoji_symbol + " = " + emoji_symbol + " + " + str(emoji_points) + \
                      " WHERE message_id = " + \
                      str(message_id) + " AND username = '" + username + "';"
                try:
                    # Execute the SQL command
                    await cur.execute(sql)
                    # Commit your changes in the database
                    await conn.commit()
                except Exception as e:
                    # Rollback in case there is any error
                    await conn.rollback()
                    print("update_message_karma error: " + str(e))
                finally:
                    await cur.close()
    pool.close()
    await pool.wait_closed()


# Delete message_id row from database
async def delete_row(database, message_id, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Add message_id, photo's hash, and current date to database
            sql = "SELECT SUM(thumbsup + ok_hand + heart) FROM message_karma WHERE message_id = " + \
                  str(message_id) + ";"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                points_to_delete = await cur.fetchone()
            except Exception as e:
                print("Error in delete_row: " + str(e))
            # Delete hashes older than 30 days
            sql = "DELETE from message_karma WHERE message_id = " + str(message_id) + ";"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Commit your changes in the database
                await conn.commit()
            except Exception as e:
                # Rollback in case there is any error
                await conn.rollback()
                print("Error in delete_row: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return points_to_delete


# Check total karma for specific emoji for a specific message
async def check_emoji_points(database, message_id, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT SUM(thumbsup), SUM(ok_hand), SUM(heart) FROM message_karma WHERE message_id = " + \
                  str(message_id) + ";"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                result = await cur.fetchone()
            except Exception as e:
                print("Error in check_emoji_points: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return result


# Get total karma per user for a specific message
async def get_message_karma(database, message_id, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)

    return_message = "Votes\n\n"

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT username, SUM(thumbsup + ok_hand + heart) AS karma FROM message_karma WHERE message_id = " + \
                  str(message_id) + " GROUP BY username ORDER BY username;"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                results = await cur.fetchall()

                # Find length of longest username and karma
                longest_username_length = 0
                longest_karma_length = 0
                for row in results:
                    longest_username_length = max(longest_username_length, len(row[0]))
                    longest_karma_length = max(longest_karma_length, len(str(row[1])))

                # Add each user and karma as its own row
                for row in results:
                    username = row[0]
                    karma_points = row[1]
                    return_message += username + (" " * (longest_username_length - len(username))) + "   " + (
                            " " * (longest_karma_length - len(str(karma_points)))) + str(karma_points) + "\n"
            except Exception as e:
                return_message += "Error"
                print("Error in get_message_karma: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return return_message


# Get user's personal chat_id with Aqua
async def get_chat_id(tele_user, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=os.getenv("DATABASE1"),
                                      loop=loop)
    # prepare a cursor object using cursor() method
    # cursor = await db.cursor()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT chat_id FROM user_chat_id WHERE username = '" + str(tele_user) + "';"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                result = await cur.fetchone()
            except Exception as e:
                print("Error in get_chat_id: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return result[0]


def compute_hash(file_name):
    print(file_name)
    phasher = PHash()
    media_hash = phasher.encode_image("./" + file_name)
    print(media_hash)

    # Cleanup downloaded media
    try:
        os.remove("./" + file_name)
    except Exception as e:
        print(str(e))
    return media_hash


# Store hash of message_id's media in database
async def store_hash(database, message_id, media_hash, loop):
    print("Entered store_hash()")
    print(message_id)
    print(database)
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Add message_id, photo's hash, and current date to database
            sql = "INSERT INTO media_hash VALUES (" + str(message_id) + ",'" + media_hash + "', + CURRENT_DATE);"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Commit your changes in the database
                await conn.commit()
            except Exception as e:
                # Rollback in case there is any error
                await conn.rollback()
                print("Error in store_hash: " + str(e))
            # Delete hashes older than 30 days
            sql = "DELETE FROM media_hash WHERE Date < NOW() - INTERVAL 30 DAY;"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Commit your changes in the database
                await conn.commit()
            except Exception as e:
                # Rollback in case there is any error
                await conn.rollback()
                print("Error in store_hash: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()


# Check hash of message_id's media against all previously stored hashes
async def compare_hash(message_id, database, loop):
    # Set MySQL settings
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"),
                                      user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASS"),
                                      db=database,
                                      loop=loop)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # SELECT message_id, hash, COUNT(hash) FROM media_hash
            # WHERE hash = (SELECT hash FROM media_hash WHERE message_id=4223)
            # GROUP BY hash HAVING COUNT(*) > 1
            sql = "SELECT message_id, hash, COUNT(hash), 'temp' AS temp_col FROM media_hash" + \
                  " WHERE LEFT(hash, 4) = " + \
                  "(SELECT LEFT(hash, 4) FROM media_hash WHERE message_id = " + str(message_id) + ")" + \
                  " GROUP BY temp_col HAVING COUNT(*) > 1;"
            try:
                # Execute the SQL command
                await cur.execute(sql)
                # Fetch all the rows in a list of lists.
                result = await cur.fetchall()
            except Exception as e:
                print("Error in compare_hash: " + str(e))
            finally:
                await cur.close()
    pool.close()
    await pool.wait_closed()
    return result


@run_async
# Forward message that was posted by another user to the channel with emoji buttons
def repost(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # If user posts a photo/video in a private chat with the bot, ignore it
    if update.message.chat.type == "private":
        return

    # If user is replying to a message, store the id to use later
    reply_message_id = None
    try:
        if update.message.reply_to_message.message_id is not None:
            reply_message_id = update.message.reply_to_message.message_id
    except:
        print("Not a reply")

    # Check to see if user doesn't want their photo to be deleted
    if update.message.caption is not None:
        if "aquano" in update.message.caption.replace(" ", "").lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return
        elif "noaqua" in update.message.caption.replace(" ", "").lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return

    repost_caption = None

    keyboard = [[InlineKeyboardButton(str(0) + " " + emojize(":thumbsup:", use_aliases=True), callback_data=1),
                 InlineKeyboardButton(str(0) + " " + emojize(":ok_hand:", use_aliases=True), callback_data=2),
                 InlineKeyboardButton(str(0) + " " + emojize(":heart:", use_aliases=True), callback_data=3),
                 InlineKeyboardButton(emojize(":star:", use_aliases=True), callback_data=10),
                 InlineKeyboardButton("Votes", callback_data=11)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Give credit to who originally posted the photo/video
    if update.message.caption is not None:
        repost_caption = update.message.caption + "\n\nPosted by " + update.message.from_user.username
    else:
        repost_caption = "\n\nPosted by " + update.message.from_user.username

    while True:
        # Try sending photo
        try:
            # Send message with inline keyboard
            # Get message_id of re-posted image
            repost_id = context.bot.send_photo(chat_id=update.message.chat.id, photo=update.message.photo[-1].file_id,
                                               caption=repost_caption,
                                               reply_to_message_id=reply_message_id, reply_markup=reply_markup,
                                               timeout=20,
                                               parse_mode="HTML")['message_id']
            print("repost_id: " + str(repost_id))
            # Download file to hash
            file = context.bot.get_file(file_id=update.message.photo[-1].file_id)
            # Download the media (jpg, png)
            file_name = file.download(timeout=10)
            media_hash = compute_hash(file_name)
            # Find room name and assign correct database
            if update.message.chat.title == os.getenv("GROUP1"):
                database = os.getenv("DATABASE1")
            elif update.message.chat.title == os.getenv("GROUP2"):
                database = os.getenv("DATABASE2")
            elif update.message.chat.title == os.getenv("GROUP3"):
                database = os.getenv("DATABASE3")
            loop.run_until_complete(store_hash(database, repost_id, media_hash, loop))
        except Exception as e:
            print("Not a photo")
            print(str(e))
        else:
            # Delete original message
            context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            return
        # Try sending document animation
        try:
            # If user posts a document animation in reply to another message, ignore it
            if reply_message_id is not None:
                return
            # Send message with inline keyboard
            context.bot.send_animation(chat_id=update.message.chat.id, animation=update.message.document.file_id,
                                       caption=repost_caption,
                                       reply_to_message_id=reply_message_id, reply_markup=reply_markup, timeout=20,
                                       parse_mode="HTML")
        except Exception as e:
            print("Not a document video")
            print(str(e))
        else:
            # Delete original message
            context.bot.delete_message(
                chat_id=update.message.chat.id, message_id=update.message.message_id)
            return
        # Try sending video animation
        try:
            # If user posts a video animation in reply to another message, ignore it
            if reply_message_id is not None:
                return
            # Send message with inline keyboard
            context.bot.send_video(chat_id=update.message.chat.id, video=update.message.video.file_id,
                                   caption=repost_caption,
                                   reply_to_message_id=reply_message_id, reply_markup=reply_markup, timeout=20,
                                   parse_mode="HTML")
        except Exception as e:
            print("Not a video video")
            print(str(e))
        else:
            # Delete original message
            context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            return
        finally:
            return


@run_async
def button(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    query = update.callback_query
    if query.message.chat.type == "private":
        chat_type = "private"
        if int(query.data) == 20:
            message = loop.run_until_complete(get_user_karma(os.getenv("DATABASE1"), chat_type, loop))
            query.edit_message_text(text=message, parse_mode="Markdown", timeout=20)
        elif int(query.data) == 21:
            query.edit_message_text(
                text=loop.run_until_complete(get_user_karma(os.getenv("DATABASE2"), chat_type, loop)),
                parse_mode="Markdown", timeout=20)
        elif int(query.data) == 22:
            query.edit_message_text(
                text=loop.run_until_complete(get_user_karma(os.getenv("DATABASE3"), chat_type, loop)),
                parse_mode="Markdown", timeout=20)
    else:
        database = ""

        # Find original poster
        username = query.message.caption.split()

        # Find room name and assign correct database
        print("env GROUP1: " + os.getenv("GROUP1"))
        print("query.message.chat.title" + query.message.chat.title)
        if query.message.chat.title == os.getenv("GROUP1"):
            database = os.getenv("DATABASE1")
        elif query.message.chat.title == os.getenv("GROUP2"):
            database = os.getenv("DATABASE2")
        elif query.message.chat.title == os.getenv("GROUP3"):
            database = os.getenv("DATABASE3")

        if int(query.data) != 10 and int(query.data) != 11:
            self_vote = False
            # Prevent users from voting on their own posts
            if query.from_user.username == username[-1]:
                context.bot.answer_callback_query(callback_query_id=query.id, text="You can't vote on your own posts!",
                                                  show_alert=False, timeout=None)
                context.bot.send_message(chat_id=query.message.chat_id,
                                         text=query.from_user.username + " just tried to give themselves points.")
                context.bot.send_sticker(chat_id=query.message.chat_id, sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
                self_vote = True
            # Update database with emoji point data
            else:
                if self_vote is False:
                    try:
                        loop.run_until_complete(update_user_karma(
                            database, username[-1], "+", query.data, loop))
                        loop.run_until_complete(update_message_karma(
                            database, query.message.message_id, query.from_user.username, query.data, loop))
                        emoji_points = loop.run_until_complete(
                            check_emoji_points(database, query.message.message_id, loop))

                        # Update emoji points. Divide by 2 & 3 for ok_hand and heart to get the correct number of votes
                        keyboard = [[InlineKeyboardButton(
                            str(emoji_points[0]) + " " + emojize(":thumbsup:", use_aliases=True), callback_data=1),
                            InlineKeyboardButton(
                                str(emoji_points[1] / 2) + " " + emojize(":ok_hand:", use_aliases=True),
                                callback_data=2),
                            InlineKeyboardButton(
                                str(emoji_points[2] / 3) + " " + emojize(":heart:", use_aliases=True),
                                callback_data=3),
                            InlineKeyboardButton(emojize(":star:", use_aliases=True), callback_data=10),
                            InlineKeyboardButton("Votes", callback_data=11)]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        query.edit_message_reply_markup(reply_markup=reply_markup)

                        # Check to see which emoji user pressed
                        if int(query.data) == 1:
                            context.bot.answer_callback_query(callback_query_id=query.id, text="You " + emojize(
                                ":thumbsup:", use_aliases=True) + " this.", show_alert=False, timeout=None)
                        elif int(query.data) == 2:
                            context.bot.answer_callback_query(callback_query_id=query.id, text="You " + emojize(
                                ":ok_hand:", use_aliases=True) + " this.", show_alert=False, timeout=None)
                        elif int(query.data) == 3:
                            context.bot.answer_callback_query(callback_query_id=query.id, text="You " + emojize(
                                ":heart:", use_aliases=True) + " this.", show_alert=False, timeout=None)
                        return
                    except Exception as e:
                        print("Error while updating buttons: " + str(e))
                        context.bot.answer_callback_query(callback_query_id=query.id, text="Error. " + str(e),
                                                          show_alert=False, timeout=None)
                        return

        # Show popup showing who voted on the picture/video
        elif int(query.data) == 11:
            context.bot.answer_callback_query(
                callback_query_id=query.id,
                text=loop.run_until_complete(get_message_karma(database, query.message.message_id, loop)),
                show_alert=True, timeout=None)
        # Forward message that the user star'd
        elif int(query.data) == 10:
            try:
                # Get user's personal chat_id with Aqua
                tele_chat_id = loop.run_until_complete(get_chat_id(query.from_user.username, loop))
                # Send photo/video with link to the original message
                if update.callback_query.message.caption is not None:
                    repost_caption = update.callback_query.message.caption + "\n\n" + update.callback_query.message.link
                else:
                    repost_caption = "\n\n" + update.callback_query.message.link

                while True:
                    # Try sending photo
                    try:
                        # Send message with inline keyboard
                        context.bot.send_photo(chat_id=tele_chat_id,
                                               photo=update.callback_query.message.photo[-1].file_id,
                                               caption=repost_caption,
                                               timeout=20, parse_mode="HTML")
                    except:
                        print("Not a photo")
                    # Try sending document animation
                    try:
                        # Send message with inline keyboard
                        context.bot.send_animation(chat_id=tele_chat_id,
                                                   animation=update.callback_query.message.document.file_id,
                                                   caption=repost_caption,
                                                   timeout=20, parse_mode="HTML")
                    except:
                        print("Not a document video")
                    # Try sending video animation
                    try:
                        # Send message with inline keyboard
                        context.bot.send_video(chat_id=tele_chat_id, video=update.callback_query.message.video.file_id,
                                               caption=repost_caption,
                                               timeout=20, parse_mode="HTML")
                    except:
                        print("Not a video video")
                    finally:
                        context.bot.answer_callback_query(
                            callback_query_id=query.id, text="Saved!", show_alert=False, timeout=None)
                        return
            except Exception as e:
                context.bot.answer_callback_query(
                    callback_query_id=query.id, text="Error: " + str(e) + "\n" + "." +
                                                     "Have you PM'd me the '/addme' command?", show_alert=True,
                    timeout=None)


def main():
    token = os.getenv("TEL_BOT_TOKEN")
    q = mq.MessageQueue()
    # set connection pool size for bot
    request = Request(con_pool_size=54)
    qbot = MQBot(token, request=request, mqueue=q)
    updater = telegram.ext.updater.Updater(
        bot=qbot, workers=50, use_context=True)

    # Create handlers
    start_handler = CommandHandler("start", start)
    updater.dispatcher.add_handler(start_handler)

    delete_handler = CommandHandler("delete", delete)
    updater.dispatcher.add_handler(delete_handler)

    sauce_handler = CommandHandler("sauce", sauce)
    updater.dispatcher.add_handler(sauce_handler)

    source_handler = CommandHandler("source", source)
    updater.dispatcher.add_handler(source_handler)

    karma_handler = CommandHandler("karma", karma)
    updater.dispatcher.add_handler(karma_handler)

    addme_handler = CommandHandler("addme", addme)
    updater.dispatcher.add_handler(addme_handler)

    give_handler = CommandHandler("give", give)
    updater.dispatcher.add_handler(give_handler)

    repost_check_handler = CommandHandler("repost_check", repost_check)
    updater.dispatcher.add_handler(repost_check_handler)

    # on noncommand i.e message - repost the photo on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.photo, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - repost the video on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.animation, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - repost the video on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.video, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - repost the document on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.document, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    updater.dispatcher.add_error_handler(error)

    # Check to see if user wants to use polling or webhooks
    if os.getenv("USE_WEBHOOK") == "FALSE":
        # Start polling
        updater.start_polling()
    elif os.getenv("USE_WEBHOOK") == "TRUE":
        # Create webhook
        # Note: The following webhook configuration is setup to use a reverse proxy
        # See https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks for more info
        updater.start_webhook(listen="0.0.0.0", port=5001, url_path=os.getenv("TEL_BOT_TOKEN"))
        updater.bot.set_webhook(url="https://" + os.getenv("DOMAIN") + "/" + os.getenv("TEL_BOT_TOKEN"))

    updater.idle()


if __name__ == "__main__":
    main()
