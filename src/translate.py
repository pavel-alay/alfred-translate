#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from urllib.parse import urlencode
import json
import feedback
import asyncio
import aiohttp
import re
import sys

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


async def process_get_response_as_json(url, session):
    async with session.get(url=url) as response:
        resp = await response.read()
        response_json = json.loads(resp)
        return response_json


async def process_spelling_request(input_string, source_lang, session):
    # Build spell check url
    spell_check_params = {
        'text': input_string,
        'lang': source_lang
    }
    spell_check_url = 'https://speller.yandex.net/services/spellservice.json/checkText' + '?' + urlencode(
        spell_check_params)
    return await process_get_response_as_json(spell_check_url, session)


async def process_vocabulary_request(input_string, source_lang, target_lang, session):
    # Build article url
    article_params = {
        'key': dict_api_key,
        'lang': source_lang + '-' + target_lang,
        'text': input_string,
        'flags': 4
    }
    article_url = 'https://dictionary.yandex.net/api/v1/dicservice.json/lookup' + '?' + urlencode(article_params)
    return await process_get_response_as_json(article_url, session)


async def process_translate_request(input_string, source_lang, target_lang, session):
    if not translate_api_key:
        return {}
    body = {
        'sourceLanguageCode': source_lang,
        'targetLanguageCode': target_lang,
        'texts': [
            input_string
        ]
    }
    async with session.post(url='https://translate.api.cloud.yandex.net/translate/v2/translate',
                            headers={'Authorization': translate_api_key},
                            json=body) as response:
        resp = await response.read()
        response_json = json.loads(resp)
        return response_json


async def process_requests(input_string):
    source_lang = get_source_lang(input_string)
    target_lang = get_target_lang(input_string)
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            process_spelling_request(input_string, source_lang, session),
            process_vocabulary_request(input_string, source_lang, target_lang, session),
            process_translate_request(input_string, source_lang, target_lang, session)
        )


def get_output(input_string):
    """Main entry point"""
    fb = feedback.Feedback()
    input_string = input_string.strip()
    if not input_string:
        fb.add_item(title="Translation not found", valid="no")
        return fb

    # Making requests in parallel
    responses = asyncio.run(process_requests(input_string))

    spelling_suggestions_items = get_spelling_suggestions(responses[0])
    # Generate possible xml outputs
    formatted_spelling_suggestions = convert_spelling_suggestions(spelling_suggestions_items)
    formatted_translation_suggestions = get_translation_suggestions(responses[1], responses[2])
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
