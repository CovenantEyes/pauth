from pauth.clients import Client
from pauth.clients.errors import UnauthorizedClientError, UnknownClientError
from pauth.conf import config
from pauth.credentials import ClientCredentials
from pauth.requests.errors import InvalidAuthorizationRequestError


class Request(object):
    required_parameters = ()

    def __new__(cls, request):
        """
        We need to take the library-user's request and transform it into something
        our library understands. We'll use an adapter function that's setup in the
        global config to do this transformation. The library-user will need to
        define this adapter, but it will usually be configured by some framework
        plugin, like a Django middleware layer or something. Ideally, the library-
        user won't have to mess with this very often (if ever).
        """
        return config.requests.adapter(request)

    def __init__(self, method='GET', headers=None, parameters=None):
        """
        This constructor defines our internally-standard interface for creating a
        request. The library-user will have to define an adapter to transform their
        requests into this interface (see `__new__()` above). But this interface
        is pretty generic and straightforward, so it shouldn't be a problem.

        This constructor also does some initial parsing of the request to get
        OAuth-specific parameters. Various subclasses of this class will have
        different rules for how the request ought to look. Depending on those rules
        (defined in the `validate()` method), this constructor can throw errors.
        """
        self.method = method
        self.headers = headers or {}
        self.parameters = parameters or {}

        if 'client_id' in self.parameters:
            credentials = ClientCredentials(self.parameters['client_id'],
                                            self.parameters.get('client_secret'))
            self.client = Client(credentials)
        else:
            self.client = None

        self.response_type = self.parameters.get('response_type')
        self.state = self.parameters.get('state')

        self.validate()  # throw some errors if the request is yucky

    def validate(self):
        """
        A hook into the constructor that allows subclasses of this class to define
        their own rules about what a valid request looks like. This method should
        throw errors when it encounters aspects of the request that it doesn't like.
        """
        if not self._has_required_parameters():
            raise InvalidAuthorizationRequestError('Some required request parameters are missing.')

        if self.client is None:
            raise UnknownClientError(self.client)
        elif not self.client.is_registered():
            raise UnknownClientError(self.client)
        elif not self.client.is_authorized():
            raise UnauthorizedClientError(self.client)

    def _has_required_parameters(self):
        """
        A simple utility function for checking to see if the request has all
        the parameters defined in `required_parameters`. It's meant to be used by
        subclasses in order keep things DRY.
        """
        return all(p in self.required_parameters for p in self.parameters)

    def has_header(self, header):
        """
        Returns `True` when `header` matches at least one of the requests headers
        without comparing case.
        """
        return any(header.lower() == h.lower() for h in self.headers)

    def get_header(self, header):
        """
        Returns the value of the request header that matches `header` (without
        comparing case) or `None` if there is no matching header.
        """
        return next((v for k, v in self.headers.items()
                     if k.lower() == header.lower()), None)