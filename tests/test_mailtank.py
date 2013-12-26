import json
import pytest

import furl
import httpretty

import mailtank


PAGES_DATA = [{
    'objects': [
        {u'name': 'type_main_news'},
        {'name': 'type_spec'},
        {'name': ''},
        {'name': 'type_unknown'},
        {'name': 'tag_7523'},
        {'name': 'tag_11592'},
        {'name': 'tag_23517'},
        {'name': 'tag_7447'},
        {'name': 'tag_23758'},
        {'name': 'tag_23464'},
    ],
    'page': 1,
    'pages_total': 3,
}, {
    'objects': [
        {'name': 'tag_17499'},
        {'name': 'tag_15097'},
        {'name': 'tag_22078'},
        {'name': 'tag_22622'},
        {'name': 'tag_10538'},
        {'name': 'tag_2743'},
        {'name': 'tag_18477'},
        {'name': 'tag_10932'},
        {'name': 'tag_20410'},
        {'name': 'tag_7900'},
    ],
    'page': 2,
    'pages_total': 3,
}, {
    'objects': [
        {'name': 'tag_9545'},
        {'name': 'tag_22437'},
        {'name': 'tag_4283'},
        {'name': 'tag_21889'},
        {'name': 'tag_2889'},
        {'name': 'tag_19389'},
        {'name': 'tag_23564'},
    ],
    'page': 3,
    'pages_total': 3,
}]


SUBSCRIBERS_DATA = [{
    'objects': [
        {
            'does_email_exist': True,
            'tags': ['rss:lala:http://lala.ru/lala:100'],
            'url': '/subscribers/c9a454f096',
            'email': 'anthony.romanovich@gmail.com',
            'id': 'c9a454f096',
            'properties': {}
        }, {
            'does_email_exist': True,
            'tags': ['rmnvch'],
            'url': '/subscribers/2eda62b980',
            'email': 'rmnvch@yandex.ru',
            'id': '2eda62b980',
            'properties': {}
        }
    ],
    'pages_total': 1,
    'page': 1
}]


class TestMailtankIterator(object):
    def test_basics(self):
        def fetch_page(n):
            return PAGES_DATA[n]

        def assert_len(expected_len, **kwargs):
            it = mailtank.client.MailtankIterator(fetch_page, **kwargs)
            assert len(list(it)) == expected_len

        assert_len(start=19, end=25, expected_len=6)
        assert_len(start=18, end=23, expected_len=5)
        assert_len(start=4, end=21, expected_len=17)
        assert_len(start=0, end=0, expected_len=0)
        assert_len(start=26, expected_len=1)
        assert_len(start=100, expected_len=0)
        assert_len(start=100, end=10000, expected_len=0)
        assert_len(start=0, expected_len=27)
        assert_len(expected_len=27)

    def test_empty_iterator(self):
        it = mailtank.client.MailtankIterator(lambda n: {
            'page': 1,
            'pages_total': 1,
            'total': 0,
            'objects': [],
        })
        assert not list(it)


class TestMailtankClient(object):
    def setup_method(self, method):
        self.m = mailtank.Mailtank('http://api.mailtank.ru', 'pumpurum')

    @httpretty.httprettified
    def test_get_tags(self):
        def request_callback(method, uri, headers):
            page = int(furl.furl(uri).args['page'])
            return (200, headers, json.dumps(PAGES_DATA[page - 1]))

        httpretty.register_uri(
            httpretty.GET, 'http://api.mailtank.ru/tags/',
            body=request_callback)

        tags = list(self.m.get_tags())

        assert len(tags) == sum(len(page['objects']) for page in PAGES_DATA)
        assert tags[0].name == 'type_main_news'
        assert tags[5].name == 'tag_11592'
        assert tags[-1].name == 'tag_23564'

    @httpretty.httprettified
    def test_get_subscribers(self):
        def request_callback(method, uri, headers):
            page = int(furl.furl(uri).args['page'])
            return (200, headers, json.dumps(SUBSCRIBERS_DATA[page - 1]))

        httpretty.register_uri(
            httpretty.GET, 'http://api.mailtank.ru/subscribers/',
            body=request_callback)

        subscribers = list(self.m.get_subscribers())

        assert len(subscribers) == sum(len(page['objects']) for page in SUBSCRIBERS_DATA)

        for i, subscriber_data in enumerate(SUBSCRIBERS_DATA[0]['objects']):
            for key, value in subscriber_data.iteritems():
                if key == 'url':
                    continue
                assert getattr(subscribers[i], key) == value

    @httpretty.httprettified
    def test_create_mailing(self):
        request_bodies = []

        def request_callback(request, uri, headers):
            request_bodies.append(request.body)
            return (200, headers, json.dumps({
                'eta': None,
                'id': 16,
                'status': 'ENQUEUED',
                'url': '/mailings/16',
            }))
        httpretty.register_uri(
            httpretty.POST, 'http://api.mailtank.ru/mailings/',
            responses=[httpretty.Response(body=request_callback,
                                          content_type='text/json'),
                       httpretty.Response(body='', status=500)])

        mailing = self.m.create_mailing('e25388fde8',
                                        {'name': 'Max'},
                                        {'tags': ['asdf'],
                                         'unsubscribe_tags': ['asdf']})
        assert json.loads(request_bodies.pop()) == {
            u'layout_id': u'e25388fde8',
            u'target': {
                u'unsubscribe_tags': [u'asdf'],
                u'tags': [u'asdf']
            },
            u'context': {u'name': u'Max'}
        }

        assert mailing.id == 16
        assert mailing.url == '/mailings/16'
        assert mailing.status == 'ENQUEUED'
        assert mailing.eta is None

        with pytest.raises(mailtank.MailtankError) as excinfo:
            mailing = self.m.create_mailing('e25388fde8', {}, {})

        assert str(excinfo.value) == '500 <Response [500]>'

    @httpretty.httprettified
    def test_get_project(self):
        httpretty.register_uri(
            httpretty.GET, 'http://api.mailtank.ru/project',
            body=json.dumps({
                'name': 'Pumpurum',
                'from_email': 'no-reply@pumpurum.ru',
            }))

        project = self.m.get_project()

        assert project.name == 'Pumpurum'
        assert project.from_email == 'no-reply@pumpurum.ru'

    @httpretty.httprettified
    def test_create_layout(self):
        request_bodies = []

        def request_callback(request, uri, headers):
            request_bodies.append(request.body)
            id = json.loads(request.body).get('id', '42adf23e')
            return (200, headers, json.dumps({'id': id}))
        httpretty.register_uri(
            httpretty.POST, 'http://api.mailtank.ru/layouts/',
            body=request_callback, content_type='text/json')

        layout = self.m.create_layout('name', 'subject-markup', 'markup')
        assert json.loads(request_bodies.pop()) == {
            u'subject_markup': u'subject-markup',
            u'markup': u'markup',
            u'name': u'name'
        }
        assert layout.id == '42adf23e'

        layout = self.m.create_layout(
            'name', 'subject-markup', 'markup',
            plaintext_markup='plaintext-markup', base='base-id', id='123')
        assert json.loads(request_bodies.pop()) == {
            u'subject_markup': u'subject-markup',
            u'name': u'name',
            u'plaintext_markup': u'plaintext-markup',
            u'markup': u'markup',
            u'base': u'base-id',
            u'id': u'123'
        }
        assert layout.id == '123'

    @httpretty.httprettified
    def test_update_subscriber(self):
        def request_callback(request, uri, headers):
            page = int(furl.furl(uri).args['page'])
            return (200, headers, json.dumps(SUBSCRIBERS_DATA[page - 1]))

        httpretty.register_uri(
            httpretty.GET, 'http://api.mailtank.ru/subscribers/',
            body=request_callback)

        subscriber = list(self.m.get_subscribers())[0]

        requests = []
        first_subscriber_data = SUBSCRIBERS_DATA[0]['objects'][0]
        def request_callback(request, uri, headers):
            data = json.loads(request.body)
            requests.append(data)
            return (200, headers, json.dumps(dict(first_subscriber_data, **data)))
        httpretty.register_uri(
            httpretty.PUT,
            'http://api.mailtank.ru/subscribers/{}'.format(first_subscriber_data['id']),
            body=request_callback)

        subscriber.save()
        last_request = requests.pop()
        assert last_request['tags'] == subscriber.tags
        assert last_request['properties'] == subscriber.properties
        assert last_request['email'] == subscriber.email

        subscriber.email = 'john@doe.com'
        subscriber.tags = ['example']
        subscriber.save()
        last_request = requests.pop()
        assert last_request['tags'] == subscriber.tags
        assert last_request['properties'] == subscriber.properties
        assert last_request['email'] == subscriber.email

    @httpretty.httprettified
    def test_delete_subscriber(self):
        httpretty.register_uri(
            httpretty.DELETE, 'http://api.mailtank.ru/subscribers/sw2fas')

        self.m.delete_subscriber('sw2fas')

        last_request = httpretty.last_request()
        assert last_request.method == 'DELETE'
        assert last_request.path == '/subscribers/sw2fas'

    @httpretty.httprettified
    def test_reassign_tag(self):
        httpretty.register_uri(
            httpretty.PATCH, 'http://api.mailtank.ru/subscribers/')

        self.m.reassign_tag('qwerty', ['id1', 'id2'])

        last_request = httpretty.last_request()
        assert last_request.method == 'PATCH'
        assert last_request.path == '/subscribers/'
        assert json.loads(last_request.body) == {
            'action': 'reassign_tag',
            'data': {
                'tag': 'qwerty',
                'subscribers': ['id1', 'id2'],
            }
        }
