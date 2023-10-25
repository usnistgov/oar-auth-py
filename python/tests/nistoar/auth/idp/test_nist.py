import unittest as test

from nistoar.auth.idp import nist as idp


class Test_NIST_IDP(test.TestCase):

    def setUp(self):
        self.samlatts = {
            idp.ATTR_NAME.ID:     ["jerk"],
            idp.ATTR_NAME.EMAIL:  ["jerk@nist.gov"],
            idp.ATTR_NAME.GIVEN:  ["Gurn"],
            idp.ATTR_NAME.FAMILY: ["Cranston"],
            idp.ATTR_NAME.OU:     ["MTV"],
        }

    def test_make_credentials(self):
        creds = idp.make_credentials(self.samlatts)

        self.assertIsNotNone(creds)
        self.assertEqual(creds.id, "jerk")
        self.assertEqual(creds.email, "jerk@nist.gov")
        self.assertEqual(creds.given_name, "Gurn")
        self.assertEqual(creds.family_name, "Cranston")
        self.assertEqual(creds['userOU'], "MTV")


        
        
        
                         
if __name__ == '__main__':
    test.main()
        
