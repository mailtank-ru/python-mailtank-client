# coding: utf-8
import sys
import json
import logging
from urlparse import urljoin

import requests

from .models import Tag, Mailing, Layout, Project, Subscriber
from .exceptions import MailtankError


ident = lambda x: x


class MailtankIterator(object):
    def __init__(self, fetch_page, wrapper=ident, start=0, end=None):
        self._fetch_page = fetch_page
        self._start = start
        self._end = end
        self._wrapper = wrapper

    def get_total_count(self):
        return self._fetch_page(0)['total']

    def __iter__(self):
        first_page_data = self._fetch_page(0)
        pages_total = first_page_data['pages_total']
        objects_per_page = len(first_page_data['objects'])
        if objects_per_page == 0:
            return

        start_page = self._start / objects_per_page
        if start_page >= pages_total:
            return

        if self._end is None:
            limit = sys.maxint
        else:
            limit = self._end - self._start
        to_skip = self._start - start_page * objects_per_page
        current_page = start_page

        while current_page < pages_total and limit > 0:
            yielded = 0
            page_data = self._fetch_page(current_page)
            for obj in page_data['objects'][to_skip:to_skip+limit]:
                yield self._wrapper(obj)
                yielded += 1
            current_page += 1
            limit -= yielded
            to_skip = 0


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

    def _check_response(self, response):
        if not 200 <= response.status_code < 400:
            raise MailtankError(response)
        return response

    def _json(self, response):
        response = self._check_response(response)
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

    def _delete(self, url, **kwargs):
        self._logger.debug('DELETE %s with %s', url, kwargs)
        return self._session.delete(url, **kwargs)

    def _get_endpoint(self, endpoint, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._json(self._get(url, **kwargs))

    def _post_endpoint(self, endpoint, data, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._json(self._post(url, data=json.dumps(data), **kwargs))

    def _put_endpoint(self, endpoint, data, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._json(self._put(url, data=json.dumps(data), **kwargs))

    def _patch_endpoint(self, endpoint, data, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._check_response(self._patch(url, data=json.dumps(data), **kwargs))

    def _delete_endpoint(self, endpoint, **kwargs):
        url = urljoin(self._api_url, endpoint)
        return self._check_response(self._delete(url, **kwargs))

    def get_tags(self, mask=None, start=0, end=None):
        def fetch_page(n):
            return self._get_endpoint(
                'tags/', params={
                    'mask': mask,
                    # Mailtank API считает страницы с единицы
                    'page': n + 1,
                })
        wrapper = lambda *args, **kwargs: Tag(*args, client=self, **kwargs)
        return MailtankIterator(fetch_page, wrapper, start=start, end=end)

    def get_subscribers(self, query=None, start=0, end=None):
        def fetch_page(n):
            return self._get_endpoint(
                'subscribers/', params={
                    'query': query,
                    'page': n + 1,
                })
        wrapper = lambda *args, **kwargs: Subscriber(*args, client=self, **kwargs)
        return MailtankIterator(fetch_page, wrapper, start=start, end=end)

    def get_project(self):
        """Возвращает текущий проект.

        :rtype: :class:`Project`
        """
        response = self._get_endpoint('project')
        return Project(response, client=self)

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
        return Subscriber(response, client=self)

    def get_subscriber(self, id):
        """Возвращает подписчика."""
        return Subscriber(self._get_endpoint('subscribers/{0}'.format(id)),
                          client=self)

    def update_subscriber(self, id, email=None, tags=None, properties=None):
        """Обновляет данные подписчика."""
        data = {}
        if email is not None:
            data['email'] = email
        if tags is not None:
            data['tags'] = tags
        if properties is not None:
            data['properties'] = properties

        self._put_endpoint('subscribers/{0}'.format(id), data)

    def delete_subscriber(self, id):
        """Удаляет подписчика."""
        self._delete_endpoint('subscribers/{0}'.format(id))

    def reassign_tag(self, tag, subscribers):
        """Переназначает тег `tag` подписчикам, указанным в `subscribers`.

        :param tag: строка с именем тега
        :param target: строка "all" или список идентификаторов подписчиков
        """
        self._patch_endpoint('subscribers/', {
            'action': 'reassign_tag',
            'data': {
                'subscribers': subscribers,
                'tag': tag,
            },
        })

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
        return Mailing(response, client=self)

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
        return Layout(response, client=self)

    def delete_layout(self, id):
        """Удаляет шаблон."""
        self._delete_endpoint('layouts/{0}'.format(id))
