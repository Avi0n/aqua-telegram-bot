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

import os
from emoji import emojize
import aiomysql


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


# Store hash of message_id's media in database
async def store_hash(database, message_id, media_hash, loop):
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
            sql = "SELECT message_id, hash, COUNT(hash) FROM media_hash WHERE LEFT(hash, 4) = \
                   (SELECT LEFT(hash, 4) FROM media_hash WHERE message_id = " + str(message_id) + ") \
                   ORDER BY message_id ASC"
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
