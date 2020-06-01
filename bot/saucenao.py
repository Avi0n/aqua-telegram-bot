# The following script is mostly a copy and paste from https://saucenao.com/tools/examples/api/identify_images_v1.1.py
import sys
import os
import io
import unicodedata
import requests
from PIL import Image
import json
import codecs
import re
import time
from collections import OrderedDict
sys.stdout = codecs.getwriter('utf8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf8')(sys.stderr.detach())
from dotenv import load_dotenv


# Search for source from SauceNao and return string i.e. "This might be it: URL"
def get_source(file_name):
    api_key = os.getenv("SAUCE_NAO_TOKEN")
    #EnableRename = False
    minsim = '68!'

    extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    thumbSize = (250, 250)

    #enable or disable indexes
    index_hmags = '0'
    index_reserved = '0'
    index_hcg = '0'
    index_ddbobjects = '0'
    index_ddbsamples = '0'
    index_pixiv = '1'
    index_pixivhistorical = '1'
    index_reserved = '0'
    index_seigaillust = '1'
    index_danbooru = '1'
    index_drawr = '1'
    index_nijie = '1'
    index_yandere = '1'
    index_animeop = '0'
    index_reserved = '0'
    index_shutterstock = '0'
    index_fakku = '0'
    index_hmisc = '0'
    index_2dmarket = '0'
    index_medibang = '0'
    index_anime = '0'
    index_hanime = '0'
    index_movies = '0'
    index_shows = '0'
    index_gelbooru = '0'
    index_konachan = '1'
    index_sankaku = '0'
    index_animepictures = '0'
    index_e621 = '0'
    index_idolcomplex = '0'
    index_bcyillust = '0'
    index_bcycosplay = '0'
    index_portalgraphics = '0'
    index_da = '1'
    index_pawoo = '0'
    index_madokami = '0'
    index_mangadex = '0'

    #generate appropriate bitmask
    db_bitmask = int(
        index_mangadex + index_madokami + index_pawoo + index_da +
        index_portalgraphics + index_bcycosplay + index_bcyillust +
        index_idolcomplex + index_e621 + index_animepictures + index_sankaku +
        index_konachan + index_gelbooru + index_shows + index_movies +
        index_hanime + index_anime + index_medibang + index_2dmarket +
        index_hmisc + index_fakku + index_shutterstock + index_reserved +
        index_animeop + index_yandere + index_nijie + index_drawr +
        index_danbooru + index_seigaillust + index_anime +
        index_pixivhistorical + index_pixiv + index_ddbsamples +
        index_ddbobjects + index_hcg + index_hanime + index_hmags, 2)
    print("dbmask=" + str(db_bitmask))

    #encoded print - handle random crap
    def printe(line):
        print(str(line).encode(sys.getdefaultencoding(),
                               'replace'))  #ignore or replace
    fname = file_name
    for ext in extensions:
        if fname.lower().endswith(ext):
            print(fname)
            image = Image.open(fname)
            image = image.convert('RGB')
            image.thumbnail(thumbSize, resample=Image.ANTIALIAS)
            imageData = io.BytesIO()
            image.save(imageData, format='PNG')

            url = 'http://saucenao.com/search.php?output_type=2&numres=1&minsim=' + minsim + '&dbmask=' + str(
                db_bitmask) + '&api_key=' + api_key
            files = {'file': ("image.png", imageData.getvalue())}
            imageData.close()

            processResults = True
            while True:
                r = requests.post(url, files=files)
                if r.status_code != 200:
                    if r.status_code == 403:
                        print(
                            'Incorrect or Invalid API Key! Please Edit Script to Configure...'
                        )
                        return
                    else:
                        #generally non 200 statuses are due to either overloaded servers or the user is out of searches
                        print("status code: " + str(r.status_code))
                        time.sleep(10)
                else:
                    results = json.JSONDecoder(
                        object_pairs_hook=OrderedDict).decode(r.text)
                    if int(results['header']['user_id']) > 0:
                        #api responded
                        print(
                            'Remaining Searches 30s|24h: ' +
                            str(results['header']['short_remaining']) +
                            '|' +
                            str(results['header']['long_remaining']))
                        if int(results['header']['status']) == 0:
                            #search succeeded for all indexes, results usable
                            break
                        else:
                            if int(results['header']['status']) > 0:
                                #One or more indexes are having an issue.
                                #This search is considered partially successful, even if all indexes failed, so is still counted against your limit.
                                #The error may be transient, but because we don't want to waste searches, allow time for recovery.
                                print('API Error. Retrying in 30 seconds...')
                                return 1
                            else:
                                #Problem with search as submitted, bad image, or impossible request.
                                #Issue is unclear, so don't flood requests.
                                print(
                                    'Bad image or other request error. Returning...'
                                )
                                processResults = False
                                return 0
                    else:
                        #General issue, api did not respond. Normal site took over for this error state.
                        #Issue is unclear, so don't flood requests.
                        print(
                            'Bad image, or API failure. Returning...')
                        processResults = False
                        return 0

            if processResults:
            #print(results)

                if int(results['header']['results_returned']) > 0:
                    #one or more results were returned
                    if float(results['results'][0]['header']
                            ['similarity']) > float(
                                results['header']['minimum_similarity']):
                        print('hit! ' + str(results['results'][0]['header']
                                            ['similarity']))

                        #get vars to use
                        service_name = ''
                        illust_id = 0
                        member_id = -1
                        index_id = results['results'][0]['header'][
                            'index_id']
                        page_string = ''
                        page_match = re.search(
                            '(_p[\d]+)\.',
                            results['results'][0]['header']['thumbnail'])
                        if page_match:
                            page_string = page_match.group(1)

                        if index_id == 5 or index_id == 6:
                            #5->pixiv 6->pixiv historical
                            service_name = 'pixiv'
                            member_id = results['results'][0]['data'][
                                'member_id']
                            illust_id = results['results'][0]['data'][
                                'pixiv_id']
                        if index_id == 9:
                            #9->danbooru
                            service_name = 'danbooru'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'danbooru_id']
                        elif index_id == 12:
                            #9->yandere
                            service_name = 'yandere'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'yandere_id']
                        elif index_id == 26:
                            #26->konachan
                            service_name = 'konachan'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'konachan_id']
                        elif index_id == 8:
                            #8->nico nico seiga
                            service_name = 'seiga'
                            member_id = results['results'][0]['data'][
                                'member_id']
                            illust_id = results['results'][0]['data'][
                                'seiga_id']
                        elif index_id == 10:
                            #10->drawr
                            service_name = 'drawr'
                            member_id = results['results'][0]['data'][
                                'member_id']
                            illust_id = results['results'][0]['data'][
                                'drawr_id']
                        elif index_id == 11:
                            #11->nijie
                            service_name = 'nijie'
                            member_id = results['results'][0]['data'][
                                'member_id']
                            illust_id = results['results'][0]['data'][
                                'nijie_id']
                        elif index_id == 34:
                            #34->da
                            service_name = 'da'
                            illust_id = results['results'][0]['data'][
                                'da_id']
                        else:
                            #unknown
                            print('Unhandled Index! Exiting...')
                            return
                        
                        # Store pic_similarity for later use
                        pic_similarity = str(results['results'][0]
                                                ['header']['similarity'])
                        result_url = results['results'][0]['data'][
                            'ext_urls'][0]

                        # Send result URL
                        if float(results['results'][0]['header']
                                    ['similarity']) < 80:
                            return "This _might_ be it: [Sauce](" + result_url + ")" + \
                                "\nSimilarity: " + pic_similarity
                        else:
                            return "[Sauce](" + result_url + ")" + "\nSimilarity: " + \
                                pic_similarity
                    else:
                        print('miss...')
                        return "I couldn't find a source for that"
                else:
                    print('no results... ;_;')
                    return "No results"

                if int(results['header']['long_remaining']
                    ) < 1:  #could potentially be negative
                    print(
                        'Out of searches for today. Returning...'
                    )
                    return 1
                if int(results['header']['short_remaining']) < 1:
                    print(
                        'Out of searches for this 30 second period. Returning...'
                    )
                    return 2
    print('Done with SauceNao search.')


# Search for source from SauceNao and return Pixiv URL
def get_image_source(file_name):
    api_key = os.getenv("SAUCE_NAO_TOKEN")
    #EnableRename = False
    minsim = '68!'

    extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    thumbSize = (250, 250)

    #enable or disable indexes
    index_hmags = '0'
    index_reserved = '0'
    index_hcg = '0'
    index_ddbobjects = '0'
    index_ddbsamples = '0'
    index_pixiv = '0'
    index_pixivhistorical = '1'
    index_reserved = '0'
    index_seigaillust = '0'
    index_danbooru = '1'
    index_drawr = '0'
    index_nijie = '0'
    index_yandere = '1'
    index_animeop = '0'
    index_reserved = '0'
    index_shutterstock = '0'
    index_fakku = '0'
    index_hmisc = '0'
    index_2dmarket = '0'
    index_medibang = '0'
    index_anime = '0'
    index_hanime = '0'
    index_movies = '0'
    index_shows = '0'
    index_gelbooru = '1'
    index_konachan = '1'
    index_sankaku = '0'
    index_animepictures = '0'
    index_e621 = '0'
    index_idolcomplex = '0'
    index_bcyillust = '0'
    index_bcycosplay = '0'
    index_portalgraphics = '0'
    index_da = '0'
    index_pawoo = '0'
    index_madokami = '0'
    index_mangadex = '0'

    #generate appropriate bitmask
    db_bitmask = int(
        index_mangadex + index_madokami + index_pawoo + index_da +
        index_portalgraphics + index_bcycosplay + index_bcyillust +
        index_idolcomplex + index_e621 + index_animepictures + index_sankaku +
        index_konachan + index_gelbooru + index_shows + index_movies +
        index_hanime + index_anime + index_medibang + index_2dmarket +
        index_hmisc + index_fakku + index_shutterstock + index_reserved +
        index_animeop + index_yandere + index_nijie + index_drawr +
        index_danbooru + index_seigaillust + index_anime +
        index_pixivhistorical + index_pixiv + index_ddbsamples +
        index_ddbobjects + index_hcg + index_hanime + index_hmags, 2)
    #print("dbmask=" + str(db_bitmask))

    #encoded print - handle random crap
    def printe(line):
        print(str(line).encode(sys.getdefaultencoding(),
                               'replace'))  #ignore or replace

    fname = file_name
    for ext in extensions:
        if fname.lower().endswith(ext):
            #print(fname)
            image = Image.open(fname)
            image = image.convert('RGB')
            image.thumbnail(thumbSize, resample=Image.ANTIALIAS)
            imageData = io.BytesIO()
            image.save(imageData, format='PNG')

            url = 'http://saucenao.com/search.php?output_type=2&numres=1&minsim=' + minsim + '&dbmask=' + str(
                db_bitmask) + '&api_key=' + api_key
            files = {'file': ("image.png", imageData.getvalue())}
            imageData.close()

            processResults = True
            while True:
                r = requests.post(url, files=files)
                if r.status_code != 200:
                    if r.status_code == 403:
                        print(
                            'Incorrect or Invalid API Key! Please Edit Script to Configure...'
                        )
                        return 0
                    else:
                        #generally non 200 statuses are due to either overloaded servers or the user is out of searches
                        print("status code: " + str(r.status_code))
                        if r.status_code == 429:
                            time.sleep(25)
                        else:
                            time.sleep(30)
                else:
                    results = json.JSONDecoder(
                        object_pairs_hook=OrderedDict).decode(r.text)
                    if int(results['header']['user_id']) > 0:
                        #api responded
                        print(
                            'Remaining Searches 30s|24h: ' +
                            str(results['header']['short_remaining']) +
                            '|' +
                            str(results['header']['long_remaining']))
                        if int(results['header']['status']) == 0:
                            #search succeeded for all indexes, results usable
                            break
                        else:
                            if int(results['header']['status']) > 0:
                                #One or more indexes are having an issue.
                                #This search is considered partially successful, even if all indexes failed, so is still counted against your limit.
                                #The error may be transient, but because we don't want to waste searches, allow time for recovery.
                                print('API Error. Returning...')
                                return 1
                            else:
                                #Problem with search as submitted, bad image, or impossible request.
                                #Issue is unclear, so don't flood requests.
                                print(
                                    'Bad image or other request error. Returning...'
                                )
                                processResults = False
                                time.sleep(10)
                                break
                                #return 0
                    else:
                        #General issue, api did not respond. Normal site took over for this error state.
                        #Issue is unclear, so don't flood requests.
                        print(
                            'Bad image, or API failure. Returning...')
                        processResults = False
                        time.sleep(10)
                        break
                        #return 0

            while processResults:
                #print(json.dumps(results, indent=4))
                if int(results['header']['results_returned']) > 0:
                    #one or more results were returned
                    if float(results['results'][0]['header']
                            ['similarity']) > float(
                                results['header']['minimum_similarity']):
                        print('hit! ' + str(results['results'][0]['header']
                                            ['similarity']))

                        #get vars to use
                        service_name = ''
                        illust_id = 0
                        member_id = -1
                        index_id = results['results'][0]['header'][
                            'index_id']
                        page_string = ''
                        page_match = re.search(
                            '(_p[\d]+)\.',
                            results['results'][0]['header']['thumbnail'])
                        if page_match:
                            page_string = page_match.group(1)

                        if index_id == 9:
                            #9->danbooru
                            service_name = 'danbooru'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'danbooru_id']
                        elif index_id == 12:
                            #9->yandere
                            service_name = 'yandere'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'yandere_id']
                        elif index_id == 26:
                            #26->konachan
                            service_name = 'konachan'
                            material = results['results'][0]['data'][
                                'material']
                            characters = results['results'][0]['data'][
                                'characters']
                            illust_id = results['results'][0]['data'][
                                'konachan_id']
                        elif index_id == 5 or index_id == 6:
                            #5->pixiv 6->pixiv historical
                            service_name = 'pixiv'
                            member_id = results['results'][0]['data'][
                                'member_id']
                            illust_id = results['results'][0]['data'][
                                'pixiv_id']

                        else:
                            #unknown
                            print('Unhandled Index! Exiting...')
                            return 0

                        # Send result URL
                        if float(results['results'][0]['header']
                                    ['similarity']) < 70:
                            return 3
                        else:
                            if index_id == 5 or index_id == 6:
                                return [illust_id]
                            else:
                                return [illust_id, material, characters]
                    else:
                        print('Miss...')
                        return 3
                else:
                    print('No results... ;_;')
                    return 3

                # could potentially be negative
                if int(results['header']['long_remaining']) < 1:
                    print('Out of searches for today :(')
                    return 1
                if int(results['header']['short_remaining']) < 1:
                    print('Out of searches for this 30 second period.')
                    time.sleep(25)

    print('Done with SauceNao Pixiv search.')
