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
#import os
#from dotenv import load_dotenv
import re



def get_tags(pixiv, illustration_id, blacklist_tags):
    illustration_info = pixiv.fetch_illustration(illustration_id)
    tag_list = ""
    if illustration_info.tags is not None:
        ignore_tag = False
        list_len = len(illustration_info.tags)
        # Max of 5 tags
        if list_len > 5:
            list_len = 5

        for x in range(list_len):
            tag = illustration_info.tags[x]['translated_name']

            try:
                if tag is not None:
                    print(tag)
                    # Check to see if the current tag is in the blacklist
                    for x in range(len(blacklist_tags)):
                        if blacklist_tags[x] in tag:
                            ignore_tag = True
                            break
                    if ignore_tag:
                        continue
                    # Ignore parenthesis and everything inside
                    elif "(" in tag:
                        tag_split = tag.split("(", 1)
                        tag = tag_split[0]
                    # Remove special characters
                    tag = re.sub("\W+", " ", tag)
                    # Capatalize every first letter of words
                    tag = tag.title()
                    # Remove spaces
                    tag = tag.replace(" ", "")
                    if tag not in tag_list:
                        tag_list += f"#{tag} "
            except TypeError:
                continue
        tag_list += "\n"

    return tag_list


def convert_string_tags(temp_list, blacklist_tags):
    tag_list = ""
    if temp_list is not None:
        ignore_tag = False
        list_len = len(temp_list)
        # Max of 5 tags
        if list_len > 5:
            list_len = 5

        for x in range(list_len):
            tag = str(temp_list[x])
            try:
                if tag is not None:
                    print(f"tag: {tag}")
                    # Check to see if the current tag is in the blacklist
                    for x in range(len(blacklist_tags)):
                        if blacklist_tags[x] in tag:
                            ignore_tag = True
                            break
                    if ignore_tag:
                        continue
                    # Ignore parenthesis and everything inside
                    elif "(" in tag:
                        tag_split = tag.split("(", 1)
                        tag = tag_split[0]
                    # Remove special characters
                    tag = re.sub("\W+", " ", tag)
                    # Capatalize every first letter of words
                    tag = tag.title()
                    # Remove spaces
                    tag = tag.replace(" ", "")
                    if tag not in tag_list:
                        tag_list += f"#{tag} "
            except TypeError:
                continue
        tag_list += "\n"

    return tag_list
