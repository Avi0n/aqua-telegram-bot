import os
import logging
import MySQLdb
import string
from dotenv import load_dotenv
from emoji import emojize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CommandHandler, BaseFilter, CallbackQueryHandler, Filters, Updater
# Imports needed for source()
import sys
import io
import requests
from PIL import Image
import json
import codecs
import time
from collections import OrderedDict
# Imports needed for convert_media()
import sys
import imageio


''' 
TODO:
- Prevent users from being able to vote more than once
- Allow user to take back their vote
'''

# Initialize dotenv
load_dotenv()

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# Retrieve user's karma from the database
def get_user_karma(database):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    return_message = ""
    sql = "SELECT * FROM user_karma WHERE karma <> 0 ORDER BY username;"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

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
            karma = row[1]
            return_message += username + (" " * (longest_username_length - len(username))) + \
                "   " + (" " * (longest_karma_length -
                                len(str(karma)))) + str(karma) + "\n"

        return_message += "\n```" + emojize(":v:", use_aliases=True)

    except Exception as e:
        return_message += "Error: " + str(e)
        print("get_user_karma() error: " + str(e))
    finally:
        cursor.close()
        db.close()
    return return_message


# Increment the total karma for a specific user
def update_user_karma(database, username, plus_or_minus, points):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    sql = "SELECT * FROM user_karma WHERE username = '" + username + "';"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    if result is None:
        # Add username to the database along with the points that were just added
        sql = "INSERT INTO user_karma VALUES ('" + username + "', " + points + ");"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Commit your changes in the database
            db.commit()
        except Exception as e:
            # Rollback in case there is any error
            db.rollback()
            print("update_karma error: " + str(e))
        finally:
            cursor.close()
            db.close()
    else:
        sql = "UPDATE user_karma SET karma = karma" + plus_or_minus + \
            points + " WHERE username = '" + username + "';"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Commit your changes in the database
            db.commit()
        except Exception as e:
            # Rollback in case there is any error
            db.rollback()
            print("update_karma error: " + str(e))
        finally:
            cursor.close()
            db.close()

'''
# Check the toggle state of an emoji
def check_for_previous_vote(message_id, username, emoji_symbol):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    sql = "SELECT " + emoji_symbol + " FROM message_karma WHERE message_id = " + \
            str(message_id) + " AND username = '" + username + "';"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    finally:
        cursor.close()
        db.close()
    if int(result) is not 0:
        return True
    else:
        return False
'''

def update_message_karma(database, message_id, username, emoji_points):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    thumb_points = 0
    ok_points = 0
    heart_points = 0
    # Figure out which column to update
    if int(emoji_points) is 1:
        emoji_symbol = 'thumbsup'
        thumb_points = 1
    elif int(emoji_points) is 2:
        emoji_symbol = 'ok_hand'
        ok_points = 2
    elif int(emoji_points) is 3:
        emoji_symbol = 'heart'
        heart_points = 3

    sql = "SELECT * FROM message_karma WHERE message_id = " + \
        str(message_id) + " AND username = '" + username + "';"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    if result is None:
        # Insert new row with message_id, username, and emoji point values
        sql = "INSERT INTO message_karma VALUES (" + str(message_id) + ", '" + username + \
            "', " + str(thumb_points) + ", " + str(ok_points) + ", " + str(heart_points) + ");"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Commit your changes in the database
            db.commit()
        except Exception as e:
            # Rollback in case there is any error
            db.rollback()
            print("update_message_karma insert error: " + str(e))
        finally:
            cursor.close()
            db.close()
    else:
        # Update emoji points that user has given a specific message_id
        sql = "UPDATE message_karma SET " + emoji_symbol + " = " + emoji_symbol + " + " + str(emoji_points) + \
            " WHERE message_id = " + \
            str(message_id) + " AND username = '" + username + "';"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Commit your changes in the database
            db.commit()
        except Exception as e:
            # Rollback in case there is any error
            db.rollback()
            print("update_message_karma error: " + str(e))
        finally:
            cursor.close()
            db.close()


# Get total karma per user for a specific message
def get_message_karma(database, message_id):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=database)
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    return_message = ""
    # SELECT SUM(thumbsup + ok_hand + heart) FROM message_karma WHERE message_id=2337 AND username='Avi0n' 
    sql = "SELECT username, SUM(thumbsup + ok_hand + heart) AS karma FROM message_karma WHERE message_id = " + \
            str(message_id) + " GROUP BY username ORDER BY username;"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        # Find length of longest username and karma
        longest_username_length = 0
        longest_karma_length = 0
        for row in results:
            longest_username_length = max(longest_username_length, len(row[0]))
            longest_karma_length = max(longest_karma_length, len(str(row[1])))

        # Add each user and karma as its own row
        for row in results:
            username = row[0]
            karma = row[1]
            return_message += username + (" " * (longest_username_length - len(username))) + \
                "   " + (" " * (longest_karma_length -
                                len(str(karma)))) + str(karma) + "\n"
    except Exception as e:
        return_message += "Error"
        print("get_message_karma() error: " + str(e))
    finally:
        cursor.close()
        db.close()
    return return_message


# Get user's personal chat_id with Aqua
def get_chat_id(tele_user):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=os.getenv("DATABASE1"))
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    sql = "SELECT chat_id FROM user_chat_id WHERE username = '" + \
        str(tele_user) + "';"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchone()
        return result[0]
    except Exception as e:
        print("Error: " + str(e))
    finally:
        cursor.close()
        db.close()


# Respond to /start
def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Send /karma to see everyone's points.\nSend /addme to let me forward" +
                             " photos that you " + emojize(":star:", use_aliases=True) + " to you!")


# Allow user to delete their own photo
def delete(update, context):
    username = update.message.reply_to_message.caption.split()

    # Only allow original poster to delete their own message
    if username[-1] == update.message.from_user.username:
        # Remove message that user replied to
        context.bot.delete_message(
            chat_id=update.message.chat_id, message_id=update.message.reply_to_message.message_id)
        # Remove the '/delete' message the user sent to keep the chat clean
        context.bot.delete_message(
            chat_id=update.message.chat_id, message_id=update.message.message_id)
    else:
        context.bot.send_message(
            chat_id=update.message.chat_id, text='You can only delete your own posts.')


# Respond to /karma
def karma(update, context):
    database = ''
    # Find out which database to use
    if update.message.chat.title == os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif update.message.chat.title == os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")
    context.bot.send_message(chat_id=update.message.chat_id,
                             text=get_user_karma(database), parse_mode='Markdown', timeout=20)


# Respond to /give
def give(update, context):
    database = ''
    # Find out which database to use
    if context.update.message.chat.title is os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif context.update.message.chat.title is os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")

    # Check to see if user used the right command format
    if '@' in update.message.text:
        # Remove all punctuation (@) and split the string
        string_split = update.message.text.translate(
            str.maketrans('', '', string.punctuation)).split()
        username = string_split[1]
        points = string_split[2]
        from_username = update.message.from_user.username

        try:
            if username == from_username:
                context.bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                         " just tried to give themselves points.")
                context.bot.send_sticker(chat_id=update.message.chat_id,
                                         sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            elif int(points) is 0:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="pfft, you just tried to give someone 0 points.")
                context.bot.send_sticker(chat_id=update.message.chat_id,
                                         sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            elif int(points) < -20:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="Don't you think that's a tad too many points to be taking away?")
            elif -21 < int(points) < 0:
                update_user_karma(database, username, '+', points)
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " took away " + points + " points from " + username + "!")
            elif 61 > int(points) > 0:
                update_user_karma(database, username, '+', points)
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=from_username + " gave " + username + " " + points + " points!")
            elif int(points) > 61:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text="Don't you think that's a tad too many points?")
        except Exception as e:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="There was a problem. Please send the following message to @Avi0n")
            context.bot.send_message(
                chat_id=update.message.chat_id, text=str(e))
    else:
        string_split = update.message.text.split()
        username = string_split[1]
        points = string_split[2]
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="The correct format is '/give @" + username + " " + points + "'")


# Respond to /addme
def addme(update, context):
    # Make sure the /addme command is being sent in a PM
    if not update.message.chat.title:
        username = update.message.from_user.username
        chat_id = update.message.chat_id
        # Set MySQL settings
        db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                             user=os.getenv("MYSQL_USER"),
                             passwd=os.getenv("MYSQL_PASS"),
                             db=os.getenv("DATABASE1"))
        # prepare a cursor object using cursor() method
        cursor = db.cursor()

        sql = "SELECT * FROM user_chat_id WHERE username = '" + str(username) + "';"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Fetch all the rows in a list of lists.
            result = cursor.fetchone()
        except Exception as e:
            print("Error: " + str(e))
        if result is None:
            # Add user's chat_id with Aqua to database
            sql = "INSERT INTO user_chat_id VALUES (" + str(chat_id) + ", '" + str(username) + "');"
            try:
                # Execute the SQL command
                cursor.execute(sql)
                # Commit your changes in the database
                db.commit()
                context.bot.send_message(chat_id=chat_id, text="Added! Now whenever you " + emojize(":star:", use_aliases=True) +
                                        " a photo, I'll forward it to you here! " + emojize(":smiley:", use_aliases=True))
            except Exception as e:
                # Rollback in case there is any error
                db.rollback()
                print("Adding user's chat_id failed. " + str(e))
                context.bot.send_message(chat_id=chat_id,
                                        text="Sorry, something went wrong. Please send the following message to @Avi0n.")
                context.bot.send_message(chat_id=chat_id, text=str(e))
            finally:
                cursor.close()
                db.close()
        else:
            context.bot.send_message(chat_id=chat_id, 
                                    text="You've already been added! " + emojize(":star:", use_aliases=True) + " away :)")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="That doesn't work in here. Send me a PM instead "
                                 + emojize(":wink:", use_aliases=True))


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
        type_found = False
        # Get media's file_id
        while type_found is False:
            try:
                media_id = update.message.reply_to_message.photo[1].file_id
                type_found = True
            except Exception as e:
                print("Not a photo")
            try:
                media_id = update.message.reply_to_message.document.file_id
                type_found = True
            except Exception as e:
                print("Not a document")
            try:
                media_id = update.message.reply_to_message.video.file_id
                type_found = True
            except Exception as e:
                print("Not a video")
            finally:
                break

        # Get the download link from Telegram
        file = context.bot.get_file(file_id=media_id)
        # Download the media (jpg, png, mp4)
        file.download(timeout=10)
        # If it's an mp4, convert it to gif
        for fname in os.listdir('.'):
            if fname.endswith('.mp4'):
                convert_media(fname, TargetFormat.GIF)
                os.remove(fname)
                break

        # Search for source from SauceNao
        # The following script is mostly a copy and paste from https://saucenao.com/tools/examples/api/identify_images_v1.py
        api_key = os.getenv("SAUCE_NAO_TOKEN")
        EnableRename = False
        minsim = '50!'

        extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
        thumbSize = (150, 150)

        """ 
        # enable or disable indexes
        index_hmags = '0'
        index_hanime = '0'
        index_hcg = '0'
        index_ddbobjects = '0'
        index_ddbsamples = '0'
        index_pixiv = '1'
        index_pixivhistorical = '1'
        index_anime = '1'
        index_seigaillust = '1'
        index_danbooru = '1'
        index_drawr = '1'
        index_nijie = '1'
        index_yandere = '1'

        # generate appropriate bitmask
        db_bitmask = int(index_yandere + index_nijie + index_drawr + index_danbooru + index_seigaillust + index_anime + \
            index_pixivhistorical + index_pixiv + index_ddbsamples + index_ddbobjects + index_hcg + index_hanime + index_hmags,2)
        """

        # encoded print - handle random crap
        def printe(line):
            # ignore or replace
            print(str(line).encode(sys.getdefaultencoding(), 'replace'))

        for root, _, files in os.walk(u'.', topdown=False):
            for f in files:
                fname = os.path.join(root, f)
                for ext in extensions:
                    if fname.lower().endswith(ext):
                        print(fname)
                        image = Image.open(fname)
                        image.thumbnail(thumbSize, Image.ANTIALIAS)
                        imageData = io.BytesIO()
                        image.save(imageData, format='PNG')

                        url = 'http://saucenao.com/search.php?output_type=2&testmode=1&numres=8&minsim=' + \
                            minsim + '&db=999' + '&api_key=' + api_key
                        files = {'file': ("photo.jpg", imageData.getvalue())}
                        imageData.close()

                        processResults = True
                        while processResults is True:
                            r = requests.post(url, files=files)
                            if r.status_code != 200:
                                if r.status_code == 403:
                                    print(
                                        'Incorrect or Invalid API Key! Please Edit Script to Configure...')
                                    sys.exit(1)
                                else:
                                    # generally non 200 statuses are due to either overloaded servers or the user is out of searches
                                    print("status code: " + str(r.status_code))
                                    time.sleep(10)
                            else:
                                results = json.JSONDecoder(
                                    object_pairs_hook=OrderedDict).decode(r.text)
                                if int(results['header']['user_id']) > 0:
                                    # api responded
                                    print(
                                        'Remaining Searches 30s|24h: ' + str(results['header']['short_remaining']) + '|' + str(
                                            results['header']['long_remaining']))
                                    if int(results['header']['status']) == 0:
                                        # search succeeded for all indexes, results usable
                                        break
                                    else:
                                        if int(results['header']['status']) > 0:
                                            # One or more indexes are having an issue.
                                            # This search is considered partially successful, even if all indexes failed,
                                            # so is still counted against your limit.
                                            print(
                                                'API Error. Retrying in 10 seconds...')
                                            time.sleep(10)
                                        else:
                                            # Problem with search as submitted, bad image, or impossible request.
                                            # Issue is unclear, so don't flood requests.
                                            print(
                                                'Bad image or other request error. Skipping in 10 seconds...')
                                            processResults = False
                                            context.bot.send_message(
                                                chat_id=update.message.chat_id, text="Something went wrong.")
                                            break
                                else:
                                    # General issue, api did not respond. Normal site took over for this error state.
                                    # Issue is unclear, so don't flood requests.
                                    print(
                                        'Bad image, or API failure. Skipping in 10 seconds...')
                                    processResults = False
                                    break

                        if processResults:
                            # print(results)

                            if int(results['header']['results_returned']) > 0:
                                # one or more results were returned
                                if float(results['results'][0]['header']['similarity']) > float(
                                        results['header']['minimum_similarity']):
                                    print(
                                        'hit! ' + str(results['results'][0]['header']['similarity']))

                                    pic_similarity = str(
                                        results['results'][0]['header']['similarity'])
                                    result_url = results['results'][0]['data']['ext_urls'][0]

                                    # Send result URL
                                    if float(results['results'][0]['header']['similarity']) < 70:
                                        context.bot.send_message(chat_id=update.message.chat_id,
                                                                 text="This _might_ be it: [Sauce](" + result_url + ")" +
                                                                 "\nSimilarity: " + pic_similarity,
                                                                 parse_mode='Markdown', disable_web_page_preview=True)
                                    else:
                                        context.bot.send_message(chat_id=update.message.chat_id,
                                                                 text="[Sauce](" + result_url + ")" +
                                                                 "\nSimilarity: " + pic_similarity,
                                                                 parse_mode='Markdown', disable_web_page_preview=True)

                                else:
                                    print('miss...')
                                    context.bot.send_message(chat_id=update.message.chat_id,
                                                     text="I couldn't find a source for that image")
                            else:
                                print('no results... ;_;')
                                context.bot.send_message(
                                    chat_id=update.message.chat_id, text="No results")

                            # could potentially be negative
                            if int(results['header']['long_remaining']) < 1:
                                print('Out of searches for today :(')
                                context.bot.send_message(chat_id=update.message.chat_id,
                                                         text="Out of searches for today :(")
                            if int(results['header']['short_remaining']) < 1:
                                print(
                                    'Out of searches for this 30 second period. Sleeping for 25 seconds...')
                                context.bot.send_message(chat_id=update.message.chat_id,
                                                         text="Out of searches for this 30 second period. Try again later.")

        print('Done with SauceNao search.')
    # If this else statement runs, the user is either not in an "authorized room", or they didn't reply to an image
    else:
        print("You're not authorized to use that command here.")
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="Did you forget to reply to an image?")

    # Cleanup downloaded media
    for fname in os.listdir('.'):
        if fname.endswith('.gif'):
            os.remove('source.gif')
        elif fname.endswith('.jpg'):
            os.remove(fname)


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
    fps = reader.get_meta_data()['fps']

    writer = imageio.get_writer(outputpath, fps=fps)
    for i, im in enumerate(reader):
        sys.stdout.write("\rframe {0}".format(i))
        sys.stdout.flush()
        writer.append_data(im)
    print("\r\nFinalizing conversion...")
    writer.close()
    print("Done converting.")


def make_keyboard(counter1, counter2, counter3):
    keyboard = [[InlineKeyboardButton(str(counter1) + ' ' + emojize(":thumbsup:", use_aliases=True), callback_data=1),
                 InlineKeyboardButton(
                     str(counter2) + ' ' + emojize(":ok_hand:", use_aliases=True), callback_data=2),
                 InlineKeyboardButton(
                     str(counter3) + ' ' + emojize(":heart:", use_aliases=True), callback_data=3),
                 InlineKeyboardButton(
                     emojize(":star:", use_aliases=True), callback_data=10),
                 InlineKeyboardButton('Votes', callback_data=11)]]

    return InlineKeyboardMarkup(keyboard)


# Forward message that was posted by another user to the channel with emoji buttons
def repost(update, context):
    # Check to see if user doesn't want their photo to be deleted
    if update.message.caption is not None:
        if 'aquano' in update.message.caption.replace(' ', '').lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return
        elif 'noaqua' in update.message.caption.replace(' ', '').lower():
            print("User doesn't want this photo to be reposted. Skipping.")
            return

    repost_caption = None
    keyboard_buttons = make_keyboard(0, 0, 0)

    # Give credit to who originally posted the photo/video
    if update.message.caption is not None:
        repost_caption = update.message.caption + \
            '\n\nPosted by: ' + update.message.from_user.username
    else:
        repost_caption = '\n\nPosted by: ' + update.message.from_user.username

    send_error = True
    while send_error is True:
        # Try sending photo
        try:
            # Send message with inline keyboard
            context.bot.send_photo(chat_id=update.message.chat.id, photo=update.message.photo[-1].file_id, caption=repost_caption,
                                   disable_notification=False, reply_markup=keyboard_buttons, timeout=20, parse_mode='HTML')
        except:
            print('Not a photo')
        else:
            # Delete original message
            context.bot.delete_message(
                chat_id=update.message.chat.id, message_id=update.message.message_id)
            send_error = False
        # Try sending document animation
        try:
            # Send message with inline keyboard
            context.bot.send_animation(chat_id=update.message.chat.id, animation=update.message.document.file_id, caption=repost_caption,
                                       disable_notification=False, reply_markup=keyboard_buttons, timeout=20, parse_mode='HTML')
        except:
            print('Not a document video')
        else:
            # Delete original message
            context.bot.delete_message(
                chat_id=update.message.chat.id, message_id=update.message.message_id)
            send_error = False
        # Try sending video animation
        try:
            # Send message with inline keyboard
            context.bot.send_video(chat_id=update.message.chat.id, video=update.message.video.file_id, caption=repost_caption,
                                   disable_notification=False, reply_markup=keyboard_buttons, timeout=20, parse_mode='HTML')
        except:
            print('Not a video video')
        else:
            # Delete original message
            context.bot.delete_message(
                chat_id=update.message.chat.id, message_id=update.message.message_id)
            send_error = False

        # Set send_error to False so we don't stay in the loop forever
        send_error = False


def button(update, context):
    query = update.callback_query
    database = ''
    counter1 = query.message.reply_markup.inline_keyboard[0][0].text
    counter2 = query.message.reply_markup.inline_keyboard[0][1].text
    counter3 = query.message.reply_markup.inline_keyboard[0][2].text
    # Find original poster
    username = query.message.caption.split()

    # Remove emoji from counter1
    counter1 = int(''.join(i for i in counter1 if i.isdigit()))

    # Remove emoji from counter2
    counter2 = int(''.join(i for i in counter2 if i.isdigit()))

    # Remove emoji from counter3
    counter3 = int(''.join(i for i in counter3 if i.isdigit()))

    # Find room name and assign correct database
    if query.message.chat.title == os.getenv("GROUP1"):
        database = os.getenv("DATABASE1")
    elif query.message.chat.title == os.getenv("GROUP2"):
        database = os.getenv("DATABASE2")
    elif query.message.chat.title == os.getenv("GROUP3"):
        database = os.getenv("DATABASE3")

    if int(query.data) == 10 or int(query.data) == 11:
        # Show popup showing who voted on the picture/video
        if int(query.data) == 11:
            context.bot.answer_callback_query(
                callback_query_id=query.id, text=get_message_karma(database, query.message.message_id), show_alert=True, timeout=None)
        # Forward message that user star'd
        elif int(query.data) == 10:
            try:
                # Get user's personal chat_id with Aqua
                tele_chat_id = get_chat_id(query.from_user.username)
                # Send message
                context.bot.forward_message(chat_id=tele_chat_id, from_chat_id=query.message.chat_id,
                                            message_id=query.message.message_id)
                context.bot.answer_callback_query(
                    callback_query_id=query.id, text='Saved!', show_alert=False, timeout=None)
            except:
                context.bot.answer_callback_query(
                    callback_query_id=query.id, text="Error. Have you PM'd me the '/addme' command?", show_alert=True, timeout=None)
    else:
        self_vote = False
        # Prevent users from voting on their own posts
        if query.from_user.username == username[-1]:
            context.bot.send_message(chat_id=query.message.chat_id,
                                    text=query.from_user.username + " just tried to give themselves points.")
            context.bot.send_sticker(
                chat_id=query.message.chat_id, sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            self_vote = True
        # Update with the appropriate amount of karma
        elif int(query.data) == 1:
            update_user_karma(database, username[-1], "+", query.data)
            update_message_karma(database, query.message.message_id, query.from_user.username, query.data)
            counter1 += 1
            context.bot.answer_callback_query(callback_query_id=query.id, text='You ' + emojize(
                ":thumbsup:", use_aliases=True) + ' this.', show_alert=False, timeout=None)
        elif int(query.data) == 2:
            update_user_karma(database, username[-1], "+", query.data)
            update_message_karma(database, query.message.message_id, query.from_user.username, query.data)
            counter2 += 1
            context.bot.answer_callback_query(callback_query_id=query.id, text='You ' + emojize(
                ":ok_hand:", use_aliases=True) + ' this.', show_alert=False, timeout=None)
        elif int(query.data) == 3:
            update_user_karma(database, username[-1], "+", query.data)
            update_message_karma(database, query.message.message_id, query.from_user.username, query.data)
            counter3 += 1
            context.bot.answer_callback_query(callback_query_id=query.id, text='You ' + emojize(
                ":heart:", use_aliases=True) + ' this.', show_alert=False, timeout=None)
        if self_vote is False:
            keyboard_buttons = make_keyboard(counter1, counter2, counter3)
            query.edit_message_reply_markup(reply_markup=keyboard_buttons)


def main():
    # Create the Updater and pass it Aqua Bot's token.
    updater = Updater(os.getenv("TEL_BOT_TOKEN"), use_context=True)

    start_handler = CommandHandler('start', start)
    updater.dispatcher.add_handler(start_handler)

    delete_handler = CommandHandler('delete', delete)
    updater.dispatcher.add_handler(delete_handler)

    sauce_handler = CommandHandler('sauce', sauce)
    updater.dispatcher.add_handler(sauce_handler)

    source_handler = CommandHandler('source', source)
    updater.dispatcher.add_handler(source_handler)

    karma_handler = CommandHandler('karma', karma)
    updater.dispatcher.add_handler(karma_handler)

    addme_handler = CommandHandler('addme', addme)
    updater.dispatcher.add_handler(addme_handler)

    give_handler = CommandHandler('give', give)
    updater.dispatcher.add_handler(give_handler)

    # on noncommand i.e message - repost the photo on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.photo, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - repost the video on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.animation, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - repost the video on Telegram
    updater.dispatcher.add_handler(MessageHandler(Filters.video, repost))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
