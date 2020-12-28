
class queries():
    """
    Wrap queries in a class, so they have shared prefic in relative import.
    """

    CREATE_KNOWN_USERS = """CREATE TABLE known_users(uid int, uname varchar(128))"""
    CREATE_RATINGS = """CREATE TABLE ratings(uid int, mu float, sigma float)"""
    CREATE_SINGLES = ("""CREATE TABLE singles(submitter_id int, rival_id int, """ +
                      """submitter_uname varchar(128), rival_uname varchar(128), """ +
                      """submitter_score TINYINT, rival_score TINYINT, timestamp INTEGER, """ +
                      """submitter_delta_mu FLOAT, submitter_delta_sigma FLOAT, """ +
                      """rival_delta_mu FLOAT, rival_delta_sigma FLOAT)""")
    CREATE_DUALS = ("""CREATE TABLE duals(submitter_id int, submitter_teammate int,""" +
                    """rival_1_id int, rival_2_id int, submitter_uname varchar(128), """ +
                    """submitter_teammate_uname varchar(128),""" +
                    """rival_1_uname varchar(128), rival_2_uname varchar(128),""" +
                    """ submitter_score TINYINT, rival_score TINYINT, timestamp INTEGER, """ +
                    """submitter_delta_mu FLOAT, submitter_delta_sigma FLOAT, """+
                    """submitter_teammate_delta_mu FLOAT, submitter_teammate_delta_sigma FLOAT, """ +
                    """rival_1_delta_mu FLOAT, rival_1_delta_sigma FLOAT, """+
                    """rival_2_delta_mu FLOAT, rival_2_delta_sigma FLOAT)""")

    INSERT_KNOWN_USERS = """INSERT INTO known_users VALUES(?, ?)"""
    INSERT_RATINGS = """INSERT INTO ratings VALUES(?, ?, ?)"""
    INSERT_SINGLES = """INSERT INTO singles VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    INSERT_DUALS = """INSERT INTO duals VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    UPDATE_RATINGS = """UPDATE ratings SET mu = ? , sigma = ? WHERE uid = ?"""