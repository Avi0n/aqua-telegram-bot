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
#from pixivapi import Client

def get_tags(pixiv, illustration_id):
    illustration_info = pixiv.fetch_illustration(illustration_id)
    tag_list = ""
    blacklist_tags = ["1000", "beautiful girl"]
    if illustration_info.tags is not None:
        ignore_tag = False
        for x in range(len(illustration_info.tags)):
            tag = illustration_info.tags[x]['translated_name']

            try:
                if tag is not None:
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
                    # Remove spaces in tag
                    tag = tag.replace(" ", "").replace("'", "")
                    if tag not in tag_list:
                        tag_list += f"#{tag} "
            except TypeError:
                continue

    return tag_list
