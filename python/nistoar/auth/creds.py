"""
a module that defines a Credentials object used to capture identity attributes
for an authenticated user.
"""
import json, time
from datetime import datetime
from collections import UserDict, OrderedDict
from typing import Any, Iterable, Mapping
from abc import ABC, abstractmethod, abstractproperty

import jwt

from nistoar.base.config import ConfigurationException

class _FallbackDict(UserDict):
    """
    this is a dictionary that allows defaults mappings to be set at 
    construction time.  The values can be overridden; however, if the 
    value is not set explicitly or an explicitly set value is deleted,
    the corresponding default value will be set.
    """
    def __init__(self, defmap: Mapping=None):
        super(_FallbackDict, self).__init__()
        if defmap is None:
            defmap = {}
        self._defs = defmap

    def get(self, key, val=None):
        """
        this is just like the standard dict.get() except that if ``val`` is 
        provided, it will override the default set at construction time.
        """
        if val is None:
            val = self._defs.get(key)
        return self.data.get(key, val)

    def keys(self):
        """
        this is just like the standard dict.get() except that it will also
        include the keys set at construction time
        """
        for key in self._defs.keys():
            yield key
        for key in self.data.keys():
            if key not in self._defs:
                yield key

    def __contains__(self, key):
        return key in self.data or key in self._defs

    def __getitem__(self, key):
        if key not in self.data:
            return self._defs[key]
        return self.data[key]
    
        

class TokenGenerator(ABC):
    """
    a class that generates authentication tokens 
    """
    def __init__(self, config: Mapping):
        """
        configure this token generator.  The supported parameters depend on
        the concrete implemenetation.  
        """
        if not isinstance(config, Mapping):
            raise TypeError("TokenGenerator.init: config parameter not a "
                            "dictionary")
        self.cfg = config

    @abstractproperty
    def lifetime(self):
        """
        the default time in seconds before a generated tokens will expire and 
        no longer be valid.  This can be overridden via :py:meth:`generate`.  
        """
        raise NotImplemented()

    @abstractmethod
    def generate(self, subject: str, data: Mapping, lifetime=None) -> str:
        """
        generate the token based on the given data
        :param str  subject:  the subject (i.e. user ID) of the credential
        :param dict    data:  the data to encode into the token
        :param int lifetime:  the time in seconds until the token should expire.
                              If not given, a configured default will be used.
                              An implementation may ignore this value.
        """
        raise NotImplemented()

class JWTGenerator(TokenGenerator):
    """
    a JSON Web Token (JWT) generator.  
    """

    def __init__(self, config):
        if config is None:
            config = {}
        super(JWTGenerator, self).__init__(config)
        self._secret = self.cfg.get('secret')
        if not self._secret:
            raise ConfigurationException("missing or empty parameter: secret")
        self._life = self.cfg.get('lifetime', 3600)  # default: 1 hour
        if not isinstance(self._life, int):
            raise ConfigurationException("wrong type for parameter: secret: "
                                         "not an int")

    @property
    def lifetime(self):
        """
        the default time in seconds before a generated tokens will expire and 
        no longer be valid.  This can be overridden via :py:meth:`generate`.  
        """
        return self._life

    def generate(self, subject: str, data: Mapping, lifetime=None) -> str:
        """
        generate the token based on the given data
        :param str  subject:  the subject (i.e. user ID) of the credential
        :param dict    data:  the data to encode into the token
        :param int lifetime:  the time in seconds until the token should expire.
                              If not given, the configured default will be used.
        """
        if not lifetime:
            lifetime = self.lifetime
        if not isinstance(lifetime, int):
            raise TypeError("JWTGenerator.generate: lifetime not an int")
        claimset = dict(data)
        if 'token' in claimset:
            del claimset['token']
        if 'userId' in claimset:
            del claimset['userId']
        claimset['sub'] = subject
        claimset['exp'] = int(time.time() + lifetime)

        return jwt.encode(claimset, self._secret, algorithm="HS256")

default_token_generator = None
default_token_generator_cls = JWTGenerator

def create_default_token_generator(config: Mapping):
    """
    create the TokenGenerator that should be used when a specific 
    instance is not otherwise specified.  The default class is set to 
    JWTGenerator.  The created instance will be saved to this module 
    as the default (``default_token_generator``).
    @param dict config:  the configuration data to pass to the generator 
                         constructor.
    """
    global default_token_generator
    default_token_generator = default_token_generator_cls(config)
    return default_token_generator

UNAUTHENTICATED = "anonymous"

class Credentials(_FallbackDict):
    """
    a container for identity information about an authenticated user that 
    can also generated a token containing the same information.

    As a subclass of dict, one can access and update the user attributes 
    by name using dictionary [name] syntax.  Certain required attributes can 
    also be accessed via a property syntax (i.e. .name).  
    """
    _startorder = "userId userEmail userName userLastName".split()
    _endorder = "token expirationTime".split()
    __defattrs = {
        "userEmail": "not@set",
        "userName": "user",
        "userLastName": "unknown"
    }

    def __init__(self, userid: str = UNAUTHENTICATED,
                 useratts: Mapping[str, Any]=None,
                 expiration: float=None,
                 tokengen: TokenGenerator = None):
        """
        Create a credentials object for a specified user with a given set of 
        attributes.
        :param str        id:  the identifier for the user being set; 
                               default: "anonymous"
        :param dict useratts:  a dictionary of user attributes to initialize
                               this container with.
        :param float expiration:  the time that the authenticated session is set to 
                               expire, given as the epoch time in seconds.
        :param TokenGenerator tokengen:  the token generator to use to create
                               authentication tokens (via 
                               :py:meth:`create_token`).  If not set, a 
                               default will be used.  
        """
        global default_token_generator

        defattrs = {"userId": userid}
        defattrs.update(self.__defattrs)
        super(Credentials, self).__init__(defattrs)

        if useratts is not None:
            for key,val in useratts.items():
                if key not in ['userId']:
                    self[key] = val

        self._expires = None
        if expiration:
            if not isinstance(expiration, (float, int)):
                raise ValueError("Credentials ctor: expiration not a number: "+str(expiration))
            self._expires = expiration

        self._gen = tokengen
        if not self._gen:
            self._gen = default_token_generator

    @property
    def id(self):
        """
        the identifier for the authenticated user
        """
        return self['userId']

    def is_authenticated(self):
        """
        return False if the user ID represents an unauthenticated user
        """
        return self.id != UNAUTHENTICATED

    @property
    def expiration_time(self):
        """
        the expected expiration of the credential's authenticated validity.  This value can 
        be None if an expiration was not set at construction time.
        """
        return self._expires

    @property
    def expiration(self):
        """
        the expected expiration of the credential's authenticated validity, returned as 
        an ISO-formatted string
        """
        if self.expiration_time is None:
            return "(unset)"
        return datetime.fromtimestamp(self.expiration_time).isoformat()

    def expired(self):
        """
        return True if the this credential expiration time has passed
        """
        if self.expiration_time is None:
            return False
        return self.expiration_time <= time.time()

    @property
    def email(self) -> str:
        """
        the value of the "userEmail" attribute
        """
        return self['userEmail']

    @email.setter
    def email(self, val: str):
        self['userEmail'] = val

    @property
    def given_name(self) -> str:
        """
        the value of the "userName" attribute, representing the user's 
        given (or first) name
        """
        return self['userName']

    @given_name.setter
    def given_name(self, val: str):
        self['userName'] = val


    @property
    def family_name(self) -> str:
        """
        the value of the "userLastName" attribute, representing the user's 
        family (or last) name
        """
        return self['userLastName']
    
    @family_name.setter
    def family_name(self, val: str):
        self['userLastName'] = val


    def keys(self) -> Iterable[str]:
        """
        return the currently set keys in this container.  This implementation
        ensures a prefered order which determines the order that the attributes
        appear in the JSON output.
        """
        setkeys = list(super(Credentials, self).keys())
        for key in self._startorder:
            if key in setkeys:
                yield key
                setkeys.remove(key)

        for key in setkeys:
            if key not in self._endorder:
                yield key

        for key in self._endorder:
            if key in setkeys:
                yield key

    def to_json(self, indent=2):
        """
        export this credential as a JSON-encoded string
        """
        return json.dumps(OrderedDict(self), indent=indent)

    def write_json(self, ostrm, indent=2):
        """
        write this credential to an output stream as JSON-encoded data
        """
        json.dump(OrderedDict(self), ostrm, indent=indent)

    @classmethod
    def from_json_dict(cls, obj: Mapping):
        id = obj.get("userId", "anonymous")
        return cls(id, obj)

    def create_token(self, lifetime=None) -> str:
        """
        create a JST token with the information contained in this credential
        :param int lifetime:  the time in seconds until the token should expire.
                              If not given, the configured default will be used.
        @return  the encoded JWT token
        """
        if not self._gen:
            raise ConfigurationException("No token generator is configured")
        return self._gen.generate(self.id, self, lifetime)

    def set_token(self, lifetime=None):
        """
        create a JWT token (using :py:meth:`create_token`) and set it as an
        attribute of this credentials object
        :param int lifetime:  the time in seconds until the token should expire.
                              If not given, the configured default will be used.
        """
        if not self.is_authenticated():
            raise RuntimeError("Credentials token cannot be set for unauthenticated, %s user" %
                               self.id)
        self['token'] = self.create_token(lifetime)

