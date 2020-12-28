import logging

class Match():
    """
    A class to represent a Match.

    Args:
        submitter (tuple(int, str)) : user-id, username pair
        rival (tuple(int, str)) : user-id, username pair
        submitter_score (int) : Goals made by the submitters team. Range 0, 10
        rival_score (int) : Goals made by the opposing team. Range 0, 10
        timestamp (int) : UNIX timestamp (seconds since 1970), when was the match submitted.
    """
    def __init__(self, submitter_score, rival_score, timestamp):
        if not isinstance(submitter_score, int):
            assert str.isdigit(submitter_score), "Submitter_score needs to be int"
        if not isinstance(rival_score, int):
            assert str.isdigit(rival_score), "Rival_score needs to be int"

        # UID, UNAME
        self.submitter_score = int(submitter_score)
        self.rival_score = int(rival_score)

        # When was the game submitted.
        self.timestamp = timestamp


    def rank(self):
        """
        Which team won the match.

        Args:
            None
        
        Returns:
            list: Ordered list of rankings. Winner being 0, Loser being 1
        """
        # Needed for Trueskill calculation
        if self.submitter_score < self.rival_score:
            return [1, 0]
        else:
            return [0, 1]


    def deltas(self, ratings, trueskill_env):
        """
        Calculate the rating deltas that would result for the match.

        Args:
            ratings (dict) : Keys should be user-ids, and values Trueskill ratings objects.

        Returns:
            dict : Keys as user-id, values tuples (delta_mu, delta_sigma).
        """
        raise NotImplementedError

    @staticmethod
    def validate_score(submitter_score, rival_score):
        """
        Verify that the gamescore is within acceptable range:

        Args:
            submitter_score (int): Team 1 score.
            rival_score (int): Team 2 score.

        Returns:
            None
        """

        if not (str.isdigit(str(submitter_score)) and str.isdigit(str(rival_score))):
            logging.log(logging.WARNING, "Game scores were not digits")
            raise ValueError("Game scores were not digits.")

        if not (int(submitter_score) >= 0 and int(submitter_score) <= 10):
            logging.log(logging.WARNING, "{} out of supported range".format(int(submitter_score)))
            raise ValueError("Your score is out of supported range.")

        if not (int(rival_score) >= 0 and int(rival_score) <= 10):
            logging.log(logging.WARNING, "{} out of supported range".format(int(rival_score)))
            raise ValueError("Rival score is out of supported range.")

        if int(submitter_score) == int(rival_score):
            raise ValueError("Draws are not possible.")

        if int(submitter_score) != 10 and int(rival_score) != 10:
            raise ValueError("One player should get 10 points.")


class Duals(Match):
    def __init__(self, submitter, submitter_teammate,
                 rival, rival_teammate,
                 submitter_score, rival_score, timestamp):
        Match.__init__(self, submitter_score, rival_score, timestamp)
        self.submitter = submitter
        self.submitter_teammate = submitter_teammate
        self.rival = rival
        self.rival_teammate = rival_teammate


    def __str__(self):
        return ("Duals match: ({} + {})".format(self.submitter, self.submitter_teammate) +
                " {} - {} ({} ".format(self.submitter_score, self.rival_score, self.rival) +
                "+ {})".format(self.rival_teammate))


    def deltas(self, ratings, trueskill_env):
        """
        Calculate the rating deltas that would result for the match.

        Args:
            ratings (dict) : Keys should be user-ids, and values Trueskill ratings objects.
        
        Returns:
            dict : Keys as user-id, values tuples (delta_mu, delta_sigma).
        """
        p1r = ratings[self.submitter[0]]
        p2r = ratings[self.submitter_teammate[0]]
        p3r = ratings[self.rival[0]]
        p4r = ratings[self.rival_teammate[0]]
        
        (p1rn, p2rn), (p3rn, p4rn) = trueskill_env.rate([(p1r, p2r), (p3r, p4r)], ranks=self.rank())

        res = {}

        t1p1_delta_mu = p1rn.mu - p1r.mu
        t1p1_delta_sigma = p1rn.sigma - p1r.sigma
        res[self.submitter[0]] = (t1p1_delta_mu, t1p1_delta_sigma)

        t1p2_delta_mu = p2rn.mu - p2r.mu
        t1p2_delta_sigma = p2rn.sigma - p2r.sigma
        res[self.submitter_teammate[0]] = (t1p2_delta_mu, t1p2_delta_sigma)

        t2p1_delta_mu = p3rn.mu - p3r.mu
        t2p1_delta_sigma = p3rn.sigma - p3r.sigma
        res[self.rival[0]] = (t2p1_delta_mu, t2p1_delta_sigma)

        t2p2_delta_mu = p4rn.mu - p4r.mu
        t2p2_delta_sigma = p4rn.sigma - p4r.sigma
        res[self.rival_teammate[0]] = (t2p2_delta_mu, t2p2_delta_sigma)

        return res


class Singles(Match):
    def __init__(self, submitter, rival, submitter_score, rival_score, timestamp):
        Match.__init__(self, submitter_score, rival_score, timestamp)
        self.submitter = submitter
        self.rival = rival

    def __str__(self):
        return ("Singles match: {} {}".format(self.submitter, self.submitter_score) +
                " - {} {}".format(self.rival_score, self.rival))

    def deltas(self, ratings, trueskill_env):
        """
        Calculate the rating deltas that would result for the match.

        Args:
            ratings (dict) : Keys should be user-ids, and values Trueskill ratings objects.
        
        Returns:
            dict : Keys as user-id, values tuples (delta_mu, delta_sigma).
        """
        p1r = ratings[self.submitter[0]]
        p2r = ratings[self.rival[0]]
        
        (p1rn,), (p2rn,) = trueskill_env.rate([(p1r,), (p2r,)], ranks=self.rank())

        res = {}

        p1_delta_mu = p1rn.mu - p1r.mu
        p1_delta_sigma = p1rn.sigma - p1r.sigma
        res[self.submitter[0]] = (p1_delta_mu, p1_delta_sigma)

        p2_delta_mu = p2rn.mu - p2r.mu
        p2_delta_sigma = p2rn.sigma - p2r.sigma
        res[self.rival[0]] = (p2_delta_mu, p2_delta_sigma)

        return res