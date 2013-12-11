# coding: utf-8
class MailtankError(Exception):
    def __init__(self, response):
        super(MailtankError, self).__init__(response)
        #: Ответ API, который послужил причиной ошибки
        self.response = response
        #: Статус ответа API, послужившего причиной ошибки
        self.code = self.response.status_code
        try:
            errors = self.response.json()
            if self.code == 400:
                self.message = unicode(errors)
            else:
                self.message = errors.get('message')
        except:
            self.message = self.response

    def __repr__(self):
        return '<MailtankError {0} [{1}]>'.format(self.code, self.message)

    def __str__(self):
        return '{0} {1}'.format(self.code, self.message)
