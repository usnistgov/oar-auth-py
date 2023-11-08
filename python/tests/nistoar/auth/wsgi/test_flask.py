import os, json, pdb, sys, tempfile, re
import unittest as test
from pathlib import Path
from io import StringIO
from copy import deepcopy

from nistoar.auth.wsgi import flask as flaskapp
from nistoar.auth.wsgi import config
from nistoar.auth import creds
from nistoar.base.config import ConfigurationException

from flask import Response, Request, session
from werkzeug.datastructures import MultiDict
from onelogin.saml2.utils import OneLogin_Saml2_Utils as samlutils

testdir = Path(__file__).parents[0]
datadir = testdir / "data"
pydir   = testdir.parents[3]
basedir = pydir.parents[0]
etcdir  = basedir / "etc"

class TestSupportFunctions(test.TestCase):

    def test_convert_flask_request_for_saml(self):
        body = '{"a": "b"}'
        reqenv = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': "/goob/gurn/",
            'SCRIPT_NAME': "/sso",
            'QUERY_STRING': "format=csv",
            'CONTENT_TYPE': "application/json",
            'HTTP_ACCEPT': "*/*",
            'HTTP_HOST': "oar.org:4443",
            'wsgi.url_scheme': "https",
            'SERVER_NAME': "oar.org",
            'SERVER_PORT': 4443,
            'SERVER_PROTOCOL': "HTTP/1.1"
        }
        reqenv['wsgi.input'] = StringIO(json.dumps(body))
        freq = Request(reqenv)

        sreq = flaskapp.convert_flask_request_for_saml(freq)
        self.assertEqual(sreq['http_host'], "oar.org:4443")
        self.assertEqual(sreq['script_name'], "/sso")
        self.assertEqual(sreq['query_string'], b"format=csv")
        self.assertEqual(sreq['get_data'], MultiDict([("format", "csv")]))
        self.assertEqual(sreq['post_data'], MultiDict([]))
        self.assertEqual(sreq['https'], "on")
        self.assertNotIn('lowercase_urlencoding', sreq)

        sreq = flaskapp.convert_flask_request_for_saml(freq, 1)
        self.assertEqual(sreq['http_host'], "oar.org:4443")
        self.assertEqual(sreq['script_name'], "/sso")
        self.assertEqual(sreq['query_string'], b"format=csv")
        self.assertEqual(sreq['get_data'], MultiDict([("format", "csv")]))
        self.assertEqual(sreq['post_data'], MultiDict([]))
        self.assertEqual(sreq['https'], "on")
        self.assertIs(sreq['lowercase_urlencoding'], True)

        reqenv['wsgi.url_scheme'] = 'http'
        freq = Request(reqenv)
        sreq = flaskapp.convert_flask_request_for_saml(freq)
        self.assertEqual(sreq['http_host'], "oar.org:4443")
        self.assertEqual(sreq['script_name'], "/sso")
        self.assertEqual(sreq['query_string'], b"format=csv")
        self.assertEqual(sreq['get_data'], MultiDict([("format", "csv")]))
        self.assertEqual(sreq['post_data'], MultiDict([]))
        self.assertEqual(sreq['https'], "off")

        reqenv['HTTP_X_FORWARDED_PROTO'] = "https"
        freq = Request(reqenv)
        sreq = flaskapp.convert_flask_request_for_saml(freq, 1)
        self.assertEqual(sreq['http_host'], "oar.org:4443")
        self.assertEqual(sreq['script_name'], "/sso")
        self.assertEqual(sreq['query_string'], b"format=csv")
        self.assertEqual(sreq['get_data'], MultiDict([("format", "csv")]))
        self.assertEqual(sreq['post_data'], MultiDict([]))
        self.assertEqual(sreq['https'], "on")
        self.assertIs(sreq['lowercase_urlencoding'], True)

    def test_create_saml_sp(self):
        body = '{"a": "b"}'
        reqenv = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': "/goob/gurn/",
            'SCRIPT_NAME': "/sso",
            'QUERY_STRING': "format=csv",
            'CONTENT_TYPE': "application/json",
            'HTTP_ACCEPT': "*/*",
            'HTTP_HOST': "oar.org:4443",
            'wsgi.url_scheme': "https",
            'SERVER_NAME': "oar.org",
            'SERVER_PORT': 4443,
            'SERVER_PROTOCOL': "HTTP/1.1"
        }
        reqenv['wsgi.input'] = StringIO(json.dumps(body))
        freq = Request(reqenv)

        with open(datadir/"testsettings.json") as fd:
            cfg = json.load(fd)

        sysdir = config.find_auth_data_dir(cfg)

        auth = flaskapp.create_saml_sp(freq, cfg['saml'], sysdir)
        self.assertTrue(auth)
        self.assertIs(auth.get_settings().get_security_data()['wantNameId'], True)
        self.assertEqual(auth._request_data['script_name'], "/sso")
        self.assertEqual(auth.get_settings().get_cert_path(), os.path.join(sysdir, "certs")+"/")

        self.assertTrue(os.path.isdir(auth.get_settings().get_cert_path()))
        
    def test_checkAllowedUrls(self):
        allowed = [
            "https://localhost:4200/portal",
            "https://mdsdev.nist.gov/dmpui",
        ]
        
        self.assertTrue(flaskapp.checkAllowedUrls("https://localhost:4200/portal/", allowed))
        self.assertTrue(flaskapp.checkAllowedUrls("https://mdsdev.nist.gov/dmpui/new/", allowed))
        self.assertTrue(flaskapp.checkAllowedUrls("https://mdsdev.nist.gov/dmpui", allowed))
        self.assertTrue(not flaskapp.checkAllowedUrls("https://mdsdev.nist.gov/dapui", allowed))
        self.assertTrue(not flaskapp.checkAllowedUrls("https://mdsdev.nist.gov:9000/dmpui", allowed))

    def test_make_testuser_credentials(self):
        crds = flaskapp.make_testuser_credentials({})

        self.assertEqual(crds.id, "testuser")
        self.assertEqual(crds.given_name, "Test")
        self.assertEqual(crds.family_name, "User")
        self.assertEqual(crds.email, "test.user@example.com")
        self.assertEqual(crds['userOU'], "unknown")
        self.assertEqual(crds['displayName'], "TestUser")
        self.assertEqual(crds['role'], "not-set")
        self.assertEqual(crds['winId'], "testuser")
        self.assertIsNone(crds.expiration_time)
        self.assertEqual(crds.expiration, "(unset)")
        self.assertFalse(crds.expired())
        self.assertTrue(crds.is_authenticated())
        
        cfg = dict(id="gurn", given_name="Gurn", family_name="Cranston",
                   email="gurn.cranston@goob.io", display_name="Gurn Cranston")
        crds = flaskapp.make_testuser_credentials(cfg)
        
        self.assertEqual(crds.id, "gurn")
        self.assertEqual(crds.given_name, "Gurn")
        self.assertEqual(crds.family_name, "Cranston")
        self.assertEqual(crds.email, "gurn.cranston@goob.io")
        self.assertEqual(crds.email, "gurn.cranston@goob.io")
        self.assertEqual(crds['userOU'], "unknown")
        self.assertEqual(crds['displayName'], "Gurn Cranston")
        self.assertEqual(crds['role'], "not-set")
        self.assertEqual(crds['winId'], "gurn")
        self.assertIsNone(crds.expiration_time)
        self.assertEqual(crds.expiration, "(unset)")
        self.assertFalse(crds.expired())
        self.assertTrue(crds.is_authenticated())


            

class TestAppHandlers(test.TestCase):

    def setUp(self):
        self.cfg = {
            "debug": True,
            "goob": "gurn",
            "flask": {
                "SECRET_KEY": "YYY"
            },
            "jwt": {
                "secret": "XXX"
            }
        }
        self.app = flaskapp.create_app(self.cfg)

    def test_ctor(self):
        self.assertEqual(self.app.config['goob'], "gurn")
        self.assertEqual(self.app.config['SECRET_KEY'], "YYY")
        self.assertIn('jwt', self.app.config)
        self.assertEqual(self.app.config['jwt']['secret'], "XXX")
        self.assertIn('saml', self.app.config)
        self.assertIn('security', self.app.config['saml'])
        self.assertTrue(self.app.config['debug'])
        self.assertTrue(self.app.config['DEBUG'])
        self.assertTrue(creds.default_token_generator)
        self.assertEqual(creds.default_token_generator._secret, "XXX")

        with self.assertRaises(ConfigurationException):
            # missing jwt
            flaskapp.create_app({})

        flaskapp.create_app({"jwt": {"secret": "0"}})
        with self.assertRaises(ConfigurationException):
            flaskapp.create_app({"jwt": {"secret": "0"}, "allowed_service_endpoints": "n/a"})

    def test_handle_error(self):
        with self.app.app_context():
            resp = flaskapp._handle_error("Oops!")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.status, "400 BAD REQUEST")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(), {"Error": "Oops!", "ErrorCode": 400})

        with self.app.app_context():
            resp = flaskapp._handle_error("Oops!", 404)
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.status, "404 NOT FOUND")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(), {"Error": "Oops!", "ErrorCode": 404})

        with self.app.app_context():
            resp = flaskapp._handle_error("Ah!", 550, "On Leave")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 550)
            self.assertEqual(resp.status, "550 On Leave")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(),
                             {"Error": "Ah!", "ErrorCode": 550, "status": "On Leave"})

        with self.app.app_context():
            resp = flaskapp._handle_error("Ack!", 403, errors=["style", "substance"], color="red")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.status, "403 FORBIDDEN")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(), {"Error": "Ack!", "ErrorCode": 403,
                                               "errors": ["style", "substance"], "color": "red"})

    def test_handle_unauthenticated(self):
        with self.app.app_context():
            resp = flaskapp._handle_unauthenticated("No token")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 401)
            self.assertEqual(resp.status, "401 UNAUTHORIZED")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(), {"Error": "No token", "ErrorCode": 401})
        
        with self.app.app_context():
            resp = flaskapp._handle_unauthenticated("Ack!", "No token")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 401)
            self.assertEqual(resp.status, "401 No token")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(),
                             {"Error": "Ack!", "ErrorCode": 401, "status": "No token"})

    def test_handle_badinput(self):
        with self.app.app_context():
            resp = flaskapp._handle_badinput("No token")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.status, "400 BAD REQUEST")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(), {"Error": "No token", "ErrorCode": 400})
        
        with self.app.app_context():
            resp = flaskapp._handle_badinput("Ack!", "poor spelling")
            self.assertTrue(isinstance(resp, Response))
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.status, "400 poor spelling")
            self.assertEqual(resp.content_type, "application/json")
            self.assertEqual(resp.get_json(),
                             {"Error": "Ack!", "ErrorCode": 400, "status": "poor spelling"})
        
class TestAppRoutes(test.TestCase):
    
    cfg = None
    @classmethod
    def setUpClass(cls):
        with open(datadir/"testsettings.json") as fd:
            cls.cfg = json.load(fd)
        idp = cls.cfg['saml']['idp']
        cls.idp_sso = idp['singleSignOnService']['url']
        cls.idp_slo = idp['singleLogoutService']['url']

    def setUp(self):
        self.app = flaskapp.create_app(self.cfg)

    def test_disabled(self):
        cfg = deepcopy(self.cfg)
        cfg['disabled_saml_login'] = {
            "engaged": True,
            "testuser": { "id": "goober" }
        }
        self.app = flaskapp.create_app(cfg)

        self.assertTrue(self.app.config['disabled_saml_login']['engaged'])
        self.assertEqual(self.app.config['disabled_saml_login']['testuser']['id'],
                         "goober")

        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/auth/_logininfo", follow_redirects=False)
            self.assertEqual(resp.status_code, 200)  # logged in as goober
            self.assertEqual(resp.json['userId'], "goober")
            self.assertEqual(resp.json['userLastName'], "User")
            self.assertNotIn('token', resp.json)

            resp = cli.get("/sso/auth/_tokeninfo", follow_redirects=False)
            self.assertEqual(resp.status_code, 200)  # logged in as goober
            self.assertEqual(resp.json['userId'], "goober")
            self.assertEqual(resp.json['userLastName'], "User")
            self.assertIn('token', resp.json)

        

        
        

    def test_login(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/saml/login", follow_redirects=False)
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json['Error'], "missing redirectTo query parameter")

            resp = cli.get("/sso/saml/login?redirectTo=https://example.com/goober",
                           follow_redirects=False)
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.status, "400 Disallowed redirectTo")
            self.assertEqual(resp.json['Error'], "redirectTo URL is not recognized or not approved")

            resp = cli.get("/sso/saml/login?redirectTo=https://localhost/goober",
                           follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.location.startswith(self.idp_sso))

    def test_logout(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/saml/logout", follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.location.startswith(self.idp_slo))

    def test_sls(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/saml/sls")
            self.assertEqual(resp.status_code, 400)

    def test_acs(self):
        msg = """
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                      xmlns="urn:oasis:names:tc:SAML:2.0:assertion"
                      ID="b0730d21b628110d8b7e004005b13a2b" Version="2.0"/>
"""
        msg = samlutils.b64encode(msg.strip())
        with self.app.test_client(self.app) as cli:
            resp = cli.post("/sso/saml/acs",
                            data={"SAMLResponse": msg, "RelayState": "https://localhost/"})
            self.assertEqual(resp.status_code, 400)

    def test_get_user_info(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/auth/_logininfo")
            self.assertEqual(resp.status_code, 401)  # not logged in

    def test_token(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/auth/_tokeninfo")
            self.assertEqual(resp.status_code, 401)  # not logged in

    def test_metadata(self):
        with self.app.test_client(self.app) as cli:
            resp = cli.get("/sso/metadata/")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "text/xml")
            body = resp.get_data(as_text=True).strip()
            self.assertTrue(body.startswith("<"))
            self.assertIn('entityID="https://p932439.nist.gov:8000/sso/metadata/"', body)
        
            

            
        
                         
if __name__ == '__main__':
    test.main()
        
