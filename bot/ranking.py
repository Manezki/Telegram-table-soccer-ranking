import logging
import sqlite3
import trueskill
import os
import datetime
from collections import deque, defaultdict

try:
    from queries import queries
except ModuleNotFoundError:
    from .queries import queries

try:
    from match import Match, Duals, Singles
except ModuleNotFoundError:
    from .match import Match, Duals, Singles

try:
    from player import Player
except ModuleNotFoundError:
    from .player import Player


class UnacceptedMatch(Exception):
    pass

class UnacceptedPlayer(Exception):
    pass

class RateLimitExceeded(Exception):
    pass

class DuplicateMatch(Exception):
    pass


class Ranking():
    # TODO Default to hidden home directory?
    DB_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "persistent_storage")

    def __init__(self, chat_id, conn=None, db_dir=None):
        # TODO Keep a rating snap-shot in database, to allow rollbacks.
        # TODO Script to recalculate the rankings from matches.

        self.chat_id = chat_id
        self.db_dir = db_dir

        if db_dir is None:
            # Default
            self.db_dir = Ranking.DB_DEFAULT
        elif not os.path.isdir(self.db_dir):
            logging.log(logging.WARNING, "db_dir was not a directory, defaulting to {}".format(Ranking.DB_DEFAULT))
            self.db_dir = Ranking.DB_DEFAULT

        # TODO No need to keep all of the games in memory, keep current ranking in memory
        self.singles = []
        self.duals = []

        self.known_users = {}
        self.user_to_id = {}

        self.ratings = {}
        self.trueskill_env = trueskill.TrueSkill(mu=25, sigma=8.333333333333334,
                                                 beta=4.166666666666667,
                                                 tau=0.08333333333333334, draw_probability=0.0)
        # TODO Include leaderboard to be kept in memory

        self.rate_limits = {}
        self.rate_limit = 5

        if conn is None:

            cid = int(self.chat_id)
            str_chat = str(cid)

            db_name = str_chat if str_chat[0] != "-" else "a" + str_chat[1:]

            db_fp = os.path.join(self.db_dir, db_name + ".db")
            self.__conn = sqlite3.connect(db_fp)
        else:
            self.__conn = conn

        self.__c = self.__conn.cursor()

        self._load_from_db()


    def _load_from_db(self):
        """
        Reconstruct the ranking object from a database.

        Args:
            None

        Returns:
            None
        """
        try:
            users = self.__c.execute("SELECT * FROM known_users")
            users = self.__c.fetchall()
            for user in users:
                try:
                    self._add_user(int(user[0]), user[1].lower())
                except AttributeError:
                    self._add_user(int(user[0]), None)
        except sqlite3.OperationalError as err:
            logging.log(logging.WARNING, msg="Problem when reading information from DB: {}. This should be expected for new chats".format(err))
            # TODO Add timestamp to the users.
            self.__c.execute(queries.CREATE_KNOWN_USERS)


        try:
            # User, mu, sigma
            ratings = self.__c.execute("SELECT * FROM ratings")
            ratings = self.__c.fetchall()
            for rating in ratings:
                self.ratings[int(rating[0])] = self.trueskill_env.create_rating(mu=rating[1],
                                                                                sigma=rating[2])
        except sqlite3.OperationalError as err:
            logging.log(logging.WARNING, msg="Problem when reading information from DB: {}. This should be expected for new chats".format(err))
            self.__c.execute(queries.CREATE_RATINGS)

        # Requires ratings
        try:
            matches = self.__c.execute("SELECT * FROM singles")
            matches = self.__c.fetchall()
            for match in matches:
                sub = (match[0], match[2])
                riv = (match[1], match[3])
                ts = int(match[6])
                M = Singles(submitter=sub, rival=riv, submitter_score=match[4], rival_score=match[5],
                            timestamp=ts)

                self.singles.append(M)

        except sqlite3.OperationalError as err:
            logging.log(logging.WARNING, msg="Problem when reading information from DB: {}. This should be expected for new chats".format(err))
            self.__c.execute(queries.CREATE_SINGLES)

        # Requires ratings
        try:
            duals = self.__c.execute("SELECT * FROM duals")
            duals = self.__c.fetchall()
            for dual in duals:
                sub_1 = (dual[0], dual[4])
                sub_2 = (dual[1], dual[5])
                riv_1 = (dual[2], dual[6])
                riv_2 = (dual[3], dual[7])
                sub_score = int(dual[8])
                riv_score = int(dual[9])
                ts = int(dual[10])
                D = Duals(submitter=sub_1, submitter_teammate=sub_2, rival=riv_1,
                          rival_teammate=riv_2, submitter_score=sub_score, rival_score=riv_score,
                          timestamp=ts)
                
                self.duals.append(D)

        except sqlite3.OperationalError as err:
            logging.log(logging.WARNING, msg="Problem when reading information from DB: {}. This should be expected for new chats".format(err))
            self.__c.execute(queries.CREATE_DUALS)


    def _add_user(self, userid, username, add_to_db=False):
        """
        Add user to the ranking object.

        Args:
            userid (int): User's telegram ID
            username (string): Users's telegram username
            add_to_db (Boolean): Should the user be added to the database.
                                 Defaults to False, should be True when adding new user.

        Returns:
            None
        """

        # Casting is checked in "add_user"
        userid = int(userid)

        # Totally new user
        if userid not in self.known_users:
            # Double check there does not exist Rating for user
            if userid in self.ratings:
                # TODO: What to do in such a case?
                logging.log(logging.WARNING, "Player '{}' was allready in the ratings, but was identified as new user.".format(userid))
            try:
                player = Player(int(userid), self.trueskill_env.mu, self.trueskill_env.sigma, username=username)
                if add_to_db:
                    self.__c.execute(queries.INSERT_KNOWN_USERS, (player.userid, player.username))
                    self.__c.execute(queries.INSERT_RATINGS,
                                     (player.userid, player.rating_mean, player.rating_std))
                    self.__conn.commit()
                # Run DB update before, so states remain same
                self.known_users[player.userid] = player
                self.ratings[player.userid] = self.trueskill_env.create_rating()
                logging.log(logging.INFO, "Added user uid: {}, username: {} to chat: {}".format(userid, username, self.chat_id))
            except sqlite3.OperationalError as err:
                logging.log(logging.ERROR, "Inserting a new user's ranking to DB failed. {}".format(err))
                raise UnacceptedPlayer("Unable to add new player {},".format(username) +
                                       " with Telegram ID {} to ranking".format(userid))


        # Discrepancy between the stored username and the one from arguments
        if self.known_users[userid].username != username:
            try:
                old = self.known_users[userid]
                new = Player(userid, old.rating_mean, old.rating_std, username=username)
                if add_to_db:
                    self.__c.execute(queries.INSERT_KNOWN_USERS, (new.userid, new.username))
                    self.__conn.commit()
                self.known_users[userid] = new
                logging.log(logging.INFO, "Updated username for uid: {}. old username: {} -> new username: {}".format(
                    new.userid, old.username, new.username))
            except sqlite3.OperationalError as err:
                logging.log(logging.ERROR, "Inserting an updated (uid, uname) to DB failed. {}".format(err))
                raise UnacceptedPlayer("Unable to update player's username {},".format(new.username) +
                                       " with Telegram ID {} to ranking".format(new.userid))


    def _update_user_rating(self, uid, rating):
        """
        Update users ranking in the object, as well as in the database.

        Args:
            uid (int): User's telegram ID
            rating (trueskill_env.rating_group): Users's new rating object

        Returns:
            Boolean: Was update performed succesfully.
        """

        # TODO Should use two ratings. Singles and Doubles
        try:
            self.__c.execute(queries.UPDATE_RATINGS,
                             (rating.mu, rating.sigma, uid))
            self.__conn.commit()
            self.ratings[uid] = rating
            return True
        except sqlite3.OperationalError:
            logging.log(logging.ERROR, "Error while trying to update rating into the database")
            return False
        except sqlite3.ProgrammingError:
            logging.log(logging.ERROR, "Trying to update rating although database connection is closed")
            return False


    def _update_rating(self, match):
        """
        Update ratings for all the players in a match.

        Args:
            match (Singles or Duals): Describing a full match.

        Returns:
            None
        """
        # TODO should have a rollback with __add_single_match & __add_dual_match
        # Check relies on the ordering of the check, as isinstance checks also subclass.
        if isinstance(match, Duals):
            # UIDs
            t1p1 = int(match.submitter[0])
            t1p2 = int(match.submitter_teammate[0])
            t2p1 = int(match.rival[0])
            t2p2 = int(match.rival_teammate[0])

            try:
                t1p1r = self.ratings[t1p1]
                t1p2r = self.ratings[t1p2]
                t2p1r = self.ratings[t2p1]
                t2p2r = self.ratings[t2p2]
            except KeyError as err:
                logging.log(logging.ERROR, "Player of a match did not have a rating assigned. {}".format(err))
                raise UnacceptedPlayer("Player of a match '{}, {} - {}, {}' did not have a rating.".format(match.submitter[1], match.submitter_teammate[1], match.rival[1], match.rival_teammate[1]))

            (t1p1rn, t1p2rn), (t2p1rn, t2p2rn) = self.trueskill_env.rate([(t1p1r, t1p2r),
                                                                      (t2p1r, t2p2r)],
                                                                     ranks=match.rank())

            self._update_user_rating(t1p1, t1p1rn)
            self._update_user_rating(t1p2, t1p2rn)
            self._update_user_rating(t2p1, t2p1rn)
            self._update_user_rating(t2p2, t2p2rn)


            logging.log(logging.INFO, "Ratings updated, as a result of match: {}".format(match))
            logging.log(logging.INFO, "Player {0} went from {1:.4} to {2:.4}.".format(match.submitter[1],
                                                                                    self.trueskill_env.expose(t1p1r),
                                                                                    self.trueskill_env.expose(t1p1rn)))
            logging.log(logging.INFO,
                        "Player {0} went from {1:.4} to {2:.4}.".format(match.submitter_teammate[1],
                                                                      self.trueskill_env.expose(t1p2r),
                                                                      self.trueskill_env.expose(t1p2rn)))
            logging.log(logging.INFO, "Player {0} went from {1:.4} to {2:.4}.".format(match.rival[1],
                                                                                    self.trueskill_env.expose(t2p1r),
                                                                                    self.trueskill_env.expose(t2p1rn)))
            logging.log(logging.INFO,
                        "Player {0} went from {1:.4} to {2:.4}.".format(match.rival_teammate[1],
                                                                      self.trueskill_env.expose(t2p2r),
                                                                      self.trueskill_env.expose(t2p2rn)))

        elif isinstance(match, Singles):
            # UIDs
            t_1 = int(match.submitter[0])
            t_2 = int(match.rival[0])

            try:
                r_1 = self.ratings[t_1]
                r_2 = self.ratings[t_2]
            except KeyError as e:
                logging.log(logging.ERROR, "Player of a match did not have a rating assigned. {}".format(e))
                raise UnacceptedPlayer("Player of a match '{}".format(match.submitter[1]) +
                                       " - {}' did not have a rating.".format(match.rival[1]))

            (r_1n,), (r_2n,) = self.trueskill_env.rate([(r_1,), (r_2,)], ranks=match.rank())
            self._update_user_rating(t_1, r_1n)
            self._update_user_rating(t_2, r_2n)

            logging.log(logging.INFO, "Ratings updated, as a result of match: {}".format(match))
            logging.log(logging.INFO, "Player {0} went from {1:.4} to {2:.4}.".format(match.submitter[1],
                                                                                    self.trueskill_env.expose(r_1),
                                                                                    self.trueskill_env.expose(r_1n)))
            logging.log(logging.INFO, "Player {0} went from {1:.4} to {2:.4}.".format(match.rival[1],
                                                                                    self.trueskill_env.expose(r_2),
                                                                                    self.trueskill_env.expose(r_2n)))

        else:
            logging.log(logging.ERROR, "Faulthy call of ranking._update_rating : Type of an 'match' argument was not Match or Dual.")
            raise TypeError("'match' was not type of Match or Dual")


    def _add_singles_match(self, singles, add_to_db=False):
        """
        Add 1-v-1 match into the database as well as Ranking-objects storage.

        Args:
            singles (Singles): Describing a full 1-v-1 match.
            add_to_db (Boolean): Should the match be added to the database.
                                 Defaults to False, should be True when adding new match.

        Returns:
            None
        """
        if not isinstance(singles, Singles):
            logging.log(logging.ERROR, "Faulthy call of ranking._add_singles_match : Type of an 'match' argument was not Match.")
            raise TypeError("match was not type of Match")

        if not self.check_under_limit(singles.submitter[0]):
            logging.log(logging.ERROR, "User {} exceeded his ratelimit.".format(singles.submitter))
            raise RateLimitExceeded("Too many submissions in the last hour")

        # Check that game in question was not in DB
        try:
            similar_games_in_db = self.__c.execute("SELECT * FROM singles WHERE submitter_id=? AND rival_id=? AND submitter_uname=? AND rival_uname=? AND submitter_score=? AND rival_score=? AND timestamp=?",
                                                (singles.submitter[0], singles.rival[0], singles.submitter[1],
                                                    singles.rival[1], singles.submitter_score, singles.rival_score,
                                                    singles.timestamp))
            similar_games_in_db = self.__c.fetchall()
            for r in similar_games_in_db:
                # If iterator was not empty, raise UnacceptedMatch
                raise DuplicateMatch("Submission was already registered.")
        except sqlite3.OperationalError:
            logging.log(logging.ERROR, "Error while trying to check database for duplicate entries.")
            raise UnacceptedMatch("The match was not saved, because could not check for duplicates.")
        except sqlite3.ProgrammingError:
            logging.log(logging.ERROR, "Trying to check for duplicate matches although database connection is closed")
            raise UnacceptedMatch("The match was not saved, because could not check for duplicates.")


        if add_to_db:
            try:
                deltas = singles.deltas(self.ratings, self.trueskill_env)

                p1 = deltas[singles.submitter[0]]
                p2 = deltas[singles.rival[0]]

                self.__c.execute(queries.INSERT_SINGLES, 
                                 (singles.submitter[0], singles.rival[0], singles.submitter[1],
                                  singles.rival[1], singles.submitter_score, singles.rival_score,
                                  singles.timestamp, p1[0], p1[1], p2[0], p2[1]))
                self.__conn.commit()
            except sqlite3.OperationalError as err:
                logging.log(logging.ERROR, "Inserting a match to the database failed. Match was as follows: {}".format(singles))
                logging.log(logging.ERROR, "SQL-error: {}".format(err))
                raise UnacceptedMatch("The match was not saved.")
            except sqlite3.ProgrammingError:
                logging.log(logging.ERROR, "Trying to insert match results although database connection is closed")
                raise UnacceptedMatch("The match was not saved.")

        self.singles.append(singles)

        self._update_rating(singles)

        # Mark the submission to rate-limit
        cur = singles.timestamp
        if singles.submitter[0] not in self.rate_limits:
            self.rate_limits[singles.submitter[0]] = deque()
        self.rate_limits[singles.submitter[0]].append(cur)


    def _add_duals_match(self, dual, add_to_db=False):
        """
        Add 2-v-2 match into the database as well as Ranking-objects storage.

        Args:
            dual (Duals): Describing a full 2-v-2 match.
            add_to_db (Boolean): Should the match be added to the database.
            Defaults to False, should be True when adding new match.

        Returns:
            None
        """
        if not isinstance(dual, Duals):
            logging.log(logging.ERROR, "Faulthy call of ranking._add_duals_match : Type of an 'dual' argument was not Dual.")
            raise TypeError("'dual' was not type of Dual")

        if not self.check_under_limit(dual.submitter[0]):
            logging.log(logging.ERROR, "User {} exceeded his ratelimit.".format(dual.submitter))
            raise RateLimitExceeded("Too many submissions in the last hour")

        # Check that game in question was not in DB
        similar_games_in_db = self.__c.execute("SELECT * FROM duals WHERE submitter_id=? AND submitter_teammate=? AND rival_1_id=? AND rival_2_id=? AND submitter_uname=? AND submitter_teammate_uname=? AND rival_1_uname=? AND rival_2_uname=? AND submitter_score=? AND rival_score=? AND timestamp=?",
                                               (dual.submitter[0], dual.submitter_teammate[0],
                                                dual.rival[0], dual.rival_teammate[0],
                                                dual.submitter[1], dual.submitter_teammate[1],
                                                dual.rival[1], dual.rival_teammate[1],
                                                dual.submitter_score, dual.rival_score,
                                                dual.timestamp))
        similar_games_in_db = self.__c.fetchall()
        for r in similar_games_in_db:
            # If iterator was not empty, raise UnacceptedMatch
            raise DuplicateMatch("Submission was already registered.")

        if add_to_db:
            try:
                deltas = dual.deltas(self.ratings, self.trueskill_env)

                p1 = deltas[dual.submitter[0]]
                p2 = deltas[dual.submitter_teammate[0]]
                p3 = deltas[dual.rival[0]]
                p4 = deltas[dual.rival_teammate[0]]

                self.__c.execute(queries.INSERT_DUALS,
                                 (dual.submitter[0], dual.submitter_teammate[0],
                                  dual.rival[0], dual.rival_teammate[0],
                                  dual.submitter[1], dual.submitter_teammate[1],
                                  dual.rival[1], dual.rival_teammate[1],
                                  dual.submitter_score, dual.rival_score,
                                  dual.timestamp, p1[0], p1[1], p2[0], p2[1],
                                  p3[0], p3[1], p4[0], p4[1]))
                self.__conn.commit()
            except sqlite3.OperationalError:
                logging.log(logging.ERROR, "Inserting a dual to the database failed. Dual was as follows: {}".format(dual))
                raise UnacceptedMatch("The duals match was not saved.")
        
        self.duals.append(dual)

        self._update_rating(dual)
        
        # Mark the submission to rate-limit
        cur = dual.timestamp
        if dual.submitter[0] not in self.rate_limits:
            self.rate_limits[dual.submitter[0]] = deque()
        self.rate_limits[dual.submitter[0]].append(cur)


    @staticmethod
    def load_ranking(chat_id, db_dir=None):
        """
        Reconstruct the ranking object from a database for a given chat0.

        Args:
            chat_id (int): Unique ID of the chat for which the Ranking should be created.
            db_dir (path): Directory path where the databases should be contained. 

        Returns:
            ranking (Ranking): Ranking of the players in the chat identified by chat_id
        """

        if db_dir is None:
            db_dir = Ranking.DB_DEFAULT

        str_chat = str(chat_id)
        db_name = str_chat if str_chat[0] != "-" else "a" + str_chat[1:]

        # This should be the first entry point for the database connection.
        # Should be a safe location to create the database directory if it's missing
        if not os.path.exists(db_dir):
            os.mkdir(db_dir)

        file_path = os.path.join(db_dir, db_name + ".db")

        if os.path.exists(file_path):
            print(file_path)
            con = sqlite3.connect(file_path)
            rank = Ranking(int(chat_id), conn=con, db_dir=db_dir)
            return rank

        logging.log(logging.WARNING, "Tried to load a Ranking for chat that does not have" +
                    " persistent storage. FP: {}".format(file_path))
        raise FileNotFoundError(file_path)


    def get_user_greeting(self, username):
        """
        Generates a chat specific greeting for new users.

        Args:
            username (string) : username of the user to be greeted.

        Returns:
            string: Message ready to be sent to the user.
        """

        msg = ("""Hello {}!\n""".format(username) +
               """This channel contains a ranking, and I'm happy to welcome you to join in on the games.""" +
               """The games that you play should be reported here by one of the players. By doing so, we """ +
               """get an idea what should be your standing in the leaderboards.\n\n""" +
               """For 1-on-1 matches we have following command:\n"""+
               """'/singles @opponent_username your-score opponent-score'\n""" +
               """and for 2-on-2's:\n""" +
               """'/duals @teammate_username @opponent_1_username @opponent_2_username your-score opponent-score'\n\n""" +
               """Good luck and happy gaming!""")
        
        return msg


    def add_user(self, userid, username=None):
        """
        Add a new player to the ranking.

        Args:
            userid (int): Unique and consistent ID for the user.
            username (string): Username to be associated with the player.
                               Defaults to None (no name).

        Returns:
            None
        """
        # BUG KeyError if user does not exist
        try:
            userid = int(userid)
        except ValueError:
            logging.log(logging.ERROR, "Adding a user with id that is not castable to INT. User {}".format(userid))
            raise UnacceptedPlayer("Userid was not acceptable form. (Castable to Int)")

        if username is None:
            self._add_user(userid, username, add_to_db=True)
        else:
            self._add_user(userid, username.lower(), add_to_db=True)


    def add_singles_match(self, submitter, rival, submitter_score, rival_score, timestamp):
        """
        Add a new 1-v-1 match to the ranking.

        Args:
            submitter (int): User ID of the sumbitter.
            rival (int): User ID of the rival.
            submitter_score (int): Score of the submitter.
            rival_score (int): Score of the rival.
            timestamp (int): POSIX timestamp of the game submission.

        Returns:
            Singles: Full description of the 1-v-1 match.
        """
        match = Singles(submitter, rival, submitter_score, rival_score, timestamp)

        self._add_singles_match(match, add_to_db=True)

        return match


    def add_dual_match(self, submitter, submitter_teammate, rival_1, rival_2, submitter_score, rival_score, timestamp):
        """
        Add a new 2-v-2 match to the ranking.

        Args:
            submitter (int): User ID of the sumbitter.
            submitter_teammate (int): User ID of the sumbitter's teammate.
            rival_1 (int): User ID of the rival player 1.
            rival_2 (int): User ID of the rival player 2.
            submitter_score (int): Score of the submitting team.
            rival_score (int): Score of the rivaling team.
            timestamp (int): POSIX timestamp of the game submission.

        Returns:
            Duals: Full description of the 2-v-2 match.
        """
        dual = Duals(submitter, submitter_teammate, rival_1, rival_2, submitter_score, rival_score, timestamp)

        self._add_duals_match(dual, add_to_db=True)

        return dual


    def get_user(self, userid=None, username=None):
        """
        Find user's ID and username based on EITHER userid or username.

        Args:
            userid (int): User ID of the user. Defaults to None.
            username (string): Username of the user. Defaults to None.

        Returns:
            tuple: (User ID, Username)
        """
        assert not (userid is None and username is None), "UserId and UserName cannot be None"

        if userid is not None:
            try:
                # Should be contained in dictionary
                player = self.known_users[userid]
                return (player.userid, player.username)
            except KeyError:
                logging.log(logging.ERROR, "Unknown userid was requested from Ranking")
                return (userid, None)

        # Username must be not None
        else:
            try:
                # TODO: This loop could definitely use a refactoring
                # Username should be contained in dictionary
                for uid, player in self.known_users.items():
                    if username.lower() == player.username:
                        break
                # Not sure if this cleaner, but follows JeffPaines/beautiful_idiomatic_python convention
                else:
                    return (None, username.lower())
                return (uid, player.username)

            except IndexError:
                logging.log(logging.ERROR, "Unknown username was requested from Ranking")
                return (None, username)


    def check_under_limit(self, userid):
        """
        Check that user has not made more submissions than stated by self.rate_limit.

        Args:
            Userid (int) : Of the player in question.

        Returns:
            Boolean : True if player is still UNDER the ratelimit.
        """

        # Submitter always will have userid
        if userid not in self.rate_limits:
            return True

        cur = int(datetime.datetime.now().timestamp())
        # Clean ratelimits while checking
        subs = self.rate_limits[userid]

        # Check which of the previous submissions are older than 1 hour.
        for _ in range(len(subs)):
            hist = subs.popleft()
            t_d = cur - hist
            if t_d < datetime.timedelta(hours=1).total_seconds():
                subs.append(hist)

        # Should have less than rate_limit submissions from the last hours, as we are
        # going to add one
        if len(self.rate_limits[userid]) < self.rate_limit:
            return True

        return False


    def get_leaderboard(self):
        """
        Ordered list of users with their ratings. Users are ordered by their skill-level.

        Args:
            None

        Returns:
            list : Ordered list of (user, rating) tuples.
        """
        leaderboard = sorted(self.ratings.items(), key=lambda x: self.trueskill_env.expose(x[1]),
                             reverse=True)
        return [(user, rating) for user, rating in leaderboard]

    
    def matches_per_user(self):
        """
        Return amount of matches that has been recorded for each player.

        Args:
            None

        Returns:
            Dict(uid -> int) : Amount of matches recorded for user-id.
        """
        ret = defaultdict(int)

        for m in self.singles:
            sub, riv = (m.submitter[0], m.rival[0])
            
            ret[sub] += 1
            ret[riv] += 1
        
        for d in self.duals:
            sub, sub_t = (d.submitter[0], d.submitter_teammate[0])
            riv, riv_t = (d.rival[0], d.rival_teammate[0])

            ret[sub] += 1
            ret[sub_t] += 1
            ret[riv] += 1
            ret[riv_t] += 1

        return ret


    def __del__(self):
        self.__conn.close()
