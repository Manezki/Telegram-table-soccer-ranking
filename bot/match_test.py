import unittest
from match import Match


class TestMatchScore(unittest.TestCase):


    def testScoreNotDigit(self):

        with self.assertRaises(ValueError, msg="The validation should not accept scores other than digits"):
            Match.validate_score("abc", None)


    def testScoreIsDraw(self):

        with self.assertRaises(ValueError, msg="The validation should not accept draws"):
            Match.validate_score(10, 10)


    def testScoreHasNoWinner(self):

        with self.assertRaises(ValueError, msg="The validation should require one person to get 10 points"):
            Match.validate_score(9, 5)
    

    def testScoreIsNegative(self):

        with self.assertRaises(ValueError, msg="The validation should not accept negative scores"):
            Match.validate_score(-5, 10)


    def testScoreIsCorrect(self):

        try:
            Match.validate_score(10, 5)
        except ValueError:
            self.fail(msg="The validation should accept proper scores")
