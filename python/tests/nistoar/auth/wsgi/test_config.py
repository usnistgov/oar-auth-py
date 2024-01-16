import os, json, pdb, sys, tempfile
import unittest as test
from pathlib import Path

from nistoar.auth.wsgi import config
from nistoar.base.config import ConfigurationException

testdir = Path(__file__).parents[0]
pydir   = testdir.parents[3]
basedir = pydir.parents[0]
etcdir  = basedir / "etc"

class TestConfig(test.TestCase):

    def test_assumptions(self):
        self.assertEqual(pydir.name, "python")

    def test_find_auth_data_dir(self):
        cfg = {
            # setting to an arbitrary existing directory
            "data_dir":  os.path.join(os.path.dirname(__file__))
        }
        self.assertEqual(config.find_auth_data_dir(cfg), cfg['data_dir'])
        root = basedir
        if os.environ.get('OAR_HOME') and \
           os.path.exists(os.environ.get('OAR_HOME')):
            root = Path(os.environ.get('OAR_HOME'))

        cfg['data_dir'] = "/does/not/exist"
        with self.assertRaises(ConfigurationException):
            config.find_auth_data_dir(cfg)

        # test find etc relative to build
        self.assertEqual(config.find_auth_data_dir({}), str(root/"etc"/"authservice"))
        self.assertEqual(config.def_auth_data_dir, str(root/"etc"/"authservice"))

        # test use of OAR_HOME env var
        with tempfile.TemporaryDirectory(prefix="_test_auth") as tmpdirname:
            tmpdir = Path(tmpdirname)
            datadir = tmpdir/"etc"/"authservice"
            datadir.mkdir(parents=True)
            os.environ['OAR_HOME'] = tmpdirname
            try:
                self.assertEqual(config.find_auth_data_dir(), str(datadir))
            finally:
                del os.environ['OAR_HOME']

    def test_expand_config(self):
        # just load default data
        cfg = config.expand_config()
        self.assertEqual(cfg['logfile'], "authserver.log")
        self.assertIn('saml', cfg)
        self.assertTrue(cfg['saml']['strict'])

        # provide defaults directly
        cfg = config.expand_config(def_config={"goob": "gurn"})
        self.assertIn("goob", cfg)
        self.assertNotIn('saml', cfg)
        self.assertNotIn('logfile', cfg)

        with self.assertRaises(TypeError):
            cfg = config.expand_config(def_config={"goob", "gurn"})

        # test merge
        cfg = config.expand_config({"goob": "gurn", "hardware": "hank"},
                                   {"goob": "cranstron", "uh": "clem" })
        self.assertEqual(cfg, {"goob": "gurn", "hardware": "hank", "uh": "clem" })

        # test merge with defaults from file
        with tempfile.TemporaryDirectory(prefix="_test_auth") as tmpdirname:
            defcfgfile = Path(tmpdirname) / "defcfg.json"
            with open(defcfgfile, 'w') as fd:
                json.dump({"goob": "cranstron", "uh": "clem" }, fd)
            cfg = config.expand_config({"goob": "gurn", "hardware": "hank"}, defcfgfile)
            self.assertEqual(cfg, {"goob": "gurn", "hardware": "hank", "uh": "clem" })

        # test merge with defaults from sys file
        cfg = config.expand_config({"goob": "gurn",
                                    "saml": { "strict": False, "glub": "blub",
                                              "security": { "hardware": "hank"}}})
        self.assertIs(cfg['saml']['strict'], False)
        self.assertEqual(cfg['goob'], "gurn")
        self.assertIn('security', cfg['saml'])
        self.assertEqual(cfg['saml']['glub'], "blub")
        self.assertEqual(cfg['saml']['security']['hardware'], "hank")
        self.assertIs(cfg['saml']['security']['nameIdEncrypted'], False)



        

        
        
        
        
        
                         
if __name__ == '__main__':
    test.main()
        


            
        
