# coding: utf-8
class Tag(object):
    def __init__(self, data):
        self.name = data.get('name')


class Mailing(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.url = data.get('url')
        self.eta = data.get('eta')
        self.status = data.get('status')


class Layout(object):
    def __init__(self, data):
        self.id = data.get('id')


class Project(object):
    def __init__(self, data):
        self.name = data.get('name')
        self.from_email = data.get('from_email')


class Subscriber(object):
    def __init__(self, data):
        self.id = data.get('id')
        self.email = data.get('email')
        self.does_email_exist = data.get('does_email_exist')
        self.properties = data.get('properties')
        self.tags = data.get('tags')
