import logging
import MySQLdb
from dotenv import load_dotenv
from emoji import emojize
from telegram.ext import (MessageHandler, CommandHandler, BaseFilter, Updater)

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.DEBUG)

logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def insert_new_user(username):
    # Set MySQL settings
    db = MySQLdb.connect(host="MYSQL_HOST",
                         user="MYSQL_USER",
                         passwd="MYSQL_PASS",
                         db="DATABASE")
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Prepare SQL query to INSERT a record into the database.
    sql = "INSERT INTO user_karma VALUES ('" + username + "',0);"
    try:
       # Execute the SQL command
       cursor.execute(sql)
       # Commit your changes in the database
       db.commit()
    except:
       # Rollback in case there is any error
       db.rollback()
       print("insert_new_user failed")


def read_db():
    # Set MySQL settings
    db = MySQLdb.connect(host="MYSQL_HOST",
                         user="MYSQL_USER",
                         passwd="MYSQL_PASS",
                         db="DATABASE")
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    return_message = ""
    sql = "SELECT * FROM user_karma WHERE karma <> 0;"
    try:
       # Execute the SQL command
       cursor.execute(sql)
       # Fetch all the rows in a list of lists.
       results = cursor.fetchall()
       for row in results:
          username = row[0]
          karma = row[1]
          # Now print fetched result
          print(username, karma)
          return_message += username + " " + str(karma) + "\n"
    except:
       return_message += "Error"
       print("Error: unable to fetch data")
    finally:
        cursor.close()
        db.close()
    print(return_message)
    return return_message


def update_karma(username, plus_or_minus, points):
    # Set MySQL settings
    db = MySQLdb.connect(host="MYSQL_HOST",
                         user="MYSQL_USER",
                         passwd="MYSQL_PASS",
                         db="DATABASE")
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Prepare SQL query to UPDATE required records
    sql = "UPDATE user_karma SET karma = karma" + plus_or_minus + points + " WHERE username = '" + username + "';"
    try:
       # Execute the SQL command
       cursor.execute(sql)
       # Commit your changes in the database
       db.commit()
    except:
       # Rollback in case there is any error
       db.rollback()
       print("update_karma failed")
    finally:
        cursor.close()
        db.close()


# Respond to /start
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You can send '/karma' to see everyone's points")


# Respond to /karma
def karma(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=read_db(), timeout=20)


# Recognize who's picture was liked and store point in database
def process_emoji(bot, update):
    try:
        username = update.message.reply_to_message.from_user.username
    except:
        print("This is not a reply")
        username = None
    if update.message.chat.title == "Debauchery Tea Party" or update.message.chat.title == "Bot testing":
        # If :thumbsup:, add 1 point
        if emojize(":thumbsup:", use_aliases=True) in update.message.text and username is not None:
            update_karma(username, "+", "1")
            print("from_user.username: " + username)
        # If :ok_hand:, add 2 points
        if emojize(":ok_hand:", use_aliases=True) in update.message.text and username is not None:
            update_karma(username, "+", "2")
            print("from_user.username: " + username)
        # If :heart:, add 3 points
        if emojize(":heart:", use_aliases=True) in update.message.text and username is not None:
            update_karma(username, "+", "3")
        # If :thumbsdown:, subtract 1 point
        if emojize(":thumbsdown:", use_aliases=True) in update.message.text and username is not None:
            update_karma(username, "-", "1")
            print("from_user.username: " + username)
        # If :no_entry_sign: or :underage:, send lolice gif
        if emojize(":no_entry_sign:", use_aliases=True) in update.message.text and username is not None or \
                emojize(":underage:", use_aliases=True) in update.message.text and username is not None or \
                emojize(":police_car:", use_aliases=True) in update.message.text and username is not None or \
                emojize(":oncoming_police_car:", use_aliases=True) in update.message.text and username is not None or \
                emojize(":rotating_light:", use_aliases=True) in update.message.text and username is not None:
            bot.send_animation(chat_id=update.message.chat_id, animation="CgADAQADhAADY7TZRxavzR5I5uLCAg")
            bot.send_message(chat_id=update.message.chat_id, text="MODS!! MODS!!!! LOLI LEWDING REPORTED!!!")
        # If :sweat_drops:, send Aqua Nature Beauty party trick gif
        if emojize(":sweat_drops:", use_aliases=True) in update.message.text and username is not None:
            bot.send_animation(chat_id=update.message.chat_id, animation="CgADAQADSwADac6YRRnvmf0EWKsDAg")
        # If :crocodile: or :shower:, send Aqua purification gif
        if emojize(":crocodile:", use_aliases=True) in update.message.text and username is not None or \
                emojize(":shower:", use_aliases=True) in update.message.text and username is not None:
            bot.send_animation(chat_id=update.message.chat_id, animation="CgADAQADewADMXsJRLbQLkfBMmOsAg")

# Look for certain emojis to reply to
class FilterEmoji(BaseFilter):
    def filter(self, message):
        return emojize(":thumbsup:", use_aliases=True) in message.text or \
               emojize(":heart:", use_aliases=True) in message.text or \
               emojize(":ok_hand:", use_aliases=True) in message.text or \
               emojize(":thumbsdown:", use_aliases=True) in message.text or \
               emojize(":no_entry_sign:", use_aliases=True) in message.text or \
               emojize(":underage:", use_aliases=True) in message.text or \
               emojize(":police_car:", use_aliases=True) in message.text or \
               emojize(":oncoming_police_car:", use_aliases=True) in message.text or \
               emojize(":rotating_light:", use_aliases=True) in message.text or \
               emojize(":sweat_drops:", use_aliases=True) in message.text or \
               emojize(":crocodile:", use_aliases=True) in message.text or \
               emojize(":shower:", use_aliases=True) in message.text


# Remember to initialize the class
filter_emoji = FilterEmoji()


def main():
    """Start the bot"""
    # Set Aqua bot token
    updater = Updater(token='TEL_BOT_TOKEN', request_kwargs={'read_timeout': 15, 'connect_timeout': 30})

    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    karma_handler = CommandHandler('karma', karma)
    dispatcher.add_handler(karma_handler)

    # If an emoji in the list above is found, run process_emoji()
    emoji_handler = MessageHandler(filter_emoji, process_emoji)
    dispatcher.add_handler(emoji_handler)

    dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
