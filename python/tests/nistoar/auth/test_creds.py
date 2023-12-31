import os, json, pdb, time, jwt
import unittest as test
from collections import OrderedDict
from io import StringIO

from nistoar.auth import creds
from nistoar.base.config import ConfigurationException

class Test_FallbackDict(test.TestCase):

    def test_keys(self):
        map = creds._FallbackDict()
        self.assertEqual(list(map.keys()), [])

        map = creds._FallbackDict({"a": 1, "b": 2})
        self.assertEqual(list(map.keys()), ["a", "b"])
        self.assertEqual(list(map._defs.keys()), ["a", "b"])
        self.assertEqual(list(map.data.keys()), [])

        map['c'] = 3
        map['a'] = "goob"

        self.assertEqual(list(map.keys()), ["a", "b", "c"])
        del map['a']
        del map['c']
        self.assertEqual(list(map.keys()), ["a", "b"])

    def test_get(self):
        map = creds._FallbackDict()
        self.assertIsNone(map.get('a'))
        self.assertEqual(map.get('a', "hey"), "hey")

        map = creds._FallbackDict({"a": 1, "b": 2})
        self.assertEqual(map.get('a'), 1)
        self.assertEqual(map['a'], 1)
        self.assertEqual(map['b'], 2)
        self.assertEqual(map.get('a', "hey"), "hey")

        map['c'] = 3
        map['a'] = "goob"
        self.assertEqual(map.get('a'), "goob")
        self.assertEqual(map.get('c'), 3)
        self.assertEqual(map.get('c', "gurn"), 3)
        self.assertEqual(map['a'], "goob")
        self.assertEqual(map['b'], 2)
        self.assertEqual(map.get('a', "hey"), "goob")

        del map['a']
        del map['c']
        self.assertEqual(map.get('a'), 1)
        self.assertIsNone(map.get('c'))
        self.assertEqual(map.get('c', "gurn"), "gurn")
        self.assertEqual(map['a'], 1)
        self.assertEqual(map['b'], 2)
        self.assertEqual(map.get('a', "hey"), "hey")
        with self.assertRaises(KeyError):
            map['c']


class TestJWTGenerator(test.TestCase):

    def setUp(self):
        creds.default_token_generator = None
        self.cfg = {
            "secret": "hush!"
        }

        self.gen = creds.JWTGenerator(self.cfg)

    def test_ctor(self):
        self.assertEqual(self.gen._secret, self.cfg['secret'])
        self.assertEqual(self.gen.lifetime, 3600)

        self.cfg['lifetime'] = 600
        self.gen = creds.JWTGenerator(self.cfg)
        self.assertEqual(self.gen._secret, self.cfg['secret'])
        self.assertEqual(self.gen.lifetime, 600)

        with self.assertRaises(ConfigurationException):
            creds.JWTGenerator({})
        with self.assertRaises(ConfigurationException):
            creds.JWTGenerator({"lifetime": "tomorrow", "secret": "XX"})

    def test_generate(self):
        due = time.time() + 3600
        tok = self.gen.generate("me", {"name": "Bud", "color": "green"})
        self.assertIsNotNone(tok)

        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "me")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)
        self.assertEqual(data['name'], "Bud")
        self.assertEqual(data['color'], "green")

        due = time.time() + 600
        tok = self.gen.generate("you",
                                {"sub": "me", "phase": "Bud", "color": "blue"},
                                600)
        self.assertIsNotNone(tok)

        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "you")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)
        self.assertEqual(data['phase'], "Bud")
        self.assertEqual(data['color'], "blue")

    def test_create_default_token_generator(self):
        self.assertIsNone(creds.default_token_generator)
        creds.create_default_token_generator(self.cfg)
        self.assertTrue(isinstance(creds.default_token_generator,
                                   creds.JWTGenerator))

class TestCredentials(test.TestCase):

    def setUp(self):
        self.cfg = {
            "secret": "hush!"
        }
        creds.create_default_token_generator(self.cfg)

        self.atts = {
            "userId": "you",
            "userName": "Gurn",
            "userLastName": "Cranston",
            "userOU": "Ministry of Funny Walks"
        }

    def test_ctor(self):
        self.crd = creds.Credentials("me", self.atts)

        self.assertEqual(self.crd.id, "me")
        self.assertEqual(self.crd['userId'], "me")
        self.assertEqual(self.crd.email, "not@set")
        self.assertEqual(self.crd['userEmail'], "not@set")
        self.assertEqual(self.crd.given_name, "Gurn")
        self.assertEqual(self.crd['userName'], "Gurn")
        self.assertEqual(self.crd.family_name, "Cranston")
        self.assertEqual(self.crd['userLastName'], "Cranston")
        self.assertEqual(self.crd['userOU'], "Ministry of Funny Walks")
        self.assertIsNone(self.crd.get('token'))

        self.assertIsNotNone(self.crd._gen)

        self.crd = creds.Credentials("me", self.atts, None,
                                     creds.default_token_generator)
        self.assertIsNotNone(self.crd._gen)

        self.crd = creds.Credentials()
        self.assertEqual(self.crd.id, creds.UNAUTHENTICATED)
        self.assertEqual(creds.UNAUTHENTICATED, "anonymous")

    def test_expiration(self):
        self.crd = creds.Credentials("Gurn")
        self.assertIsNone(self.crd.expiration_time)
        self.assertTrue(isinstance(self.crd.expiration, str))
        self.assertEqual(self.crd.expiration, "(unset)");
        self.assertFalse(self.crd.expired())

        self.crd = creds.Credentials("Gurn", {}, time.time()+3600)
        self.assertIsNotNone(self.crd.expiration_time)
        self.assertTrue(isinstance(self.crd.expiration, str))
        self.assertNotEqual(self.crd.expiration, "(unset)");
        self.assertFalse(self.crd.expired())

        self.crd = creds.Credentials("Gurn", {}, time.time()-3600)
        self.assertIsNotNone(self.crd.expiration_time)
        self.assertTrue(isinstance(self.crd.expiration, str))
        self.assertNotEqual(self.crd.expiration, "(unset)");
        self.assertTrue(self.crd.expired())

    def test_keys(self):
        self.crd = creds.Credentials("me", self.atts)
        self.assertEqual(list(self.crd.keys()),
                         ['userId', 'userEmail', 'userName', 'userLastName',
                          'userOU'])

        self.crd['goob'] = 'gurn'
        self.crd['token'] = 'XXXX'
        self.assertEqual(list(self.crd.keys()),
                         ['userId', 'userEmail', 'userName', 'userLastName',
                          'userOU', 'goob', 'token'])

    def test_create_token(self):
        self.crd = creds.Credentials("me", self.atts)

        due = time.time() + 3600
        tok = self.crd.create_token()
        self.assertIsNotNone(tok)

        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "me")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)
        self.assertEqual(data['userEmail'], "not@set")
        self.assertEqual(data['userName'], "Gurn")
        self.assertEqual(data['userLastName'], "Cranston")
        self.assertEqual(data['userOU'], "Ministry of Funny Walks")

        due = time.time() + 600
        tok = self.crd.create_token(600)
        self.assertIsNotNone(tok)

        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "me")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)
        self.assertEqual(data['userEmail'], "not@set")
        self.assertEqual(data['userName'], "Gurn")
        self.assertEqual(data['userLastName'], "Cranston")
        self.assertEqual(data['userOU'], "Ministry of Funny Walks")

    def test_set_token(self):
        self.crd = creds.Credentials("me", self.atts)
        self.assertIsNone(self.crd.get('token'))

        due = time.time() + 3600
        self.crd.set_token()
        tok = self.crd['token']
        self.assertIsNotNone(tok)
        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "me")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)

        due = time.time() + 600
        self.crd.set_token(600)
        tok = self.crd['token']
        self.assertIsNotNone(tok)
        data = jwt.decode(tok, self.cfg['secret'], algorithms="HS256")
        self.assertEqual(data['sub'], "me")
        self.assertGreater(data['exp'], due-1)
        self.assertLess(data['exp'], due+5)

    def test_json(self):
        self.crd = creds.Credentials("me", self.atts)

        data = json.loads(self.crd.to_json(), object_pairs_hook=OrderedDict)
        self.assertEqual(list(data.keys()), ['userDetails'])
        self.assertEqual(list(data['userDetails'].keys()),
                         ['userId', 'userEmail', 'userName', 'userLastName',
                          'userOU'])
        self.assertEqual(data['userDetails']['userId'], 'me')
        self.assertEqual(data['userDetails']['userEmail'], 'not@set')

        fd = StringIO()
        self.crd.write_json(fd)
        data = json.loads(fd.getvalue())
        self.assertEqual(list(data.keys()), ['userDetails'])
        self.assertEqual(list(data['userDetails'].keys()),
                         ['userId', 'userEmail', 'userName', 'userLastName',
                          'userOU'])
        self.assertEqual(data['userDetails']['userId'], 'me')
        self.assertEqual(data['userDetails']['userEmail'], 'not@set')

        self.crd['goob'] = "gurn"
        self.crd.set_token()
        
        data = json.loads(self.crd.to_json(), object_pairs_hook=OrderedDict)
        self.assertEqual(list(data.keys()), ['userDetails', 'token'])
        self.assertEqual(list(data['userDetails'].keys()),
                         ['userId', 'userEmail', 'userName', 'userLastName',
                          'userOU', 'goob'])
        self.assertEqual(data['userDetails']['userId'], 'me')
        self.assertEqual(data['userDetails']['userEmail'], 'not@set')
        self.assertEqual(data['token'], self.crd['token'])
        
        crd = creds.Credentials.from_json_dict(data)
        self.assertEqual(crd.id, self.crd.id)
        self.assertEqual(crd.email, self.crd.email)
        self.assertEqual(crd['userOU'], self.crd['userOU'])
        self.assertEqual(crd['token'], self.crd['token'])

        
        
        
                         
if __name__ == '__main__':
    test.main()
        
