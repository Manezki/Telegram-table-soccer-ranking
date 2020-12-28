from bot.ranking import Ranking
from add_users_from_log import DummyBot
from telegram import Update, Message, Chat, ChatMember, User
from bot.commands import parse_dual_update, parse_game_update
import bot.commands
import sqlite3
import json
from os import path as op

RESET_SINGLES = ("""DROP TABLE IF EXISTS singles;""" +
                 """CREATE TABLE IF NOT EXISTS""" + """ singles(submitter_id int, rival_id int, """ +
                      """submitter_uname varchar(128), rival_uname varchar(128), """ +
                      """submitter_score TINYINT, rival_score TINYINT, timestamp INTEGER)""")

RESET_DUALS = ("""DROP TABLE IF EXISTS duals;""" +
               """CREATE TABLE IF NOT EXISTS""" + """ duals(submitter_id int, submitter_teammate int,""" +
                    """rival_1_id int, rival_2_id int, submitter_uname varchar(128), """ +
                    """submitter_teammate_uname varchar(128),""" +
                    """rival_1_uname varchar(128), rival_2_uname varchar(128),""" +
                    """ submitter_score TINYINT, rival_score TINYINT, timestamp INTEGER)""")


def read_updates_from_log(chat_name):
    history = []

    missed_posts = 0

    with open(op.join("message_history", chat_name + ".txt"), "r") as f:
        for line in f:
            line = line.replace("\'", "\"")
            line = line.replace("True", "true")
            line = line.replace("False", "false")
            try:
                d = json.loads(line)
                history.append(Update.de_json(d, DummyBot()))
            except json.decoder.JSONDecodeError:
                print(line)
                missed_posts += 1

    print("Had problem reading {0:.2}% of posts".format(missed_posts/(len(history)+missed_posts)))
    print("--------------------------------------")
    return history

if __name__ == "__main__":

    import sys
    # Script breaking bug below
    sys.exit(0)

    # TODO Update at runtime.
    # In form [a|-]123123123
    chat_name = ""
    chat_id = chat_name if chat_name[0] != "a" else "-" + chat_name[1:]
    chat_id = int(chat_id)

    db_fp = op.join(op.dirname(__file__), "persistent_storage", chat_name+".db")
    conn = sqlite3.connect(db_fp)
    c = conn.cursor()

    c.executescript(RESET_DUALS)
    c.executescript(RESET_SINGLES)
    c.execute("""UPDATE ratings SET mu = 25, sigma = 8.333333333333334""")
    
    R = Ranking(chat_id, conn=conn)
    R.rate_limit = 250

    accepted = []

    with open("accepted_matches.txt", "r") as f:
        for line in f:
            line = line.replace("\'", "\"")
            line = line.replace("True", "true")
            line = line.replace("False", "false")

            d = json.loads(line)
            accepted.append(Update.de_json(d, DummyBot()))

    bot.commands.RANKINGS[chat_id] = R

    # BUG Games should be imported in the order of the timestamps
    # DO NOT USE BEFORE ABOVE bug IS FIXED.
    # Singles
    for upd in accepted:
        if upd.message.text is None:
            continue
    
        try:
            sub, sub_score, riv, riv_score = parse_game_update(upd)
            ts = int(upd.message.date.timestamp())
            R.add_singles_match(sub, riv, sub_score, riv_score, ts)
        except ValueError as err:
            if "'/singles'" not in str(err):
                print("Encountered value error")
                print()
                print(err)
                print()
                print(upd)
                print()
        except AttributeError:
             print(upd)

    # Duals
    # TODO Finalize, requires fix for parse_dual_update
    for upd in accepted:
        if upd.message.text is None:
           continue
    
        try:
            sub, sub_tm, rival, rival_tm, sub_score, riv_score = parse_dual_update(upd)
            ts = int(upd.message.date.timestamp())
            #print(parse_dual_update(upd))
            R.add_dual_match(sub, sub_tm, rival, rival_tm, sub_score, riv_score, ts)
        except ValueError as err:
            if "'/dual'" not in str(err):
                print(err)
                print(upd)
                print()
        except AttributeError as err:
             print(upd)
             print(err)