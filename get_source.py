# The following script is mostly a copy and paste from https://saucenao.com/tools/examples/api/identify_images_v1.py
import os
import sys
import io
import requests
from PIL import Image
import json
import codecs
import time
from collections import OrderedDict
from dotenv import load_dotenv

# Search for source from SauceNao
def get_source():
    api_key = os.getenv("SAUCE_NAO_TOKEN")
    #EnableRename = False
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
    #def printe(line):
        # ignore or replace
    #    print(str(line).encode(sys.getdefaultencoding(), 'replace'))

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
                                print('Incorrect or Invalid API Key! Please Edit Script to Configure...')
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
                                        print('API Error. Retrying in 10 seconds...')
                                        time.sleep(10)
                                    else:
                                        # Problem with search as submitted, bad image, or impossible request.
                                        # Issue is unclear, so don't flood requests.
                                        print('Bad image or other request error. Skipping in 10 seconds...')
                                        processResults = False
                                        return "Something went wrong."
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
                                    return "This _might_ be it: [Sauce](" + result_url + ")" + \
                                        "\nSimilarity: " + pic_similarity
                                else:
                                    return "[Sauce](" + result_url + ")" + "\nSimilarity: " + \
                                        pic_similarity
                            else:
                                print('miss...')
                                return "I couldn't find a source for that image"
                        else:
                            print('no results... ;_;')
                            return "No results"

                        # could potentially be negative
                        if int(results['header']['long_remaining']) < 1:
                            print('Out of searches for today :(')
                            return "Out of searches for today :("
                        if int(results['header']['short_remaining']) < 1:
                            print('Out of searches for this 30 second period. Sleeping for 25 seconds...')
                            return "Out of searches for this 30 second period. Try again later."

    print('Done with SauceNao search.')
