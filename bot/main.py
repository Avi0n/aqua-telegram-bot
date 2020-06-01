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
import time
from random import randint
from pathlib import Path

import imagehash
import imageio
import sqlite_functions as db
import telegram.bot
from PIL import Image
from dotenv import load_dotenv
from emoji import emojize
from pixivapi import Client
from get_tags import get_tags
from get_tags import convert_string_tags
from saucenao import get_source
from saucenao import get_image_source
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (BadRequest)
from telegram.ext import MessageHandler, CommandHandler, \
    CallbackQueryHandler, Filters
from telegram.ext import messagequeue as mq
from telegram.ext.dispatcher import run_async
from telegram.utils.request import Request

#if os.getenv("USE_MYSQL") == "TRUE":
#    import mariadb_functions as db
#else:
#    import sqlite_functions as db

# Initialize dotenv
load_dotenv()

# Initialize logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.os.getenv("BOT_LOG_LEVEL"))

logger = logging.getLogger(__name__)

# Login to Pixiv
if os.getenv("AUTH_ROOMS_ONLY") == "TRUE":
    pixiv_c = Client()
    pixiv_c.login(os.getenv("PIXIV_USER"), os.getenv("PIXIV_PASS"))


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
        # Wrapped method would accept new 'queued' and 'isgroup'
        # OPTIONAL arguments
        return super(MQBot, self).send_message(*args, **kwargs)


# Convert mp4 to gif. Copy paste from:
# https://gist.github.com/michaelosthege/cd3e0c3c556b70a79deba6855deb2cc8
class TargetFormat(object):
    GIF = ".gif"
    MP4 = ".mp4"
    AVI = ".avi"


def convert_media(inputpath, targetFormat):
    # Reference:
    # http://imageio.readthedocs.io/en/latest/examples.html#convert-a-movie
    outputpath = "./media/source" + targetFormat
    print("converting\r\n\t{0}\r\nto\r\n\t{1}".format(inputpath, outputpath))

    reader = imageio.get_reader(inputpath)
    fps = reader.get_meta_data()["fps"]

    writer = imageio.get_writer(outputpath, fps=fps)
    for x, im in enumerate(reader):
        sys.stdout.write("\rframe {0}".format(x))
        sys.stdout.flush()
        writer.append_data(im)
    print("\r\nFinalizing conversion...")
    writer.close()
    print("Done converting.")


def delete_media(**kwargs):
    file_name = kwargs.get('media_name', None)

    if file_name is not None:
        path = os.path.join("./", file_name)
        os.remove(path)
    else:
        # Cleanup downloaded media
        try:
            # Cleanup downloaded media
            for fname in os.listdir("./media"):
                if fname.endswith(".gif"):
                    os.remove("source.gif")
                elif fname.endswith(".jpg"):
                    os.remove(fname)
        except Exception as e:
            print("Error in delete_media(): " + str(e))


def compute_hash(file_name):
    try:
        img = Image.open(file_name)
        media_hash = imagehash.phash(img)
    except Exception as e:
        print("Error in compute_hash: " + str(e))

    return media_hash


def check_auth_room(room_id):
    # If AUTH_ROOMS_ONLY is set to TRUE in .env, only allow bot to
    # be used in specified rooms
    if os.getenv("AUTH_ROOMS_ONLY") == "TRUE":
        authorized_status = False
        group_ids = [
            os.getenv("GROUP1ID"),
            os.getenv("GROUP2ID"),
            os.getenv("GROUP3ID")
        ]

        for x in range(len(group_ids)):
            if room_id == group_ids[x]:
                authorized_status = True
                break
    # If AUTH_ROOMS_ONLY is set to FALSE in .env, anyone can use
    # the bot
    else:
        authorized_status = True
    return authorized_status


@run_async
# Respond to /start
def start(update, context):
    if update.message.chat.type == "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Use /addme to let me forward media that you " +
            emojize(":star:", use_aliases=True) + " to you!")
    # Check to see if bot can be used in this group chat
    elif check_auth_room(str(update.message.chat.id)) is False:
        return
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Populate db with room's id
        if db.populate_db(str(update.message.chat.id), loop) is True:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="Your group has already been added.")
        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="Your group has been added! I will" +
                                     " now repost photos/videos/gifs with" +
                                     " reaction emojis! You can put" +
                                     ' "no aqua" somewhere in the caption if' +
                                     " you don't want me to repost." +
                                     " Have fun :)")


# Respond to /sauce
def sauce(update, context):
    source(update, context)


# Respond to /source
def source(update, context):
    # Check if only authorized rooms can use this command
    if os.getenv("SOURCE_COMMAND_AUTH_ROOMS_ONLY") == "TRUE":
        # Make sure the command is being used in an authorized room
        if str(update.message.chat.id) in (os.getenv("GROUP1ID"),
                                           os.getenv("GROUP2ID"),
                                           os.getenv("GROUP3ID")):
            pass
        else:
            return
    # Check if the user replied to anything
    if update.message.reply_to_message is None:
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="Did you forget to reply to an image?")
    else:
        # Get media's file_id
        try:
            media_id = update.message.reply_to_message.photo[1].file_id
        except IndexError:
            try:
                media_id = update.message.reply_to_message.document.file_id
            except IndexError:
                try:
                    media_id = update.message.reply_to_message.video.file_id
                except IndexError:
                    pass
                    media_id = None
        if media_id is not None:
            # Get the download link from Telegram
            file = context.bot.get_file(file_id=media_id)
            # Find the file name
            file_split = file.file_path.split("/")
            # Download the media (jpg, png, mp4)
            file.download(custom_path=f"./media/{file_split[6]}", timeout=10)
            file_name = f"./media/{file_split[6]}"
            # If it's an mp4, convert it to gif
            if file_name.endswith(".mp4"):
                convert_media(file_name, TargetFormat.GIF)
                os.remove(file_name)
                file_name = "./media/source.gif"

            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=get_source(file_name),
                                     parse_mode='Markdown',
                                     disable_web_page_preview=True)

            # Cleanup downloaded media
            delete_media(media_name=file_name)


@run_async
# Allow user to delete their own photo
def delete(update, context):
    # If the command is being used in a private chat, return
    if update.message.chat.type == "private":
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="You can't use that command here.")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    database = str(update.message.chat.id)

    username = update.message.reply_to_message.caption.split()
    delete_message_id = update.message.reply_to_message.message_id

    # Only allow original poster to delete their own message
    if username[-1] == update.message.from_user.username:
        try:
            points_to_delete = loop.run_until_complete(
                db.delete_row(database, delete_message_id, loop))
            if points_to_delete[0] is not None:
                loop.run_until_complete(
                    db.update_user_karma(database, username[-1], "-",
                                         str(points_to_delete[0]), loop))
            # Remove message that user replied to
            context.bot.delete_message(chat_id=update.message.chat_id,
                                       message_id=delete_message_id)
            # Remove the "/delete" message the user sent to keep the chat clean
            context.bot.delete_message(chat_id=update.message.chat_id,
                                       message_id=update.message.message_id)
        except Exception as e:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="Error: " + str(e))
    else:
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="You can only delete your own posts.")


# Respond to /karma
@run_async
def karma(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Find out which database to use.
    # If the chat is private, watch for user specified database
    if os.getenv("AUTH_ROOMS_ONLY"
                 ) == "TRUE" and update.message.chat.type == "private":
        keyboard = [[
            InlineKeyboardButton(os.getenv("GROUP1"), callback_data="20"),
            InlineKeyboardButton(os.getenv("GROUP2"), callback_data="21")
        ], [InlineKeyboardButton(os.getenv("GROUP3"), callback_data="22")]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Please choose a room.",
                                  reply_markup=reply_markup)
    elif update.message.chat.type == "private":
        return
    else:
        # If not a private chat, check the room name to match to a database
        message = loop.run_until_complete(
            db.get_user_karma(str(update.message.chat.id), loop))

        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=message,
                                 parse_mode="Markdown",
                                 timeout=20)


@run_async
# Respond to /give
def give(update, context):
    # If the command is being used in a private chat, return
    if update.message.chat.type == "private":
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="You can't use that command here.")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Find out which database to use
    database = str(update.message.chat.id)

    # Check to see if user used the right command format
    if "@" in update.message.text:
        # Remove all punctuation (@) and split the string
        string_split = update.message.text.split()
        username = string_split[1].translate(
            str.maketrans("", "", string.punctuation))
        points = string_split[2]
        points_no_punc = points.translate(
            str.maketrans("", "", string.punctuation))
        from_username = update.message.from_user.username

        try:
            if os.getenv("WEEBIFY") == "TRUE":
                if username == from_username:
                    context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=update.message.from_user.username +
                        " just tried to give themselves points.")
                    context.bot.send_sticker(
                        chat_id=update.message.chat_id,
                        sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
                elif int(points) == 0:
                    context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text="pfft, you just tried to give someone 0 points.")
                    context.bot.send_sticker(
                        chat_id=update.message.chat_id,
                        sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            if int(points) < -20:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="That's too many points to be taking away.")
            elif -21 < int(points) < 0:
                loop.run_until_complete(
                    db.update_user_karma(database, username, "-",
                                         points_no_punc, loop))
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " took away " +
                                         points + " points from " + username +
                                         "!")
            elif 51 > int(points) > 0:
                loop.run_until_complete(
                    db.update_user_karma(database, username, "+",
                                         points_no_punc, loop))
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " gave " +
                                         username + " " + points + " points!")
            elif int(points) > 51:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="Points must be less than 51")
        except Exception as e:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="Error: " + str(e))
    else:
        string_split = update.message.text.split()
        username = string_split[1]
        points = string_split[2]
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="The correct format is '/give @" +
                                 username + " " + points + "'")


@run_async
# Respond to /addme
def addme(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    chat_type = update.message.chat.type
    username = update.message.from_user.username
    chat_id = update.message.chat_id

    context.bot.send_message(chat_id=chat_id,
                             text=loop.run_until_complete(
                                 db.addme_async(chat_type, username, chat_id,
                                                loop)))


# Respond to /check_repost
def repost_check(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Find group id and assign correct database
    database = str(update.message.chat.id)

    # Fetch hash of message_id that /repost_challenge was used on
    photo_hash = loop.run_until_complete(
        db.fetch_one_hash(update.message.reply_to_message.message_id, database,
                          loop))
    # Fetch all stored hashes
    hash_list = loop.run_until_complete(
        db.fetch_all_hashes(update.message.reply_to_message.message_id,
                            database, loop))

    message_id_dupe_list = []
    dupes = 0
    # Compare hash or message command was used on with all other hashes
    for x in range(len(hash_list)):
        # If the hash difference is less than 10, assume it is a duplicate
        if (imagehash.hex_to_hash(photo_hash[0]) -
                imagehash.hex_to_hash(hash_list[x][1])) < 10:
            dupes += 1
            # Store duplicate photo message ids
            message_id_dupe_list.append(str(hash_list[x][0]))

    # If duplicates were found, let the user know
    if dupes > 1:
        # Make sure user isn't using command on the
        # first occurrence of the photo
        if message_id_dupe_list[
                0] == update.message.reply_to_message.message_id:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text="This is the first time this photo has "
                "been posted in the last 30 days, but "
                "it has been reposted " + str(dupes) + " times since then.")
            return

        message_text = "Yep, that's a repost. " \
                       + "Here's the first occurance I could find." \
                       + "\nIt's been posted " \
                       + str(dupes) + " times in the last 30 days."
        message_sent = False
        for x in range(len(message_id_dupe_list)):
            # If this is the last dupe message_id, the ones before it
            # have been deleted either by the user or an admin.
            # Send a different message.
            if x + 1 == len(message_id_dupe_list) and message_sent is False:
                message_text = "Yep, that's a repost.\nIt's been" \
                               + " posted " + str(dupes) \
                               + " times in the last 30 days, but" \
                               + " I couldn't find the others." \
                               + " Maybe they were deleted?"
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=message_text)
            elif message_sent is True:
                break
            else:
                try:
                    context.bot.send_message(
                        chat_id=update.message.chat_id,
                        reply_to_message_id=message_id_dupe_list[x],
                        text=message_text).result()
                    message_sent = True
                # TODO: Find a better way to handle "Reply message not found"
                # Currently prints error to console and it should not
                except BadRequest:
                    continue
    else:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Hmm... doesn't look like a repost to me.")


@run_async
# Repost media to the channel with an inline emoji keyboard
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
    except AttributeError:
        pass

    # Check to see if user doesn't want their photo to be deleted
    if update.message.caption is not None:
        if "noaqua" in update.message.caption.replace(" ", "").lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return
        elif "aquano" in update.message.caption.replace(" ", "").lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return

    try:
        # Download file to hash
        file = context.bot.get_file(file_id=update.message.photo[-1].file_id)
        # Find the file name
        file_split = file.file_path.split("/")
        # Download the media (jpg, png)
        file.download(custom_path=f"./media/{file_split[6]}", timeout=10)
        file_name = f"./media/{file_split[6]}"
        is_photo = True
    except IndexError:
        # Not a photo, don't download
        is_photo = False
        pass

    # Only allow SauceNao fetching in specified rooms
    if os.getenv("AUTH_ROOMS_ONLY"
                 ) == "TRUE" and update.message.chat.title in os.getenv(
                     "TAG_LOOKUP_ROOMS") and is_photo:
        print("Starting new image")

        # This is bad, I know. I need to figure out a better way of 
        # spacing out these calls
        temp_rand = randint(1,100)
        print(f"Starting sleep: {temp_rand}")
        time.sleep(randint(3,10))
        print(f"Ending sleep: {temp_rand}")
        tags_list = []
        tags = ""
        fetch_tags = True
        source_result = get_image_source(file_name)

        if source_result == 3:
            print("Miss or no results")
            fetch_tags = False
        elif source_result == 0:
            print("Bad image or other SauceNao API error.")
            fetch_tags = False
        elif source_result == 1:
            print("SauceNao API error.")
            fetch_tags = False
        elif source_result == 2:
            # Out of searches
            print("Out of searches for today...")
            fetch_tags = False

        if fetch_tags:
            try:
                #post_id = source_result[0]
                material = source_result[1]
                characters = source_result[2]
                temp_list = []

                material = material.split(",")
                for x in range(len(material)):
                    temp_list.append(material[x])

                characters = characters.split(",")
                for x in range(len(characters)):
                    temp_list.append(characters[x])
                
                blacklist_tags = os.getenv("BLACKLIST_TAGS").split(",")
                tags = convert_string_tags(temp_list, blacklist_tags)
            except Exception as e:
                # if str(e) == "list index out of range":
                #     post_id = source_result[0]
                #     try:
                #         tags = get_tags(pixiv_c, post_id)
                #     except Exception as e:
                #         print(f"Error in repost() line 585: {e}")
                # else:
                    print(f"Error in repost() line 588: {e}")
            try:
                # Remove pound signs and store tags in a dictionary
                tags_no_h = tags.replace("#", "")
                tags_split = tags_no_h.split()
                for x in range(len(tags_split)):
                    tags_list.append(tags_split[x])

                for x in range(0, 2):
                    db_status = loop.run_until_complete(
                        db.store_tags(update.message.message_id, tags_list,
                                        str(update.message.chat.id)))
                    # If store_tags() returned False, the db doesn't exist
                    if db_status is False:
                        db.populate_db(str(update.message.chat.id), loop)
                    else:
                        break
                else:
                    tags = ""
            except Exception as e:
                print(f"Exception while fetching Pixiv tags: {e}")
                tags = ""
    else:
        tags = ""

    # Get hash and delete downloaded photo if the media sent was a photo
    if is_photo:
        media_hash = compute_hash(file_name)
        # Cleanup downloaded media
        delete_media(media_name=file_name)

    keyboard = [[
        InlineKeyboardButton(str(0) + " " +
                             emojize(":thumbsup:", use_aliases=True),
                             callback_data=1),
        InlineKeyboardButton(str(0) + " " +
                             emojize(":ok_hand:", use_aliases=True),
                             callback_data=2),
        InlineKeyboardButton(str(0) + " " +
                             emojize(":heart:", use_aliases=True),
                             callback_data=3),
        InlineKeyboardButton(emojize(":star:", use_aliases=True),
                             callback_data=10),
        InlineKeyboardButton("Votes", callback_data=11)
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # See if the caption is formatted i.e. bold, italic, etc.
    try:
        caption_ent_check = update.message.caption_entities[-1]
    except Exception as e:
        if str(e) == "list index out of range":
            caption_ent_check = None
            pass
    # Give credit to who originally posted the photo/video
    if update.message.caption is not None:
        # Create Markdown formatting/links
        if caption_ent_check is not None:
            ent_num = len(update.message.caption_entities)
            cap_ent = update.message.caption_entities
            caption = update.message.caption
            cap_formatted = ""
            last_pos = 0
            is_mention = False
            for x in range(ent_num):
                if "url" in str(cap_ent[x]):
                    url = cap_ent[x].url
                    is_url = True
                else:
                    is_url = False
                offset = cap_ent[x].offset
                length = cap_ent[x].length
                cur_pos = offset + length
                # First letter of format type i.e. 'b' when 'bold'
                fl_ft = cap_ent[x].type[0]
                if fl_ft == "c":
                    fl_ft = "code"
                # Check if it's a mention
                elif fl_ft == "m":
                    is_mention = True

                # If offset is 0, the first character is formatted
                if offset == 0:
                    if is_url is True:
                        cap_formatted += f"<a href='{url}'>{caption[:length]}</a>"
                    elif is_mention is True:
                        cap_formatted += f"{caption[:length]}"
                    else:
                        cap_formatted += f"<{fl_ft}>{caption[:length]}</{fl_ft}>"
                    last_pos = cur_pos
                else:
                    if is_url is True:
                        cap_formatted += caption[last_pos:offset] \
                                        + "<a href='" + url + "'>" \
                                        + caption[offset:cur_pos] \
                                        + "</a>"
                    elif is_mention is True:
                        cap_formatted += caption[last_pos:offset] \
                                        + caption[offset:cur_pos]
                    else:
                        cap_formatted += caption[last_pos:offset] \
                                      + "<" + fl_ft + ">" \
                                      + caption[offset:cur_pos] \
                                      + "</" + fl_ft + ">"
                    last_pos = cur_pos
                if x == ent_num - 1:
                    # Attach rest of message
                    # If we're at the last character, attach Posted by
                    if cur_pos == len(caption):
                        repost_caption = cap_formatted \
                                        + "\n" + tags \
                                        + "\n\nPosted by " \
                                        + update.message.from_user.username
                    # If we're not at the last character, attach the rest of
                    # the caption before attaching Posted by
                    else:
                        repost_caption = cap_formatted + caption[cur_pos:] \
                                        + "\n" + tags + "\nPosted by " \
                                        + update.message.from_user.username
        # No formatting in caption, attach caption to message
        else:
            repost_caption = update.message.caption \
                            + "\n" + tags + "\nPosted by " \
                            + update.message.from_user.username
    else:
        repost_caption = tags + "\nPosted by " + update.message.from_user.username

    while True:
        # Try sending photo
        try:
            # Send message with inline keyboard
            # Get message_id of reposted image
            repost_id = context.bot.send_photo(
                chat_id=update.message.chat.id,
                photo=update.message.photo[-1].file_id,
                caption=repost_caption,
                reply_to_message_id=reply_message_id,
                reply_markup=reply_markup,
                disable_notification=True,
                timeout=20,
                parse_mode="HTML")['message_id']
            # Find room name and assign correct database
            database = str(update.message.chat.id)

            loop.run_until_complete(
                db.store_hash(database, repost_id, str(media_hash), loop))
        except IndexError:
            pass
        # Try sending document animation
        try:
            # If user posts a document animation in reply to another message,
            # ignore it
            if reply_message_id is not None:
                return
            # Send message with inline keyboard
            context.bot.send_animation(
                chat_id=update.message.chat.id,
                animation=update.message.document.file_id,
                caption=repost_caption,
                reply_to_message_id=reply_message_id,
                reply_markup=reply_markup,
                disable_notification=True,
                timeout=20,
                parse_mode="HTML")
        except AttributeError:
            pass
        # Try sending video animation
        try:
            # If user posts a video animation in reply to another message,
            # ignore it
            if reply_message_id is not None:
                return
            # Send message with inline keyboard
            context.bot.send_video(chat_id=update.message.chat.id,
                                   video=update.message.video.file_id,
                                   caption=repost_caption,
                                   reply_to_message_id=reply_message_id,
                                   reply_markup=reply_markup,
                                   disable_notification=True,
                                   timeout=20,
                                   parse_mode="HTML")
        except AttributeError:
            pass
        finally:
            # Delete original message
            context.bot.delete_message(chat_id=update.message.chat.id,
                                       message_id=update.message.message_id)
            return


@run_async
def button(update, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    query = update.callback_query

    # Find room name and assign correct database
    database = str(query.message.chat.id)

    if query.message.chat.type == "private":
        if os.getenv("AUTH_ROOMS_ONLY") == "TRUE":
            if int(query.data) == 20:
                query.edit_message_text(
                    text=os.getenv("GROUP1") + "\n" + loop.run_until_complete(
                        db.get_user_karma(os.getenv("GROUP1ID"), loop)),
                    parse_mode="Markdown",
                    timeout=20)
            elif int(query.data) == 21:
                query.edit_message_text(
                    text=os.getenv("GROUP2") + "\n" + loop.run_until_complete(
                        db.get_user_karma(os.getenv("GROUP2ID"), loop)),
                    parse_mode="Markdown",
                    timeout=20)
            elif int(query.data) == 22:
                query.edit_message_text(
                    text=os.getenv("GROUP3") + "\n" + loop.run_until_complete(
                        db.get_user_karma(os.getenv("GROUP3ID"), loop)),
                    parse_mode="Markdown",
                    timeout=20)
        else:
            return
    else:
        # Find original poster
        username = query.message.caption.split()

        if int(query.data) != 10 and int(query.data) != 11:
            self_vote = False
            # Prevent users from voting on their own posts
            if query.from_user.username == username[-1]:
                context.bot.answer_callback_query(
                    callback_query_id=query.id,
                    text="You can't vote on your own posts!",
                    show_alert=True,
                    timeout=None)
                if os.getenv("WEEBIFY") == "TRUE":
                    context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=query.from_user.username +
                        " just tried to give themselves points.")
                    context.bot.send_sticker(
                        chat_id=query.message.chat_id,
                        sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
                self_vote = True
            # Update database with emoji point data
            else:
                if self_vote is False:
                    try:
                        # If db returns true, user has already pressed this
                        # emoji
                        user_voted = loop.run_until_complete(
                            db.update_message_karma(database,
                                                    query.message.message_id,
                                                    query.from_user.username,
                                                    query.data, loop))
                        # If user hasn't already pressed this emoji,
                        # add a point from their overall karma
                        if user_voted is False:
                            loop.run_until_complete(
                                db.update_user_karma(database,
                                                     username[-1], "+",
                                                     str(query.data), loop))
                        # Otherwise subtract a point
                        else:
                            loop.run_until_complete(
                                db.update_user_karma(database,
                                                     username[-1], "-",
                                                     str(query.data), loop))
                        # Check db to make sure we have the correct vote count
                        emoji_points = loop.run_until_complete(
                            db.check_emoji_points(database,
                                                  query.message.message_id,
                                                  loop))

                        # Update keyboard emoji points
                        keyboard = [[
                            InlineKeyboardButton(
                                str(emoji_points[0]) + " " +
                                emojize(":thumbsup:", use_aliases=True),
                                callback_data=1),
                            InlineKeyboardButton(
                                str(emoji_points[1]) + " " +
                                emojize(":ok_hand:", use_aliases=True),
                                callback_data=2),
                            InlineKeyboardButton(
                                str(emoji_points[2]) + " " +
                                emojize(":heart:", use_aliases=True),
                                callback_data=3),
                            InlineKeyboardButton(emojize(":star:",
                                                         use_aliases=True),
                                                 callback_data=10),
                            InlineKeyboardButton("Votes", callback_data=11)
                        ]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        query.edit_message_reply_markup(
                            reply_markup=reply_markup)

                        # If the user hasn't pressed this emoji before,
                        # send toast notification to let them know
                        # which emoji they pressed
                        if user_voted is False:
                            if int(query.data) == 1:
                                context.bot.answer_callback_query(
                                    callback_query_id=query.id,
                                    text="You " +
                                    emojize(":thumbsup:", use_aliases=True) +
                                    " this.",
                                    show_alert=False,
                                    timeout=None)
                            elif int(query.data) == 2:
                                context.bot.answer_callback_query(
                                    callback_query_id=query.id,
                                    text="You " +
                                    emojize(":ok_hand:", use_aliases=True) +
                                    " this.",
                                    show_alert=False,
                                    timeout=None)
                            elif int(query.data) == 3:
                                context.bot.answer_callback_query(
                                    callback_query_id=query.id,
                                    text="You " +
                                    emojize(":heart:", use_aliases=True) +
                                    " this.",
                                    show_alert=False,
                                    timeout=None)
                        # Send toast letting user know they took their
                        # reaction back
                        else:
                            context.bot.answer_callback_query(
                                callback_query_id=query.id,
                                text="You took your reaction back.",
                                show_alert=False,
                                timeout=None)
                        return
                    except Exception as e:
                        print("Error while updating buttons: " + str(e))
                        context.bot.answer_callback_query(
                            callback_query_id=query.id,
                            text="Error. " + str(e),
                            show_alert=False,
                            timeout=None)
                        return

        # Show popup showing who voted on the picture/video
        elif int(query.data) == 11:
            context.bot.answer_callback_query(
                callback_query_id=query.id,
                text=loop.run_until_complete(
                    db.get_message_karma(database, query.message.message_id,
                                         loop)),
                show_alert=True,
                timeout=None)
        # Forward message that the user star'd
        elif int(query.data) == 10:
            try:
                # Get user's personal chat_id with Aqua
                tele_chat_id = loop.run_until_complete(
                    db.get_chat_id(query.from_user.username, loop))
                # Send photo/video with link to the original message
                if update.callback_query.message.caption is not None:
                    repost_caption = update.callback_query.message.caption \
                                     + "\n\n" \
                                     + update.callback_query.message.link
                else:
                    repost_caption = "\n\n" \
                                     + update.callback_query.message.link

                while True:
                    # Try sending photo
                    try:
                        # Send message with inline keyboard
                        context.bot.send_photo(chat_id=tele_chat_id,
                                               photo=update.callback_query.
                                               message.photo[-1].file_id,
                                               caption=repost_caption,
                                               timeout=20,
                                               parse_mode="HTML")
                    except (IndexError, AttributeError):
                        pass
                    # Try sending document animation
                    try:
                        # Send message with inline keyboard
                        context.bot.send_animation(
                            chat_id=tele_chat_id,
                            animation=update.callback_query.message.document.
                            file_id,
                            caption=repost_caption,
                            timeout=20,
                            parse_mode="HTML")
                    except (IndexError, AttributeError):
                        pass
                    # Try sending video animation
                    try:
                        # Send message with inline keyboard
                        context.bot.send_video(
                            chat_id=tele_chat_id,
                            video=update.callback_query.message.video.file_id,
                            caption=repost_caption,
                            timeout=20,
                            parse_mode="HTML")
                    except (IndexError, AttributeError):
                        pass
                    finally:
                        context.bot.answer_callback_query(
                            callback_query_id=query.id,
                            text="Saved!",
                            show_alert=False,
                            timeout=None)
                        return
            except Exception as e:
                context.bot.answer_callback_query(
                    callback_query_id=query.id,
                    text="Have you PM'd me the '/addme' command?",
                    show_alert=True,
                    timeout=None)


def main():
    print("Starting Aqua 3.2 beta 10.4")
    # Check to see if db folder exists
    if Path("db").exists() is True:
        pass
    else:
        print("db folder does not exist, creating it.")
        Path("db").mkdir(parents=True, exist_ok=True)
    # Check to see if all db tables exist
    db.check_tables_exist()

    token = os.getenv("TEL_BOT_TOKEN")
    q = mq.MessageQueue(group_burst_limit=19, group_time_limit_ms=60050)
    # set connection pool size for bot
    request = Request(con_pool_size=54)
    qbot = MQBot(token, request=request, mqueue=q)
    updater = telegram.ext.updater.Updater(bot=qbot,
                                           workers=50,
                                           use_context=True)

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
        # The following webhook configuration is setup to use a reverse proxy
        # See https://github.com/python-telegram-bot/python-telegram-bot\
        # /wiki/Webhooks for more info
        updater.start_webhook(listen="0.0.0.0",
                              port=5001,
                              url_path=os.getenv("TEL_BOT_TOKEN"))
        updater.bot.set_webhook(url="https://" + os.getenv("DOMAIN") + "/" +
                                os.getenv("TEL_BOT_TOKEN"))

    updater.idle()


if __name__ == "__main__":
    main()
