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
import sqlite3

import aiosqlite
from emoji import emojize


# Check for first run
def check_first_db_run():
    first_run = False

    try:
        db = sqlite3.connect("db/user_chat_ids.db")
        sql = "SELECT * FROM user_karma;"
        cursor = db.cursor()

        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchall()

        cursor.close()
        db.close()
    except Exception as e:
        if "no such table" in str(e):
            print("This is the first run. Populating initial database.")
            # Populate db with initial tables
            db = sqlite3.connect("db/user_chat_ids.db")
            cursor = db.cursor()

            # Create table
            sql = '''
                    CREATE TABLE user_chat_ids (
                    chat_id int(50) DEFAULT NULL,
                    username varchar(255) DEFAULT NULL
                    )'''
            try:
                # Execute the SQL command
                cursor.execute(sql)
            except Exception as ex:
                print("Error in check_first_db_run while creating the table" +
                      " user_chat_ids: " + str(ex))
            cursor.close()
            db.close()

            # Create 2nd initial table
            db = sqlite3.connect("db/group_members.db")
            cursor = db.cursor()
            sql = '''
                    CREATE TABLE group_members (
                    user_id int(11) DEFAULT NULL
                    )'''
            try:
                # Execute the SQL command
                cursor.execute(sql)
            except Exception as ex:
                print("Error in check_first_db_run while creating the table" +
                      " group_members: " + str(ex))
            cursor.close()
            db.close()

            print("Done populating the database, starting the bot.")
        else:
            print("Error: " + str(e) + "\n"
                  "There was an error populating the database.")
    return


def populate_db(database, loop):
    print("Entered populate_db")
    populated_status = False

    try:
        db = sqlite3.connect("db/" + database + ".db")
        sql = "SELECT * FROM user_karma;"
        cursor = db.cursor()

        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = cursor.fetchall()

        cursor.close()
        db.close()

        populated_status = True
    except:
        db = sqlite3.connect("db/" + database + ".db")
        cursor = db.cursor()

        # Create tables
        sql = '''
                CREATE TABLE media_hash(
                    message_id int(11) NOT NULL,
                    hash varchar(255) NOT NULL,
                    date date NOT NULL
                )'''
        try:
            # Execute the SQL command
            cursor.execute(sql)
        except Exception as e:
            print("Error in check_first_db_run: " + str(e))
            first_run = True

        sql = '''
                CREATE TABLE message_karma (
                    message_id int(11) NOT NULL,
                    username varchar(20) DEFAULT NULL,
                    thumbsup int(4) NOT NULL,
                    ok_hand int(4) NOT NULL,
                    heart int(4) NOT NULL
                )'''
        try:
            # Execute the SQL command
            cursor.execute(sql)
        except Exception as e:
            print("Error in populate_db while creating the table" +
                  "message_karma: " + str(e))

        sql = '''
                CREATE TABLE user_karma (
                    username varchar(255) NOT NULL,
                    karma int(11) DEFAULT NULL
                )'''
        try:
            # Execute the SQL command
            cursor.execute(sql)
        except Exception as e:
            print("Error in populate_db while creating the table" +
                  " user_karma: " + str(e))
        cursor.close()
        db.close()

        # Add group's chat_id to the group_members table
        db = sqlite3.connect("db/group_members.db")
        cursor = db.cursor()
        sql = f"ALTER TABLE group_members ADD COLUMN '{database}' VARCHAR(50)"
        try:
            # Execute the SQL command
            cursor.execute(sql)
        except Exception as e:
            print("Error in populate_db while altering the table" +
                  " group_members: " + str(e))
        cursor.close()
        db.close()

    # Return True if db already existed
    return populated_status


# Retrieve user's karma from the database
async def get_user_karma(database, loop):
    db = await aiosqlite.connect(f"db/{database}.db")
    sql = "SELECT * FROM user_karma WHERE karma <> 0 ORDER BY username;"
    cursor = await db.cursor()
    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = await cursor.fetchall()

        return_message = "```\n"

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
            return_message += username + (
                " " * (longest_username_length - len(username))) + "   " + (
                    " " * (longest_karma_length -
                           len(str(karma_points)))) + str(karma_points) + "\n"

        return_message += "\n```" + emojize(":v:", use_aliases=True)

    except Exception as e:
        return_message += "Error: " + str(e)
        print("get_user_karma() error: " + str(e))
    finally:
        await cursor.close()
    await db.close()
    return return_message


# Increment the total karma for a specific user
async def update_user_karma(database, username, plus_or_minus, points, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    sql = "SELECT * FROM user_karma WHERE username = '" + username + "';"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        result = await cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    if result is None:
        # Add username to the database along with
        # the points that were just added
        sql = "INSERT INTO user_karma VALUES ('" + username + "', " \
              + points + ");"
        try:
            # Execute the SQL command
            await cursor.execute(sql)
            # Commit your changes in the database
            await db.commit()
        except Exception as e:
            # Rollback in case there is any error
            await db.rollback()
            print("update_user_karma error: " + str(e))
        finally:
            await cursor.close()
    else:
        sql = "UPDATE user_karma SET karma = karma" + plus_or_minus + points \
              + " WHERE username = '" + username + "';"
        try:
            # Execute the SQL command
            await cursor.execute(sql)
            # Commit your changes in the database
            await db.commit()
        except Exception as e:
            # Rollback in case there is any error
            await db.rollback()
            print("update_user_karma error: " + str(e))
        finally:
            await cursor.close()
    await db.close()


# Update a message_id's points
async def update_message_karma(database, message_id, username, query_data,
                               loop):
    user_voted = False

    thumb_points = 0
    ok_points = 0
    heart_points = 0
    # Figure out which column to update
    if int(query_data) == 1:
        emoji_symbol = "thumbsup"
        thumb_points = 1
    elif int(query_data) == 2:
        emoji_symbol = "ok_hand"
        ok_points = 1
    elif int(query_data) == 3:
        emoji_symbol = "heart"
        heart_points = 1

    db = await aiosqlite.connect("db/" + database + ".db")
    sql = "SELECT * FROM message_karma WHERE message_id = " + \
          str(message_id) + " AND username = '" + username + "';"
    cursor = await db.cursor()
    # Check if this message_id exists in the db already
    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        result = await cursor.fetchone()
    except Exception as e:
        print("Error: " + str(e))
    if result is None:
        # Insert new row with message_id, username, and emoji point values
        sql = "INSERT INTO message_karma VALUES (" + str(message_id) + ", '" \
              + username + "', " + str(thumb_points) + ", " + str(ok_points) \
              + ", " + str(heart_points) + ");"
        try:
            # Execute the SQL command
            await cursor.execute(sql)
            # Commit your changes in the database
            await db.commit()
        except Exception as e:
            # Rollback in case there is any error
            await db.rollback()
            print("update_message_karma insert error: " + str(e))
        finally:
            await cursor.close()
    else:
        # If user has already voted, check to see if this specific emoji has
        # already been pressed
        if int(query_data) == 1:
            if int(result[2]) != 0:
                # Change specified emoji field to 0 since user is
                # taking back reaction
                sql = "UPDATE message_karma SET thumbsup = 0" \
                    + " WHERE message_id = " + str(message_id) \
                    + " AND username = '" + username + "';"
                user_voted = True
        elif int(query_data) == 2:
            if int(result[3]) != 0:
                # Change specified emoji field to 0 since user is
                # taking back reaction
                sql = "UPDATE message_karma SET ok_hand = 0" \
                    + " WHERE message_id = " + str(message_id) \
                    + " AND username = '" + username + "';"
                user_voted = True
        elif int(query_data) == 3:
            if int(result[4]) != 0:
                # Change specified emoji field to 0 since user is
                # taking back reaction
                sql = "UPDATE message_karma SET heart = 0" \
                    + " WHERE message_id = " + str(message_id) \
                    + " AND username = '" + username + "';"
                user_voted = True
        # If user hasn't already pressed the emoji, add point to db
        if user_voted is False:
            # Update emoji points that user has given a specific message_id
            sql = "UPDATE message_karma SET " + emoji_symbol + " = " \
                + emoji_symbol + " + 1" \
                + " WHERE message_id = " + str(message_id) \
                + " AND username = '" + username + "';"
        try:
            # Execute the SQL command
            await cursor.execute(sql)
            # Commit your changes in the database
            await db.commit()
        except Exception as e:
            # Rollback in case there is any error
            await db.rollback()
            print("update_message_karma error: " + str(e))
        finally:
            await cursor.close()
    await db.close()

    # Return true if user has pressed this emoji already
    # Return false if user has not pressed this emoji already
    return user_voted


# Delete message_id row from database
async def delete_row(database, message_id, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    # Fetch number of points that need to be deleted
    sql = "SELECT SUM(thumbsup + ok_hand + heart) FROM message_karma " \
          + "WHERE message_id = " + str(message_id) + ";"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        points_to_delete = await cursor.fetchone()
    except Exception as e:
        print("Error in delete_row: " + str(e))
    # Delete row that matches message_id
    sql = f"DELETE from message_karma WHERE message_id = {str(message_id)};"
    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Commit your changes in the database
        await db.commit()
    except Exception as e:
        # Rollback in case there is any error
        await db.rollback()
        print("Error in delete_row: " + str(e))
    finally:
        await cursor.close()
    await db.close()
    return points_to_delete


# Check total karma for specific emoji for a specific message
async def check_emoji_points(database, message_id, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    sql = "SELECT SUM(thumbsup), SUM(ok_hand), SUM(heart) FROM message_karma" \
          + " WHERE message_id = " + str(message_id) + ";"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        result = await cursor.fetchone()
    except Exception as e:
        print("Error in check_emoji_points: " + str(e))
    finally:
        await cursor.close()
    await db.close()
    return result


# Get total karma per user for a specific message
async def get_message_karma(database, message_id, loop):
    return_message = "Votes\n\n"

    db = await aiosqlite.connect("db/" + database + ".db")
    # Multiply ok_hand by 2 and heart by 3 to get correct sum of votes
    sql = "SELECT username, SUM(thumbsup + ok_hand*2 + heart*3) AS karma " \
          + "FROM message_karma WHERE message_id = " + str(message_id) \
          + " GROUP BY username ORDER BY username;"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = await cursor.fetchall()

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
            return_message += username + (
                " " * (longest_username_length - len(username))) + "   " + (
                    " " * (longest_karma_length -
                           len(str(karma_points)))) + str(karma_points) + "\n"
    except Exception as e:
        return_message += "Error"
        print("Error in get_message_karma: " + str(e))
    finally:
        await cursor.close()
    await db.close()
    return return_message


# Get user's personal chat_id with Aqua
async def get_chat_id(tele_user, loop):
    db = await aiosqlite.connect("db/user_chat_ids.db")
    sql = "SELECT chat_id FROM user_chat_ids WHERE username = '" + str(
        tele_user) + "';"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        result = await cursor.fetchone()
    except Exception as e:
        print("Error in get_chat_id: " + str(e))
    finally:
        await cursor.close()
    await db.close()
    return result[0]


async def addme_async(chat_type, username, chat_id, loop):
    # Make sure the /addme command is being sent in a PM
    if chat_type == "private":
        db = await aiosqlite.connect("db/user_chat_ids.db")
        sql = "SELECT * FROM user_chat_ids WHERE username = '" + str(
            username) + "';"
        cursor = await db.cursor()

        try:
            # Execute the SQL command
            await cursor.execute(sql)
            # Fetch one row
            result = await cursor.fetchone()
        except Exception as e:
            print("Error: " + str(e))
        if result is None:
            # Add user's chat_id with Aqua to database
            sql = "INSERT INTO user_chat_ids VALUES (" + str(
                chat_id) + ", '" + str(username) + "');"
            try:
                # Execute the SQL command
                await cursor.execute(sql)
                # Commit your changes in the database
                await db.commit()
                message = "Added! Now whenever you " \
                          + emojize(":star:", use_aliases=True) \
                          + " a photo, I'll forward it to you here! " \
                          + emojize(":smiley:", use_aliases=True)
            except Exception as e:
                # Rollback in case there is any error
                await db.rollback()
                print("Adding user's chat_id failed. " + str(e))
                message = "Error: " + str(e)
            finally:
                await cursor.close()
        else:
            message = "You've already been added! " + \
                      emojize(":star:", use_aliases=True) + " away :)"
        await db.close()
    else:
        message = "That doesn't work in here. Send me a PM instead " + \
                  emojize(":wink:", use_aliases=True)
    return message


# Store hash of message_id's media in database
async def store_hash(database, message_id, media_hash, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    # Add message_id, photo's hash, and current date to database
    sql = "INSERT INTO media_hash VALUES (" + str(
        message_id) + ",'" + media_hash + "', + date('now'));"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Commit your changes in the database
        await db.commit()
    except Exception as e:
        # Rollback in case there is any error
        await db.rollback()
        print("Error in store_hash: " + str(e))
    # Delete hashes older than 30 days
    sql = "DELETE FROM media_hash " \
          + "WHERE Date NOT BETWEEN date('now','-30 days') " \
          + "AND date('now');"
    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Commit your changes in the database
        await db.commit()
    except Exception as e:
        # Rollback in case there is any error
        await db.rollback()
        print("Error in store_hash: " + str(e))
    finally:
        await cursor.close()
    await db.close()


# Fetch hash of message_id
async def fetch_one_hash(message_id, database, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    # Fetch a specific message_id's associated hash
    sql = "SELECT hash FROM media_hash WHERE message_id = " + str(
        message_id) + ";"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch one row
        result = await cursor.fetchone()
    except Exception as e:
        print("Error in compare_hash: " + str(e))
        result = str(e)
    finally:
        await cursor.close()
    await db.close()
    return result


# Fetch all stored hashes
async def fetch_all_hashes(message_id, database, loop):
    db = await aiosqlite.connect("db/" + database + ".db")
    sql = "SELECT message_id, hash FROM media_hash"
    cursor = await db.cursor()

    try:
        # Execute the SQL command
        await cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        result = await cursor.fetchall()
    except Exception as e:
        print("Error in compare_hash: " + str(e))
        result = str(e)
    finally:
        await cursor.close()
    await db.close()
    return result
