#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from urllib.parse import urlencode
import json
import feedback
import concurrent.futures
import re
import sys
import http.client

dict_api_key = os.getenv('DICTIONARY_API_KEY')
translate_api_key = os.getenv('TRANSLATE_API_KEY')


def is_ascii(s):
    """https://stackoverflow.com/questions/196345/how-to-check-if-a-string-in-python-is-in-ascii"""
    return all(ord(c) < 128 for c in s)


def get_target_lang(text):
    """Returns direction of translation. en-ru or ru-en"""
    if is_ascii(text):
        return 'ru'
    else:
        return 'en'


def get_source_lang(text):
    """Returns either 'ru' or 'en' corresponding for text"""
    if is_ascii(text):
        return 'en'
    else:
        return 'ru'


def convert_spelling_suggestions(spelling_suggestions):
    res = []
    if len(spelling_suggestions) != 0:
        for spelling_suggestion in spelling_suggestions:
            res.append({
                'title': spelling_suggestion,
                'autocomplete': spelling_suggestion
            })
    return res


def get_spelling_suggestions(spelling_suggestions):
    """Returns spelling suggestions from JSON if any """
    res = []
    if spelling_suggestions and spelling_suggestions[0] and spelling_suggestions[0]['s']:
        res = spelling_suggestions[0]['s']
    return res


def get_translation_suggestions(vocabulary_article, translation_suggestions):
    """Returns XML with translate suggestions"""
    res = []
    if len(vocabulary_article['def']) != 0:
        for article in vocabulary_article['def']:
            for translation in article['tr']:
                if 'ts' in article.keys():
                    subtitle = article['ts']
                elif 'ts' in translation.keys():
                    subtitle = translation['ts']
                else:
                    subtitle = ''
                res.append({
                    'translation': translation['text'],
                    'transcription': subtitle,
                })
    if len(res) == 0:
        if translation_suggestions and len(translation_suggestions['translations']) != 0:
            for translation in translation_suggestions['translations']:
                res.append({
                    'translation': translation['text'].replace('\\ ', ' '),  # otherwise prints slash before spaces
                    'transcription': ''
                })
    return res


def to_json(response):
    return json.loads(response)


def process_spelling_request(input_string, source_lang):
    # Build spell check url
    spell_check_params = {
        'text': input_string,
        'lang': source_lang
    }
    conn = http.client.HTTPSConnection("speller.yandex.net")
    conn.request("GET", '/services/spellservice.json/checkText?' + urlencode(spell_check_params))
    response = conn.getresponse()
    data = response.read().decode()
    conn.close()
    return to_json(data)


def process_vocabulary_request(input_string, source_lang, target_lang):
    # Build article url
    article_params = {
        'key': dict_api_key,
        'lang': source_lang + '-' + target_lang,
        'text': input_string,
        'flags': 4
    }

    conn = http.client.HTTPSConnection("dictionary.yandex.net")
    conn.request("GET", '/api/v1/dicservice.json/lookup?' + urlencode(article_params))
    response = conn.getresponse()
    data = response.read().decode()
    conn.close()
    return to_json(data)


def process_translate_request(input_string, source_lang, target_lang):
    if not translate_api_key:
        return {}
    body = {
        'sourceLanguageCode': source_lang,
        'targetLanguageCode': target_lang,
        'texts': [
            input_string
        ]
    }
    headers = {
        'Authorization': translate_api_key
    }
    conn = http.client.HTTPSConnection('translate.api.cloud.yandex.net')
    conn.request("POST", "/translate/v2/translate", json.dumps(body), headers)
    response = conn.getresponse()
    data = response.read().decode()
    conn.close()
    return to_json(data)


def process_requests(input_string):
    source_lang = get_source_lang(input_string)
    target_lang = get_target_lang(input_string)
    data = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_req = {executor.submit(process_spelling_request, input_string, source_lang): 'spelling',
                         executor.submit(process_vocabulary_request, input_string, source_lang, target_lang): 'vocabulary',
                         executor.submit(process_translate_request, input_string, source_lang, target_lang): 'translate'}
    for future in concurrent.futures.as_completed(future_to_req):
        req_type = future_to_req[future]
        data[req_type] = future.result()
    return data


def get_output(input_string):
    """Main entry point"""
    fb = feedback.Feedback()
    input_string = input_string.strip()
    if not input_string:
        fb.add_item(title="Translation not found", valid="no")
        return fb

    # Making requests in parallel
    responses = process_requests(input_string)

    spelling_suggestions_items = get_spelling_suggestions(responses['spelling'])
    # Generate possible xml outputs
    formatted_spelling_suggestions = convert_spelling_suggestions(spelling_suggestions_items)
    formatted_translation_suggestions = get_translation_suggestions(responses['vocabulary'], responses['translate'])
    words_in_phase = len(re.split(' ', input_string))

    # Output
    if len(formatted_spelling_suggestions) == 0 and len(formatted_translation_suggestions) == 0:
        fb.add_item(title="Translation not found", valid="no")
        return fb

    # Prepare suggestions output
    # Spellcheck error
    if words_in_phase <= 2 and len(formatted_spelling_suggestions) != 0:
        for spelling_suggestion in formatted_spelling_suggestions:
            fb.add_item(title=spelling_suggestion['title'],
                        autocomplete=spelling_suggestion['autocomplete'],
                        icon='spellcheck.png')

    # Translations output
    for formatted_translated_suggestion in formatted_translation_suggestions:
        fb.add_item(title=formatted_translated_suggestion['translation'],
                    arg=formatted_translated_suggestion['translation'],
                    subtitle=formatted_translated_suggestion['transcription'])
    return fb


print(get_output(sys.argv[1]))
