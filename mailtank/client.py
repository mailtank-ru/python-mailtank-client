# coding: utf-8
import json
import logging
from urlparse import urljoin

import requests

from .models import Tag, Mailing, Layout, Project
from .exceptions import MailtankError


class Mailtank(object):
    def __init__(self, api_url, api_key):
        self._api_url = api_url
        self._api_key = api_key
        self._session = requests.session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'rsstank',
            'X-Auth-Token': self._api_key,
        })
        self._logger = logging.getLogger(__name__)

    def _delete(self, url, **kwargs):
        self._logger.debug('DELETE %s with %s', url, kwargs)
        return self._session.delete(url, **kwargs)

    def _json(self, response):
        if not 200 <= response.status_code < 400:
            raise MailtankError(response)
        try:
            return response.json()
        except ValueError:
            raise MailtankError(response)

    def _get(self, url, **kwargs):
        self._logger.debug('GET %s with %s', url, kwargs)
        return self._session.get(url, **kwargs)

    def _patch(self, url, **kwargs):
        self._logger.debug('PATCH %s with %s', url, kwargs)
        return self._session.patch(url, **kwargs)

    def _post(self, url, data, **kwargs):
        self._logger.debug('POST %s with %s, %s', url, data, kwargs)
        return self._session.post(url, data, **kwargs)

    def _put(self, url, **kwargs):
        self._logger.debug('PUT %s with %s', url, kwargs)
        return self._session.put(url, **kwargs)

    def _get_endpoint(self, endpoint, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._json(self._get(url, **kwargs))

    def _post_endpoint(self, endpoint, data, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._json(self._post(url, data=json.dumps(data), **kwargs))

    def get_tags(self, mask=None):
        # TODO Не загружать все страницы сразу, возвращать итератор по тегам,
        # который будет подгружать страницы по мере необходимости

        def fetch_page(n):
            return self._get_endpoint(
                'tags/', params={
                    'mask': mask,
                    # Mailtank API считает страницы с единицы
                    'page': current_page + 1,
                })

        # Первая страница есть всегда; необходимо запросить её вне цикла
        # затем, чтобы узнать общее количество страниц
        current_page = 0
        first_page = fetch_page(current_page)
        pages_total = first_page['pages_total']
        rv = map(Tag, first_page['objects'])

        # Начинаем цикл со второй страницы, так как первую уже обработали
        current_page = 1
        while current_page < pages_total:
            page = fetch_page(current_page)
            rv += map(Tag, page['objects'])
            current_page += 1

        return rv

    def get_project(self):
        """Возвращает текущий проект.

        :rtype: :class:`Project`
        """
        response = self._get_endpoint('project')
        return Project(response)

    def create_subscriber(self, email, id=None, tags=None, properties=None):
        """Создаёт подписчика.

        :param email: email-адрес подписчика
        :type email: строка

        :param id: идентификатор подписчика
        :type id: строка

        :param tags: список тегов подписчика
        :type tags: список строк

        :param properties: словарь со свойствами подписчика

        :rtype: :class:`Subscriber`
        """
        data = {
            'email': email,
        }
        if id is not None:
            data['id'] = id
        if tags is not None:
            data['tags'] = tags
        if properties is not None:
            data['properties'] = properties

        response = self._post_endpoint('subscribers/', data)
        return Subscriber(response)

    def create_mailing(self, layout_id, context, target, attachments=None):
        """Создает и выполняет рассылку.

        :param layout_id: идентификатор шаблона, который будет
                          использован для рассылки
        :type layout_id: строка

        :param context: словарь, содержащий данные рассылки. Должен
                        удовлетворять структуре используемого шаблона

        :param target: словарь, задающий получателей рассылки.

        :param attachments: список словарей, описывающих вложения

        :rtype: :class:`Mailing`
        """
        data = {
            'context': context,
            'layout_id': layout_id,
            'target': target,
        }
        if attachments is not None:
            data['attachments'] = attachments

        response = self._post_endpoint('mailings/', data)
        return Mailing(response)

    def create_layout(self, name, subject_markup, markup, plaintext_markup=None,
                      base=None, id=None):
        """Создает шаблон.

        :param name: имя шаблона
        :type name: строка

        :param subject_markup: разметка темы шаблоны
        :type subject_markup: строка

        :param markup: разметка тела шаблона
        :type markup: строка

        :param plaintext_markup: разметка текстовой версии шаблона
        :type plaintext_markup: строка

        :param base: идентификатор родительского базового шаблона
        :type base: строка

        :param id: идентификатор шаблона
        :type id: строка

        :rtype: :class:`Layout`
        """
        data = {
            'name': name,
            'subject_markup': subject_markup,
            'markup': markup,
        }
        if plaintext_markup is not None:
            data['plaintext_markup'] = plaintext_markup
        if base is not None:
            data['base'] = base
        if id is not None:
            data['id'] = id

        response = self._post_endpoint('layouts/', data)
        return Layout(response)
