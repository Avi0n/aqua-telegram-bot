import os
import logging
import MySQLdb
from dotenv import load_dotenv
from emoji import emojize
from telegram.ext import (MessageHandler, CommandHandler, BaseFilter, Updater)
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


# Initialize dotenv
load_dotenv()

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def read_db():
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=os.getenv("DATABASE"))
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
        return_message += "Error"
        print("read_db() error: " + str(e))
    finally:
        cursor.close()
        db.close()
    return return_message


def update_karma(username, plus_or_minus, points):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=os.getenv("DATABASE"))
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Prepare SQL query to UPDATE required records
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


# Respond to /start
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Send /karma to see everyone's points.\nSend /addme to let me forward" +
                     " photos that you " + emojize(":star:", use_aliases=True) + " to you!")


# Respond to /karma
def karma(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=read_db(), parse_mode='Markdown', timeout=20)


# Respond to /source
def source(bot, update):
    authorized_room = False

    try:
        username = update.message.reply_to_message.from_user.username
    except Exception as e:
        print(str(e))
        username = None

    if update.message.chat.title == "Bot testing" or update.message.chat.title == "Debauchery Tea Party":
        authorized_room = True

    if authorized_room is True and username is not None:
        # Get media's file_id
        while True:
            try:
                media_id = update.message.reply_to_message.photo[2].file_id
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

        # Get the download link from Telegram
        file = bot.get_file(file_id=media_id)
        # Download the media (jpg, png, mp4)
        file.download(custom_path="source.jpg",timeout=10)
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
                                            bot.send_message(
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
                                        bot.send_message(chat_id=update.message.chat_id,
                                                         text="This _might_ be it: [Sauce](" + result_url + ")" +
                                                         "\nSimilarity: " + pic_similarity,
                                                         parse_mode='Markdown', disable_web_page_preview=True)
                                    else:
                                        bot.send_message(chat_id=update.message.chat_id,
                                                         text="[Sauce](" + result_url + ")" +
                                                         "\nSimilarity: " + pic_similarity,
                                                         parse_mode='Markdown', disable_web_page_preview=True)

                                else:
                                    print('miss... ' + pic_similarity)
                                    bot.send_message(chat_id=update.message.chat_id,
                                                     text="I couldn't find anything.\n" +
                                                     "Similarity: " + pic_similarity)

                            else:
                                print('no results... ;_;')
                                bot.send_message(
                                    chat_id=update.message.chat_id, text="No results")

                            # could potentially be negative
                            if int(results['header']['long_remaining']) < 1:
                                print('Out of searches for today :(')
                                bot.send_message(chat_id=update.message.chat_id,
                                                 text="Out of searches for today :(")
                            if int(results['header']['short_remaining']) < 1:
                                print(
                                    'Out of searches for this 30 second period. Sleeping for 25 seconds...')
                                bot.send_message(chat_id=update.message.chat_id,
                                                 text="Out of searches for this 30 second period. Try again later.")

        print('Done with SauceNao search.')
    # If this else statement runs, the user is either not in an "authorized room", or they didn't reply to an image
    else:
        print("You're not authorized to use that command here.")
        bot.send_message(chat_id=update.message.chat_id,
                         text="Did you forget to reply to an image?")

    # Cleanup downloaded media
    for fname in os.listdir('.'):
        if fname.endswith('.gif'):
            os.remove('source.gif')
        elif fname.endswith('.jpg'):
            os.remove('source.jpg')


# Respond to /addme
def addme(bot, update):
    if not update.message.chat.title:
        username = update.message.from_user.username
        chat_id = update.message.chat_id
        # Set MySQL settings
        db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                             user=os.getenv("MYSQL_USER"),
                             passwd=os.getenv("MYSQL_PASS"),
                             db=os.getenv("DATABASE"))
        # prepare a cursor object using cursor() method
        cursor = db.cursor()

        # Add user's chat_id with Aqua to database if it doesn't already exist
        sql = "UPDATE user_chat_id SET chat_id = " + \
            str(chat_id) + " WHERE username = '" + str(username) + "';"
        try:
            # Execute the SQL command
            cursor.execute(sql)
            # Commit your changes in the database
            db.commit()
            bot.send_message(chat_id=chat_id, text="Added! Now whenever you " + emojize(":star:", use_aliases=True) +
                                                   " a photo in DTP, I'll forward it to you here! " +
                                                   emojize(":smiley:", use_aliases=True))
        except Exception as e:
            # Rollback in case there is any error
            db.rollback()
            print("Adding user's chat_id failed")
            bot.send_message(chat_id=chat_id, text="Sorry, something went wrong. Please send the following message to " +
                                                   "@Avi0n.")
            bot.send_message(chat_id=chat_id, text=str(e))
        finally:
            cursor.close()
            db.close()
    else:
        bot.send_message(chat_id=update.message.chat_id, text="That doesn't work in here. Send me a PM instead "
                         + emojize(":wink:", use_aliases=True))


# Get user's personal chat_id with Aqua
def get_chat_id(tele_user):
    # Set MySQL settings
    db = MySQLdb.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USER"),
                         passwd=os.getenv("MYSQL_PASS"),
                         db=os.getenv("DATABASE"))
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
        print("forward_photo() error: " + str(e))
    finally:
        cursor.close()
        db.close()


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


# Recognize who's picture was liked and store point in database
def process_emoji(bot, update):
    try:
        username = update.message.reply_to_message.from_user.username
    except Exception as e:
        print(str(e))
        username = None

    # Assign emoji in message or sticker to a variable
    message_emoji = ""

    if not update.message.text is None:
        message_emoji = update.message.text
        print(message_emoji)

    elif not update.message.sticker.emoji is None:
        message_emoji = update.message.sticker.emoji
        print(message_emoji)

    if update.message.chat.title == "Bot testing" or update.message.chat.title == "Debauchery Tea Party":
        # If message contains :heart:, add 3 points and forward the message to whoever liked it
        if emojize(":heart:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "3")

        # If message contains :ok_hand:, add 2 points
        elif emojize(":ok_hand:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "2")

        # If message contains :thumbsup:, add 1 point
        elif emojize(":thumbsup:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "1")

        # If message contains :thumbsdown:, subtract 1 point
        elif emojize(":thumbsdown:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to take away points from themselves.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "-", "1")

        # If message contains :star:, forward message that the user replied to with :star:
        if emojize(":star:", use_aliases=True) in message_emoji and username is not None:
            # Get user's personal chat_id with Aqua
            tele_chat_id = get_chat_id(update.message.from_user.username)
            # Send message
            bot.forward_message(chat_id=tele_chat_id, from_chat_id=update.message.chat_id,
                                message_id=update.message.reply_to_message.message_id)
            bot.send_message(chat_id=update.message.chat_id,
                             text=update.message.reply_to_message)

        # If message contains :no_entry_sign: or :underage:, send lolice gif
        if emojize(":no_entry_sign:", use_aliases=True) in message_emoji and username is not None or \
                emojize(":underage:", use_aliases=True) in message_emoji and username is not None or \
                emojize(":police_car:", use_aliases=True) in message_emoji and username is not None or \
                emojize(":oncoming_police_car:", use_aliases=True) in message_emoji and username is not None or \
                emojize(":rotating_light:", use_aliases=True) in message_emoji and username is not None:
            bot.send_animation(chat_id=update.message.chat_id,
                               animation="CgADAQADhAADY7TZR2yn8RNCCai9Ag")
            bot.send_message(chat_id=update.message.chat_id,
                             text="MODS!! MODS!!!! LOLI LEWDING REPORTED!!!")

        # If message contains :sweat_drops:, send Aqua Nature Beauty party trick gif
        if emojize(":sweat_drops:", use_aliases=True) in message_emoji:
            bot.send_animation(chat_id=update.message.chat_id,
                               animation="CgADAQADSwADac6YRfOLXW5UD4qJAg")

        # If message contains :crocodile: or :shower:, send Aqua purification gif
        if emojize(":crocodile:", use_aliases=True) in message_emoji or \
                emojize(":shower:", use_aliases=True) in message_emoji:
            bot.send_animation(chat_id=update.message.chat_id,
                               animation="CgADAQADewADMXsJRAYOmfxivPi3Ag")


# Look for certain emojis to reply to
class FilterEmoji(BaseFilter):
    def filter(self, message):
        accepted_emojis = [
            ":thumbsup:",
            ":ok_hand:",
            ":heart:",
            ":thumbsdown:",
            ":star:",
            ":no_entry_sign:",
            ":underage:",
            ":police_car:",
            ":oncoming_police_car:",
            ":rotating_light:",
            ":sweat_drops:",
            ":crocodile:",
            ":shower:"
        ]
        message_emoji = ""
        emoji_found = False

        if not message.text is None:
            message_emoji = message.text
            print(message_emoji)
            emoji_found = True
            print("emoji in message.text = " + str(emoji_found))

        elif not message.sticker.emoji is None:
            message_emoji = message.sticker.emoji
            print(message_emoji)
            emoji_found = True
            print("emoji in message.sticker.emoji = " + str(emoji_found))

        if emoji_found is True:
            for x in accepted_emojis:
                if emojize(x, use_aliases=True) in message_emoji:
                    print("Yep, that's an emoji in the message")
                    return True
        else:
            print("That ain't an emoji chief.")
            return False


def main():
    """Start the bot"""
    # Initialize emoji filter class
    filter_emoji = FilterEmoji()

    # Set Aqua bot token
    updater = Updater(token=os.getenv("TEL_BOT_TOKEN"), request_kwargs={
                      'read_timeout': 15, 'connect_timeout': 30})

    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    source_handler = CommandHandler('source', source)
    dispatcher.add_handler(source_handler)

    karma_handler = CommandHandler('karma', karma)
    dispatcher.add_handler(karma_handler)

    addme_handler = CommandHandler('addme', addme)
    dispatcher.add_handler(addme_handler)

    # If an emoji in the list above is found, run process_emoji()
    emoji_handler = MessageHandler(filter_emoji, process_emoji)
    dispatcher.add_handler(emoji_handler)

    dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
