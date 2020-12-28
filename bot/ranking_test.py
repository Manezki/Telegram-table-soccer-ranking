import unittest
import sqlite3
from ranking import Ranking, Match, RateLimitExceeded
from queries import queries
import datetime
import logging

logging.basicConfig(level=logging.INFO)


# Drop the 'create table' from the queries.CREATE_*
RESET_USERS = ("""DROP TABLE IF EXISTS known_users; """ +
               """CREATE TABLE IF NOT EXISTS""" + queries.CREATE_KNOWN_USERS[12:])

RESET_SINGLES = ("""DROP TABLE IF EXISTS singles;""" +
                 """CREATE TABLE IF NOT EXISTS""" + queries.CREATE_SINGLES[12:])

RESET_DUALS = ("""DROP TABLE IF EXISTS duals;""" +
               """CREATE TABLE IF NOT EXISTS""" + queries.CREATE_DUALS[12:])

RESET_RATINGS = ("""DROP TABLE IF EXISTS ratings;""" +
                 """CREATE TABLE IF NOT EXISTS""" + queries.CREATE_RATINGS[12:])

# TODO Tests should not write databases to disk

class TestRanking(Ranking):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.c = self.conn.cursor()
        Ranking.__init__(self, 1, conn=self.conn)
    
    def reset(self):
        self.c.executescript(RESET_USERS)
        self.c.executescript(RESET_SINGLES)
        self.c.executescript(RESET_RATINGS)
        self.c.executescript(RESET_DUALS)

        self.singles = []
        self.duals = []
        self.known_users = {}
        self.rate_limits = {}



USERS = [(123, "player_a"), (234, "player_b"), (345, "player_c"), (456, "player_d")]
# TODO Add submissions fit for the deltas.
SINGLES = [(123, 234, "player_a", "player_b", 10, 0, 1, 0., 0., 0., 0.)]
DUALS = [(123, 234, 345, 456, "player_a", "player_b", "player_c", "player_d", 10, 0, 1, 0., 0., 0., 0., 0., 0., 0., 0.)]
RATINGS = [(123, 25, 5), (234, 27, 5), (345, 26, 5), (456, 28, 5)]

TABLES = ["singles", "known_users", "duals", "ratings"]

class TestRankingCreation(unittest.TestCase):
    def setUp(self):
        self.R = TestRanking()


    def testCreateTablesIfNotExist(self):

        for table in TABLES:
            try:
                self.R.c.execute("SELECT * FROM {}".format(table))
            except Exception:
                self.fail("{} did not exist after creation".format(table))


    def testAddUsersFromDB(self):
        self.R.reset()

        self.R.c.executemany(queries.INSERT_KNOWN_USERS, USERS)

        R = Ranking(1, conn=self.R.conn)

        self.assertTrue(all([user[0] in R.known_users for user in USERS]), "All of the users were not added from DB")


    def testAddSinglesFromDB(self):
        self.R.reset()
        self.R.c.executemany(queries.INSERT_SINGLES, SINGLES)
        self.R.c.executemany(queries.INSERT_RATINGS, RATINGS)

        R = Ranking(1, self.R.conn)

        submitters = [user[0] for user in USERS]
        self.assertTrue(all(match.submitter[0] in submitters for match in R.singles), "All of the matches were not added from the DB")


    def testAddDualsFromDB(self):
        self.R.c.executemany(queries.INSERT_DUALS, DUALS)
        self.R.c.executemany(queries.INSERT_RATINGS, RATINGS)

        R = Ranking(1, self.R.conn)

        submitters = [user[0] for user in USERS]
        self.assertTrue(all(dual.submitter[0] in submitters for dual in R.duals), "All of the duals were not added from the DB")


    def tearDown(self):
        self.R.conn.close()


class TestRankingMethods(unittest.TestCase):
    def setUp(self):
        self.R = TestRanking()


    def testAddUsersWithIDWithoutUname(self):
        self.R.reset()

        for user in USERS:
            self.R.add_user(userid=user[0])

        db = self.R.c.execute("SELECT * FROM known_users")

        self.assertTrue(all([u[0] in [uid for uid, uname in USERS] for u in db]))


    def testAddUsersWithUnameAndID(self):
        self.R.reset()

        for user in USERS:
            self.R.add_user(userid=user[0], username=user[1])

        db = self.R.c.execute("SELECT * FROM known_users")

        self.assertTrue(all([u in USERS for u in db]))


    def testUpdateUname(self):
        self.R.reset()

        for user in USERS:
            self.R.add_user(userid=user[0])

        self.R.add_user(userid=USERS[0][0], username=USERS[0][1])

        db = self.R.c.execute("SELECT * FROM known_users")

        self.assertTrue(USERS[0] in db.fetchall())

    
    def testRateLimit(self):
        self.R.reset()

        self.R.rate_limit = 2

        user1 = USERS[0]
        user2 = USERS[1]
        self.R.add_user(userid=user1[0], username=user1[1])
        self.R.add_user(userid=user2[0], username=user2[1])

        cur = int(datetime.datetime.now().timestamp())

        for i, _ in enumerate(range(2)):
            self.R.add_singles_match(user1, user2, 10, 3, cur + i)
        
        with self.assertRaises(RateLimitExceeded, msg="Should not allow user to exceed rate-limit."):
            self.R.add_singles_match(user1, user2, 10, 3, cur + 2)


    def testLeaderboardUpdateSingles(self):
        self.R.reset()

        user1 = USERS[0]
        user2 = USERS[1]

        self.R.add_user(userid=user1[0], username=user1[1])
        self.R.add_user(userid=user2[0], username=user2[1])
        self.R.add_singles_match(user1, user2, 10, 3, 0)

        board1 = self.R.get_leaderboard()

        self.assertTrue(board1[0][0] == user1[0])
        
        self.R.add_singles_match(user2, user1, 10, 3, 1)
        self.R.add_singles_match(user2, user1, 10, 3, 2)

        board2 = self.R.get_leaderboard()
        self.assertTrue(board2[0][0] == user2[0])


    def testLeaderboardUpdateDuals(self):
        self.R.reset()

        for user in USERS:
            self.R.add_user(userid=user[0], username=user[1])

        D = DUALS[0]
        p1 = (D[0], D[4])
        p2 = (D[1], D[5])
        p3 = (D[2], D[6])
        p4 = (D[3], D[7])

        # P1 & P2 win single match
        self.R.add_dual_match(p1, p2, p3, p4, 10, 0, 1)

        board1 = [uid for uid, _ in self.R.get_leaderboard()]
        

        self.assertTrue((p1[0] in board1[:2]) and (p2[0] in board1[:2]),
                        "Winning players should take the lead on a fresh leaderboard.")
        
        # P3 & P4 win two matches
        self.R.add_dual_match(p1, p2, p3, p4, 0, 10, 2)
        self.R.add_dual_match(p1, p2, p3, p4, 0, 10, 3)

        board2 = [uid for uid, _ in self.R.get_leaderboard()]
        

        self.assertFalse(all([board1[i] == board2[i] for i in range(len(board1))]),
                         "Rankings should have changed after lost matches.")
        
        self.assertTrue((p3[0] in board2[:2]) and (p4[0] in board2[:2]),
                        "Players with most wins against each others, should end up on top of the leaderboard.")


    def testMatchesPerUser(self):
        self.R.reset()
        self.R.c.executemany(queries.INSERT_KNOWN_USERS, USERS)
        self.R.c.executemany(queries.INSERT_RATINGS, RATINGS)

        # Use a fresh Ranking to load the information from DB
        R = Ranking(1, conn=self.R.conn)

        for dual in DUALS:
            R.add_dual_match((dual[0], dual[4]), (dual[1], dual[5]), (dual[2], dual[6]), (dual[3], dual[7]),
                             dual[8], dual[9], dual[10])
        
        try:
            R.matches_per_user()
        except Exception:
            self.fail("Calculating the number of matches per user should not throw error.")


    def tearDown(self):
        self.R.conn.close()


class TestRatingConsistency(unittest.TestCase):
    def setUp(self):
        self.R = TestRanking()


    def testUserRatingNotUpdatedWithSeveredDatabaseConnection(self):
        for user in USERS:
            self.R.add_user(userid=user[0], username=user[1])

        database_rating = self.R.c.execute("SELECT * FROM ratings WHERE uid=?", (int(USERS[0][0]),))
        # Collect to memory
        database_rating = [res for res in database_rating]

        # Severe database connection
        self.R.conn.close()

        rating_1 = self.R.trueskill_env.create_rating()
        rating_2 = self.R.trueskill_env.create_rating()

        (upd_1,), (_,) = self.R.trueskill_env.rate([(rating_1,), (rating_2,)], ranks=[1, 0])

        # Will fail because severed connection
        self.R._update_user_rating(USERS[0][0], upd_1)

        ranking_rating = self.R.ratings[USERS[0][0]]

        for _, mean, sigma in database_rating:
            try:
                self.assertAlmostEqual(ranking_rating.mu, mean, places=2, msg="The rating should not be updated if it" +
                                       " cannot be updated on the database AND memory.")
                self.assertAlmostEqual(ranking_rating.sigma, sigma, places=2, msg="The rating should not be updated if it" +
                                       " cannot be updated on the database AND memory.")
            finally:
                self.R = TestRanking()


    def tearDown(self):
        self.R.conn.close()


if __name__ == '__main__':
    unittest.main()
