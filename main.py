import os
import logging
import MySQLdb
from dotenv import load_dotenv
from emoji import emojize
from telegram.ext import (MessageHandler, CommandHandler, BaseFilter, Updater)

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
                     text="You can send '/karma' to see everyone's points")


# Respond to /karma
def karma(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=read_db(), parse_mode='Markdown', timeout=20)


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
            bot.send_message(chat_id=chat_id, text="Added! Now whenever you " + emojize(":heart:", use_aliases=True) +
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


# Recognize who's picture was liked and store point in database
def process_emoji(bot, update):
    try:
        username = update.message.reply_to_message.from_user.username
    except Exception as e:
        print(str(e))
        username = None

    # Assign emoji in message or sticker to a variable
    message_emoji = ""
    emoji_found = False

    if not update.message.text is None:
        message_emoji = update.message.text
        print(message_emoji)
        emoji_found = True
        print("emoji in update.message.text = " + str(emoji_found))

    elif not update.message.sticker.emoji is None:
        message_emoji = update.message.sticker.emoji
        print(message_emoji)
        emoji_found = True
        print("emoji in update.message.sticker.emoji = " + str(emoji_found))

    if update.message.chat.title == "Bot testing" or update.message.chat.title == "Debauchery Tea Party":
        # If message contains :thumbsup:, add 1 point
        if emojize(":thumbsup:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "1")

        # If message contains :ok_hand:, add 2 points
        if emojize(":ok_hand:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "2")

        # If message contains :heart:, add 3 points and forward the message to whoever liked it
        if emojize(":heart:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to give themselves points.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "+", "3")

        # If message contains :star:, forward message that the user replied to with :star:
        if emojize(":star:", use_aliases=True) in message_emoji and username is not None:
            # Get user's personal chat_id with Aqua
            tele_chat_id = get_chat_id(update.message.from_user.username)
            # Send message
            bot.forward_message(chat_id=tele_chat_id, from_chat_id=update.message.chat_id,
                                message_id=update.message.reply_to_message.message_id)
            bot.send_message(chat_id=update.message.chat_id,
                             text=update.message.reply_to_message)

        # If message contains :thumbsdown:, subtract 1 point
        if emojize(":thumbsdown:", use_aliases=True) in message_emoji and username is not None:
            if update.message.from_user.username == username:
                bot.send_message(chat_id=update.message.chat_id, text=update.message.from_user.username +
                                 " just tried to take away points from themselves.")
                bot.send_sticker(chat_id=update.message.chat_id,
                                 sticker="CAADAQADbAEAA_AaA8xi9ymr2H-ZAg")
            else:
                update_karma(username, "-", "1")

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
            ":heart:",
            ":ok_hand:",
            ":thumbsdown:",
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
