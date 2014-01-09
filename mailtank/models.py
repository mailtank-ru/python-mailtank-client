# coding: utf-8
class Model(object):
    fields = ()

    def __init__(self, data, client=None):
        self._client = client
        for field in self.fields:
            setattr(self, field, data.get(field))

    def to_dict(self):
        rv = {}
        for field in self.fields:
            rv[field] = getattr(self, field)
        return rv


class Tag(Model):
    fields = ('name',)


class Mailing(Model):
    fields = ('id', 'url', 'eta', 'status')


class Layout(Model):
    fields = ('id',)


class Project(Model):
    fields = ('name', 'from_email')


class Subscriber(Model):
    fields = ('id', 'url', 'email', 'does_email_exist', 'properties', 'tags')

    def save(self):
        data = self.to_dict()
        del data['id']
        del data['url']
        del data['does_email_exist']
        if self.id:
            self._client.update_subscriber(self.id, **data)
        else:
            self._client.create_subscriber(
                self.email, tags=self.tags, properties=self.properties)
