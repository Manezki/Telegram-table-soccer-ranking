# BACKUP
# For each ranking
# For each Row on Ranking set delta for the database
# ** Change the table

import os
import sqlite3
import trueskill

dbs = os.path.join(os.path.dirname(__file__), "..", "persistent_storage")

trueskill_env = trueskill.TrueSkill(mu=25, sigma=8.333333333333334,
                                    beta=4.166666666666667,
                                    tau=0.08333333333333334, draw_probability=0.0)

ratings = {}


class Single():
    def __init__(self, p1, p2, p1_score, p2_score, timestamp):
        self.p1 = p1
        self.p2 = p2
        self.p1_score = p1_score
        self.p2_score = p2_score
        self.timestamp = timestamp

        self.p1_delta_mu = 0.
        self.p1_delta_sigma = 0.
        self.p2_delta_mu = 0.
        self.p2_delta_sigma = 0.

        self.table_name = "singles"


    def rate(self):
        p1r = ratings[self.p1]
        p2r = ratings[self.p2]
        
        (p1rn,), (p2rn,) = trueskill_env.rate([(p1r,), (p2r,)], ranks=self.rank())
        
        self.p1_delta_mu = p1rn.mu - p1r.mu
        self.p1_delta_sigma = p1rn.sigma - p1r.sigma

        self.p2_delta_mu = p2rn.mu - p2r.mu
        self.p2_delta_sigma = p2rn.sigma - p2r.sigma

        ratings[self.p1] = p1rn
        ratings[self.p2] = p2rn
        

    def deltas(self):
        return(
            self.p1_delta_mu,
            self.p1_delta_sigma,
            self.p2_delta_mu,
            self.p2_delta_sigma)


    def rank(self):
        if self.p1_score < self.p2_score:
            return [1, 0]
        else:
            return [0, 1]


    def __repr__(self):
        return "S @ " + str(self.timestamp)


class Dual():
    def __init__(self, t1p1, t1p2, t2p1, t2p2, t1_score, t2_score, timestamp):
        self.t1p1 = t1p1
        self.t1p2 = t1p2
        self.t2p1 = t2p1
        self.t2p2 = t2p2
        self.t1_score = t1_score
        self.t2_score = t2_score
        self.timestamp = timestamp

        self.t1p1_delta_mu = 0.
        self.t1p1_delta_sigma = 0.
        self.t1p2_delta_mu = 0.
        self.t1p2_delta_sigma = 0.

        self.t2p1_delta_mu = 0.
        self.t2p1_delta_sigma = 0.
        self.t2p2_delta_mu = 0.
        self.t2p2_delta_sigma = 0.

        self.table_name = "duals"


    def rate(self):
        p1r = ratings[self.t1p1]
        p2r = ratings[self.t1p2]
        p3r = ratings[self.t2p1]
        p4r = ratings[self.t2p2]
        
        (p1rn, p2rn), (p3rn, p4rn) = trueskill_env.rate([(p1r, p2r), (p3r, p4r)], ranks=self.rank())
        
        self.t1p1_delta_mu = p1rn.mu - p1r.mu
        self.t1p1_delta_sigma = p1rn.sigma - p1r.sigma

        self.t1p2_delta_mu = p2rn.mu - p2r.mu
        self.t1p2_delta_sigma = p2rn.sigma - p2r.sigma

        self.t2p1_delta_mu = p3rn.mu - p3r.mu
        self.t2p1_delta_sigma = p3rn.sigma - p3r.sigma

        self.t2p2_delta_mu = p4rn.mu - p4r.mu
        self.t2p2_delta_sigma = p4rn.sigma - p4r.sigma

        ratings[self.t1p1] = p1rn
        ratings[self.t1p2] = p2rn
        ratings[self.t2p1] = p3rn
        ratings[self.t2p2] = p4rn


    def deltas(self):
        return(
            self.t1p1_delta_mu,
            self.t1p1_delta_sigma,
            self.t1p2_delta_mu,
            self.t1p2_delta_sigma,
            self.t2p1_delta_mu,
            self.t2p1_delta_sigma,
            self.t2p2_delta_mu,
            self.t2p2_delta_sigma)

    def rank(self):
        if self.t1_score < self.t2_score:
            return [1, 0]
        else:
            return [0, 1]


    def __repr__(self):
        return "D @ " + str(self.timestamp)


# Perform for each ranking
for ranking_db in os.listdir(dbs):
    print("Processing ranking for chat: {}".format(ranking_db))

    conn = sqlite3.connect(os.path.join(dbs, ranking_db))
    c = conn.cursor()

    for user in c.execute("SELECT uid, uname FROM known_users"):
        ratings[user[0]] = trueskill_env.create_rating()

    games = []

    for single in c.execute("SELECT submitter_id, rival_id, submitter_score, rival_score, timestamp from singles"):
        games.append(Single(*single))

    for dual in c.execute("SELECT submitter_id, submitter_teammate, rival_1_id, rival_2_id, submitter_score, rival_score, timestamp from duals"):
        games.append(Dual(*dual))
    
    # Order to from oldest to newest
    games = sorted(games, key=lambda x: x.timestamp)

    # Update user ratings in chronological order
    for game in games:
        game.rate()

    # TODO Update the Single and Dual classes accordingly
    # **** Possibly move the rating updates to those classes, and store the deltas as done here.
    # TODO Update the Ranking methods accordingly

    try:
        c.execute("""ALTER TABLE singles ADD COLUMN submitter_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("""ALTER TABLE singles ADD COLUMN submitter_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("""ALTER TABLE singles ADD COLUMN rival_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("""ALTER TABLE singles ADD COLUMN rival_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN submitter_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN submitter_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN submitter_teammate_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN submitter_teammate_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN rival_1_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN rival_1_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN rival_2_delta_mu FLOAT""")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""ALTER TABLE duals ADD COLUMN rival_2_delta_sigma FLOAT""")
    except sqlite3.OperationalError:
        pass

    # Add the deltas for each game
    for game in games:
        if isinstance(game, Single):
            # At the moment uniquely identified by timestamp
            c.execute(("""UPDATE singles SET submitter_delta_mu=?, submitter_delta_sigma=?, """ +
                       """rival_delta_mu=?, rival_delta_sigma=? WHERE timestamp=?"""),
                      (game.p1_delta_mu, game.p1_delta_sigma, game.p2_delta_mu, game.p2_delta_sigma, game.timestamp))
            conn.commit()
        else:
            c.execute(("""UPDATE duals SET submitter_delta_mu=?, submitter_delta_sigma=?, """ +
                       """submitter_teammate_delta_mu=?, submitter_teammate_delta_sigma=?, """ +
                       """rival_1_delta_mu=?, rival_1_delta_sigma=?, """ +
                       """rival_2_delta_mu=?, rival_2_delta_sigma=? WHERE timestamp=?"""),
                      (game.t1p1_delta_mu, game.t1p1_delta_sigma, game.t1p2_delta_mu, game.t1p2_delta_sigma,
                       game.t2p1_delta_mu, game.t2p1_delta_sigma, game.t2p2_delta_mu, game.t2p2_delta_sigma,
                       game.timestamp))
            conn.commit()

    # Update user ratings
    for user, rating in ratings.items():
        c.execute("UPDATE ratings SET mu=?, sigma=? WHERE uid=?",
                  (rating.mu, rating.sigma, user))
        conn.commit()
