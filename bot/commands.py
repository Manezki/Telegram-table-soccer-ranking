import logging
try:
    from ranking import Ranking, UnacceptedMatch, UnacceptedPlayer, DuplicateMatch, RateLimitExceeded
except ModuleNotFoundError:
    from .ranking import Ranking, UnacceptedMatch, UnacceptedPlayer, DuplicateMatch, RateLimitExceeded

import functools
import os
from os import path as op
from telegram import Update
from telegram.error import NetworkError

# Hold rankings for multiple chats
# TODO The rankings should not be hold in this file. Some higher level structure should be posed
RANKINGS = {}

PRINT_UPDATES = False
__ERROR_BARRIER = False

# TODO Allow users to remove their own submission.
# TODO Move player-information to class.
# TODO Inform unsuccesful submission in private chat

def user_tracker(func):
    """
    Collect user-information form each update, and saves it to the corresponding chat rating.
    Users are collected from: Message-sender, and new-chat-member updates.
    Returns empty list, if no ranking has been started for the chat.

    Args:
        bot (Telegram Bot) : Bot that collected the update.
        update (Telegram Update) : Update to be parsed.
        skip_write (boolean, optional) : Defaults to False. Should the update be logged.

    Returns:
        list : UserIDs of the found users.
    """

    @functools.wraps(func)
    def wrapper_user_tracker(*args, **kwargs):

        # Release __ERROR_BARRIER as we got proper update
        global __ERROR_BARRIER
        __ERROR_BARRIER = False

        # Try gathering needed arguments
        try:
            update = args[1]
        except IndexError:
            logging.warning("Tracker-wrapper was used with a function with no 'update' as second arg.")
            return func(*args, **kwargs)
        
        if not isinstance(update, Update):
            logging.warning("Tracer-wrapper had second argumnet with some other type than Update.")
            return func(*args, **kwargs)

        if update.message.chat.type == "private":
            # Skip tracking
            return func(*args, **kwargs)

        if PRINT_UPDATES:
            print_upd(update)

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username

        if not __check_ranking_exists(chat_id):
            logging.log(logging.INFO, "Tracker tried to store information of users from a chat with no ranking.")
            # TODO Collect user information before the ranking is created
            return func(*args, **kwargs)

        # Add sending user
        if not update.effective_user.is_bot:
            try:
                # POSSIBLE BUG Users should not be added to the ranking if they are there already
                RANKINGS[chat_id].add_user(user_id, username)
            except UnacceptedPlayer:
                logging.log(logging.WARNING,
                            "Tracker was not able to add user information to the ranking." +
                            " uid:{} username:{}".format(user_id, username))

        for user in update.message.new_chat_members:
            try:
                RANKINGS[chat_id].add_user(user.id, user.username)
            except UnacceptedPlayer:
                logging.log(logging.WARNING,
                            "Tracker was not able to add user information to the ranking." +
                            " uid:{} username:{}".format(user.id, user.username))

            try:
                bot = args[0]

                if user.username is None:
                    uname = user.first_name
                else:
                    uname = user.username

                msg = bot.send_message(chat_id=chat_id, text=RANKINGS[chat_id].get_user_greeting(uname))
                bot_log(msg)
            except (TypeError, IndexError) as err:
                logging.log(logging.ERROR, "Following error was raised when greeting an user. {}".format(err))

        return func(*args, **kwargs)

    return wrapper_user_tracker


def __lazy_load_ranking(chat_id):
    chat_id = int(chat_id)
    R = Ranking.load_ranking(chat_id)
    RANKINGS[chat_id] = R
    return


def __check_ranking_exists(chat_id):
    return chat_id in RANKINGS


def _drop_mentions(update):
    """
    Replaces the non-standard format mentions in Telegram message's text with 'MESSAGE' tokens.

    Args:
        update (Telegram Update): Update to be converted.

    Returns:
        string: Update text with mentions replaced with MENTION-tokens.
    """

    entities = [(ent.offset, ent.length) for ent in update.message.parse_entities().keys()]

    if not entities:
        return update.message.text

    entities = sorted(entities, key=lambda x: x[0])
    replaced = update.message.text

    offset_change = 0

    for ent in entities:
        offset = ent[0]+offset_change

        before_replace = replaced[:offset]
        to_be_replaced = replaced[offset:offset+ent[1]]
        after_replace = replaced[offset+ent[1]:]

        offset_change += len("MENTION") - len(to_be_replaced)
        replaced = "".join([before_replace, "MENTION", after_replace])

    return replaced


def check_score(submitter, rival):
    """
    Verify that the gamescore is within acceptable range:

    Args:
        submitter (int): Team 1 score.
        rival (int): Team 2 score.

    Returns:
        None
    """
    if not (str.isdigit(submitter) and str.isdigit(rival)):
        logging.log(logging.WARNING, "Game scores were not digits")
        raise ValueError("Game scores were not digits.")

    if not (int(submitter) >= 0 and int(submitter) <= 10):
        logging.log(logging.WARNING, "{} out of supported range".format(int(submitter)))
        raise ValueError("Your score is out of supported range.")

    if not (int(rival) >= 0 and int(rival) <= 10):
        logging.log(logging.WARNING, "{} out of supported range".format(int(rival)))
        raise ValueError("Rival score is out of supported range.")

    if int(submitter) == int(rival):
        raise ValueError("Draws are not possible.")


def parse_game_update(update):
    """
    Extracts the information from a standard format message. This information is supposed to
    describe a game between 2 players with a result. Expected format:
    '/singles [OPPONENT] [SUBMITTING_PLAYERS_SCORE] [OPPONENT_SCORE]'

    Args:
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        tuple: (submitter_telegram_id, submitter_score, rival_telegram_id, rival_score)
    """

    if update.message.text[:8].lower() != "/singles":
        logging.log(logging.INFO, "Game parse called from wrong command. Message start: {}".format(update.message.text[:8]))
        raise ValueError("Game did not start with '/singles'")

    # Bots should not see messages from other bots, but better be sure
    if update.effective_user.is_bot:
        raise ValueError("Game entries cannot be created by bots")

    entities = update.message.entities

    if len(entities) < 2:
        raise ValueError("Game did not contain opponent.")

    if len(entities) != 2:
        raise ValueError("Game contained some unexpected information.")

    # There's a difference between MENTION and TEXT_MENTION. Seems TEXT_MENTION is for cases,
    # when user has no Username available
    # TODO Text_mentioned users should be added as users.
    if entities[1].type not in ["mention", "text_mention"]:
        raise ValueError("Game did not contain opponent.")

    # TODO Check order of the arguments
    sp = _drop_mentions(update).split()

    if len(sp) < 4:
        raise ValueError("Game did not contain enough arguments.")

    # Check the value range, type and sense
    check_score(sp[2], sp[3])

    submitter = RANKINGS[update.effective_chat.id].get_user(
        userid=update.effective_user.id, username=update.effective_user.username)
    submitter_score = int(sp[2])

    # TODO Mentions of users without username CAN BE two part. e.g. first-name, last-name
    mentions = sorted([(ent.offset, ent.user, decoded_name) for ent, decoded_name in update.message.parse_entities().items()], key=lambda x: x[0])

    # The opponent decoded name
    if mentions[1][2][-3:] == "bot":
        raise ValueError("Cannot submit games against Telegram bots.")

    # The opponent decoded name
    try:
        if mentions[1][2][1:].lower() == update.effective_user.username.lower():
            raise ValueError("Cannot submit games against itself")
    except AttributeError:
        if mentions[1][2][1:].lower() == update.effective_user.first_name.lower():
            raise ValueError("Cannot submit games against itself")

    # Text-mentions contain User-object with ID. Text-mentions are used when user has no username.
    # Normal mentions are used when user has a username, and no User-object is returned
    # in the Update.
    rival_user = mentions[1][1]
    if rival_user is None:
        rival = RANKINGS[update.effective_chat.id].get_user(username=mentions[1][2][1:])
        if rival[0] is None:
            logging.log(logging.WARNING, "Opponent was not recognized as a user. Opponent: {}".format(mentions[1][2][1:]))
            raise ValueError("Opponent was not recognized as a user. He has probably not interacted with the chat.")
    else:
        try:
            rival_id = int(rival_user.id)
        except AttributeError:
            logging.log(logging.WARNING, "Opponent was not recognized as a user. Opponent: {}".format(mentions[1][2][1:]))
            raise ValueError("Opponent was not recognized as a user.")

        try:
            rival_uname = rival_user.username.lower()
        except AttributeError:
            rival_uname = None

        rival = RANKINGS[update.effective_chat.id].get_user(userid=rival_id, username=rival_uname)

    rival_score = int(sp[3])

    return (submitter, submitter_score, rival, rival_score)


def parse_dual_update(update):
    """
    Extracts the information from a standard format message. This information is supposed to
    describe a game between 2 teams (2 players each) with a resulting score. Expected format:
    '/duals [TEAMMATE] [OPPONENT_1] [OPPONENT_2] [SUBMITTING_TEAM_SCORE] [RIVAL_TEAM_SCORE]'

    Args:
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        tuple: (submitter_telegram_id, teammate_telegram_id, rival_1_telegram_id,
                rival_2_telegram_id, submitting_team_score, rival_team_score)
    """
    if update.message.text[:6].lower() != "/duals":
        raise ValueError("Submission did not start with '/dual'")

    # Bots should not see messages from other bots, but better be sure
    if update.effective_user.is_bot:
        raise ValueError("Game entries cannot be created by bots")

    entities = update.message.entities

    if len(entities) < 4:
        raise ValueError("Game did not contain enough players.")

    if len(entities) != 4:
        raise ValueError("Game contained some unexpected information.")

    if entities[1].type != "mention":
        raise ValueError("Game did not contain teammate.")

    if entities[2].type not in  ["mention", "text_mention"] or entities[3].type not in  ["mention", "text_mention"]:
        raise ValueError("Game did not contain rival players.")

    # TODO Check order of the arguments

    sp = _drop_mentions(update).split()

    if len(sp) < 6:
        raise ValueError("Game did not contain enough arguments.")

    # Check the value range, type and sense
    check_score(sp[4], sp[5])

    submitter = RANKINGS[update.effective_chat.id].get_user(userid=update.effective_user.id, username=update.effective_user.username)
    submitter_score = int(sp[4])
    rival_score = int(sp[5])

    #mentions = [v[1:].lower() for k, v in update.message.parse_entities().items() if k.type == "mention"]
    mentions = [(ent.offset, ent.user, decoded_name) for ent, decoded_name in update.message.parse_entities().items()]
    mentions = sorted(mentions, key=lambda x: x[0])

    if any([mention[2][-3:] == "bot" for mention in mentions]):
        raise ValueError("Cannot submit games with players as Telegram bots.")

    players = []

    for mention in mentions[1:4]:
        # No user-field in mention.
        if mention[1] is None:
            rival = RANKINGS[update.effective_chat.id].get_user(username=mention[2][1:])
            if rival[0] is None:
                logging.log(logging.WARNING, "Opponent was not recognized as a user. Opponent: {}".format(mention[2][1:]))
                raise ValueError("Opponent {} was not recognized as a user. He has probably not interacted with the chat.".format(mention[2][1:]))
            else:
                players.append(rival)

        else:
            try:
                uid = int(mention[1].id)
            except AttributeError:
                raise ValueError("Mentioned player was not recognized as a telegram user")

            try:
                uname = mention[1].username.lower()
            except AttributeError:
                uname = None

            players.append(RANKINGS[update.effective_chat.id].get_user(userid=uid, username=uname))

    import itertools
    players.append(submitter)

    for elem in itertools.combinations(players, 2):
        if elem[0][0] == elem[1][0]:
            raise ValueError("Same player cannot be twice in the game.")

    return (submitter, players[0], players[1], players[2], submitter_score, rival_score)


def start(bot, update, log_update=False):
    """
    Start a new ranking for the chat from which the message originates.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        Boolean: Was the Ranking properly started
    """

    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    if update.message.chat.type == "private":
        logging.log(logging.INFO, "{} tried to create ranking for private chat".format(update.effective_user.username))
        msg = bot.send_message(chat_id=update.message.chat_id, text=("Unfortunately, private-chats cannot have rankings.\n\n" +
                                                                             "To get started with a ranking:\n" + 
                                                                             "* Create a new channel\n" +
                                                                             "* Invite @table_soccer_ranker_bot to the channel\n" +
                                                                             "* Send '/start' message to the channel"))
        if log_update:
            bot_log(msg)
        return False

    channel_admins = update.message.chat.get_administrators()

    if not update.effective_user.id in [u.user.id for u in channel_admins]:
        logging.log(logging.INFO, "{} tried to create ranking in a chat, where he's not an admin. Chat: {}".format(update.effective_user.username, update.message.chat.title))
        msg = bot.send_message(chat_id=update.message.chat_id, text="Uh oh, you need to be an channel administrator to start a ranking.")
        if log_update:
            bot_log(msg)
        return False

    # Check if ranking exists
    chat_id = update.message.chat_id
    if not chat_id in RANKINGS:
        try:
            ranking = Ranking.load_ranking(chat_id)

        except FileNotFoundError:
            try:
                logging.log(logging.INFO, "Creating a new Ranking for chat {}.".format(update.message.chat.name))
            except AttributeError:
                # Chat had no 'name'
                logging.log(logging.INFO, "Creating a new Ranking for chat-id {}.".format(chat_id))
            ranking = Ranking(chat_id)

        RANKINGS[chat_id] = ranking

        for admin in channel_admins:
            if not admin.user.is_bot:
                ranking.add_user(admin.user.id, admin.user.username)

        starter_user = update.effective_user
        if not starter_user.is_bot:
            ranking.add_user(starter_user.id, starter_user.username)
        # TODO Ping administrator to add unknown users

        msg = bot.send_message(chat_id=update.message.chat_id, text="Succesfully created a ranking for this chat. Happy gaming!")
        if log_update:
            bot_log(msg)
        return True


@user_tracker
def game(bot, update, log_update=False):
    """
    Update the ranking of the chat where the update originated from. The format of the message
    is expected to follow format of a 1-vs-1 game.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        Singles: Singles-object describing the match
    """

    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    chat_id = update.message.chat_id
    if not __check_ranking_exists(chat_id):
        try:
            __lazy_load_ranking(chat_id)
        except FileNotFoundError:
            if update.message.chat.type == "private":
                msg = bot.send_message(chat_id=update.message.chat_id, text=("Unfortunately, private-chats cannot have rankings.\n\n" +
                                                                             "To get started with a ranking:\n" + 
                                                                             "* Create a new channel\n" +
                                                                             "* Invite @table_soccer_ranker_bot to the channel\n" +
                                                                             "* Send '/start' message to the channel"))
            else:
                msg = bot.send_message(chat_id=update.message.chat_id, text=("No ranking has been started yet.\n" +
                                                                             "To get started with one, send '/start' to this chat.\n"))
            if log_update:
                bot_log(msg)
            return None
    try:
        sub, sub_score, riv, riv_score = parse_game_update(update)
    except ValueError as e:
        msg = bot.send_message(chat_id=update.message.chat_id, text="Uh oh, malformatted game result ({}). Should be form: /singles @rival your_score rival_score".format(e.args[0]))
        if log_update:
            bot_log(msg)
        return None

    pregame_ranks = {}
    # Convert to dict
    for i, (user, _) in enumerate(RANKINGS[chat_id].get_leaderboard()):
        if user in [sub[0], riv[0]]:
            pregame_ranks[user] = i

    try:
        ts = int(update.message.date.timestamp())
        singles = RANKINGS[chat_id].add_singles_match(sub, riv, sub_score, riv_score, ts)
    except (TypeError, UnacceptedMatch, DuplicateMatch, RateLimitExceeded) as err:
        # TODO COmmunicate rate-limit
        logging.log(logging.ERROR, msg="Internal error: {}".format(err))
        msg = bot.send_message(chat_id=update.message.chat_id, text="Uh oh, Internal error when tried to process the result.")
        if log_update:
            bot_log(msg)
        return None


    postgame_ranks = {}
    # Convert to dict
    for i, (user, _) in enumerate(RANKINGS[chat_id].get_leaderboard()):
        if user in [sub[0], riv[0]]:
            postgame_ranks[user] = i

    message = ["Succesfully added the game to the records."]
    additional = False

    for uid, uname in [sub, riv]:

        rise = postgame_ranks[uid] - pregame_ranks[uid]

        if uname is None:
            try:
                chat_member = bot.get_chat_member(chat_id, uid)
                user = chat_member.user.full_name
            except (TimeoutError, AttributeError):
                uname = "Unknown"

        if rise < 0:
            # Do not add extra new-lines if nothing to report.
            if not additional:
                message.append("\n\n")
                additional = True

            if rise == -1:
                message.append("Player {}, rose {} rank\n".format(uname, abs(rise)))
            else:
                message.append("Player {}, rose {} ranks\n".format(uname, abs(rise)))

        elif rise > 0:
            if not additional:
                message.append("\n\n")
                additional = True

            # Do not report lost ranks to the users. Humans' tend to weight losing higher than winning, so avoid reporting
            # a loss.

            # if rise == 1:
            #     message.append("Player {}, lost {} rank\n".format(uname, abs(rise)))
            # else:
            #     message.append("Player {}, lost {} ranks\n".format(uname, abs(rise)))

    msg = bot.send_message(chat_id=update.message.chat_id, text="".join(message))
    if log_update:
        bot_log(msg)
    # TODO Send verification query to opponent
    return singles

@user_tracker
def dual(bot, update, log_update=False):
    """
    Update the ranking of the chat where the update originated from. The format of the message
    is expected to follow format of a 2-vs-2 game.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        Duals: Duals-object describing the match
    """
    # Assume format:
    # subm_1, subm_2, rival_1, rival_2, subm_sc, rival_sc

    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    chat_id = update.message.chat_id
    if not __check_ranking_exists(chat_id):
        try:
            __lazy_load_ranking(chat_id)
        except FileNotFoundError:
            if update.message.chat.type == "private":
                msg = bot.send_message(chat_id=update.message.chat_id, text=("Unfortunately, private-chats cannot have rankings.\n\n" +
                                                                             "To get started with a ranking:\n" + 
                                                                             "* Create a new channel\n" +
                                                                             "* Invite @table_soccer_ranker_bot to the channel\n" +
                                                                             "* Send '/start' message to the channel"))
            else:
                msg = bot.send_message(chat_id=update.message.chat_id, text=("No ranking has been started yet.\n" +
                                                                             "To get started with one, send '/start' to this chat.\n"))
            if log_update:
                bot_log(msg)
            return None

    try:
        sub, sub_tm, rival, rival_tm, sub_score, riv_score = parse_dual_update(update)
    except ValueError as e:
        msg = bot.send_message(chat_id=update.message.chat_id, text="Uh oh, malformatted game result ({}). Should be form: /duals @teammate rival_1 rival_2 your_score rival_score".format(e.args[0]))
        if log_update:
            bot_log(msg)
        return None

    pregame_ranks = {}
    # Convert to dict
    for i, (user, _) in enumerate(RANKINGS[chat_id].get_leaderboard()):
        if user in [sub[0], sub_tm[0], rival[0], rival_tm[0]]:
            pregame_ranks[user] = i

    try:
        ts = int(update.message.date.timestamp())
        duals = RANKINGS[chat_id].add_dual_match(sub, sub_tm, rival, rival_tm, sub_score, riv_score, ts)
    except (TypeError, UnacceptedMatch, DuplicateMatch, RateLimitExceeded) as err:
        # TODO COmmunicate rate-limit
        logging.log(logging.ERROR, msg="Internal error: {}".format(err))
        msg = bot.send_message(chat_id=update.message.chat_id, text="Uh oh, Internal error when tried to process the result.")
        if log_update:
            bot_log(msg)
        return None


    postgame_ranks = {}
    # Convert to dict
    for i, (user, _) in enumerate(RANKINGS[chat_id].get_leaderboard()):
        if user in [sub[0], sub_tm[0], rival[0], rival_tm[0]]:
            postgame_ranks[user] = i

    message = ["Succesfully added the game to the records."]
    additional = False

    for uid, uname in [sub, sub_tm, rival, rival_tm]:

        rise = postgame_ranks[uid] - pregame_ranks[uid]

        if uname is None:
            try:
                chat_member = bot.get_chat_member(chat_id, uid)
                user = chat_member.user.full_name
            except (TimeoutError, AttributeError):
                uname = "Unknown"

        if rise < 0:
            # Do not add extra new-lines if nothing to report.
            if not additional:
                message.append("\n\n")
                additional = True
            
            if rise == -1:
                message.append("Player {}, rose {} rank\n".format(uname, abs(rise)))
            else:
                message.append("Player {}, rose {} ranks\n".format(uname, abs(rise)))
        elif rise > 0:
            if not additional:
                message.append("\n\n")
                additional = True

            # Do not report lost ranks to the users. Humans' tend to weight losing higher than winning, so avoid reporting
            # a loss.

            # if rise == 1:
            #     message.append("Player {}, lost {} rank\n".format(uname, abs(rise)))
            # else:
            #     message.append("Player {}, lost {} ranks\n".format(uname, abs(rise)))

    msg = bot.send_message(chat_id=update.message.chat_id, text="".join(message))
    if log_update:
        bot_log(msg)

    return duals


def display_name(user, count, max_len=17):
    """
    Return display friendly name + match text.

    Args:
        user (str) : Username to be displayed. Will be shortened to fit max_len parameter.
        count (int) : Amount of matches on the user.
        max_len (int) : [OPTIONAL] Maximum length of the user + match combination.

    Return:
        String : 'User (Match-count)'
    """
    matches = "(" + str(count) + ")"
    l_matches = len(matches)

    for_name = max_len-l_matches

    if len(user) > for_name-3:
        d_name = user[:for_name-3] + ".."
    else:
        d_name = user

    return " ".join([d_name, matches])

@user_tracker
def leaderboard(bot, update, log_update=False):
    """
    Post a list of top 20 players of the chat where the query originated from.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        None
    """
    
    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    chat_id = update.message.chat_id
    if not __check_ranking_exists(chat_id):
        try:
            __lazy_load_ranking(chat_id)
        except FileNotFoundError:
            if update.message.chat.type == "private":
                msg = bot.send_message(chat_id=update.message.chat_id, text=("Unfortunately, private-chats cannot have rankings.\n\n" +
                                                                             "To get started with a ranking:\n" + 
                                                                             "* Create a new channel\n" +
                                                                             "* Invite @table_soccer_ranker_bot to the channel\n" +
                                                                             "* Send '/start' message to the channel"))
            else:
                msg = bot.send_message(chat_id=update.message.chat_id, text=("No ranking has been started yet.\n" +
                                                                             "To get started with one, send '/start' to this chat.\n"))
            if log_update:
                bot_log(msg)
            return

    board = RANKINGS[chat_id].get_leaderboard()
    to_ret = ["{0:4} | {1:8}".format("Rank", "Player"),
              "------------------------"]

    matches = RANKINGS[chat_id].matches_per_user()

    for rank, (uid, _) in enumerate(board):
        if rank >= 20:
            break
        uid, user = RANKINGS[chat_id].get_user(userid=uid)
        if user is None:
            try:
                chat_member = bot.get_chat_member(chat_id, uid)
                user = chat_member.user.full_name
            except (TimeoutError, AttributeError):
                user = "No name available"
            
        try:
            count = matches[uid]
        except KeyError:
            count = 0

        to_ret.append("{0:4} | {1}".format(rank+1, display_name(user, count)))
    
    joined = "\n".join(to_ret)
    text = "*LEADERBOARD:*\n```\n" + joined + "```"

    msg = bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    if log_update:
        bot_log(msg)


@user_tracker
def standing(bot, update, log_update=False):
    """
    Post a the list of users surrounding (and including) the player that requested the standing.
    This standing refers to the standing in the ranking associated with that chat.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.

    Returns:
        None
    """

    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    chat_id = update.message.chat.id
    uid = update.effective_user.id

    STANDING_WIDTH = 3

    if not __check_ranking_exists(chat_id):
        try:
            __lazy_load_ranking(chat_id)
        except FileNotFoundError:
            if update.message.chat.type == "private":
                msg = bot.send_message(chat_id=update.message.chat_id, text=("Unfortunately, private-chats cannot have rankings.\n\n" +
                                                                             "To get started with a ranking:\n" + 
                                                                             "* Create a new channel\n" +
                                                                             "* Invite @table_soccer_ranker_bot to the channel\n" +
                                                                             "* Send '/start' message to the channel"))
            else:
                msg = bot.send_message(chat_id=update.message.chat_id, text=("No ranking has been started yet.\n" +
                                                                             "To get started with one, send '/start' to this chat.\n"))
            if log_update:
                bot_log(msg)
            return

    board = RANKINGS[chat_id].get_leaderboard()
    
    # Board around the user.
    try:
        idx = [user for user, _ in board].index(uid)
    except ValueError:
        logging.log(logging.ERROR, "User requested standing, but did not have a rating. uid: {}".format(uid))
        msg = bot.send_message(chat_id=update.message.chat_id, text=("You do not seem to be part of the ranking."))
        if log_update:
            bot_log(msg)
        return

    low_lim = max(idx - STANDING_WIDTH, 0)
    up_lim = min(idx + STANDING_WIDTH + 1, len(board))

    to_ret = ["{0:4} | {1:8}".format("Rank", "Player"),
              "------------------------"]

    matches = RANKINGS[chat_id].matches_per_user()

    for i in range(low_lim, up_lim):
        user_id, _ = board[i]

        # Returns None usernames more often than it should.
        _, uname = RANKINGS[chat_id].get_user(userid=user_id)
        if uname is None:
            try:
                chat_member = bot.get_chat_member(chat_id, user_id)
                uname = chat_member.user.full_name
            except (TimeoutError, AttributeError):
                uname = "No name available"
            
        try:
            count = matches[user_id]
        except KeyError:
            count = 0

        to_ret.append("{0:4} | {1}".format(i+1, display_name(uname, count)))

    joined = "\n".join(to_ret)
    text = "*Your standing:*\n```\n" + joined + "```"

    msg = bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    if log_update:
        bot_log(msg)


@user_tracker
def bot_help(bot, update, log_update=False):
    """
    Post a help message to the chat.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        None
    """

    if log_update:
        update_log(update)

    if PRINT_UPDATES:
        print_upd(update)

    help_message = ("To keep track of those zero-sum games.\n\n"
                    "/start - Start a ranking for this chat, can only be done by chat admin.\n\n"
                    "Submitting a game\n"
                    "It's only possible to submit games, where you are playing yourself.\n"
                    "/singles - Submit a 1v1 match. Format: @opponent your-score opponents-score.\n"
                    "/duals - Submit a 2v2 match. Format: @your_teammate @opponent_1 @opponent_2 your-score opponents-score.\n\n"
                    "/board - Show the current leaderboartd.\n\n"
                    "Happy gamings!")
        
    msg = bot.send_message(chat_id=update.message.chat_id, text=help_message)
    if log_update:
        bot_log(msg)


@user_tracker
def normal_messages(bot, update, log_update=False):
    """
    React to a normal message in the chat.

    Args:
        bot (Telegram Bot): Bot that received the message.
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        None
    """
    
    if log_update:
        update_log(update)


# TODO Converted to a wrapper
# Used in case there's a need to replay the history. E.g. in case of corrupted database.
def update_log(update):
    """
    Store the user update in a plain-text file.

    Args:
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        None
    """
    # Could be made into Bot's method for easy disable.

    chat_id = update.message.chat_id
    str_chat = str(chat_id)

    filename = str_chat if str_chat[0] != "-" else "a" + str_chat[1:]
    log_directory = op.join(op.dirname(__file__), "..", "message_history")

    if not op.exists(log_directory):
        os.mkdir(log_directory)

    fname = op.join(log_directory, filename + ".txt")

    if not op.exists(fname):
        # TOUCH
        with open(fname, 'a'):
            os.utime(fname)

    with open(fname, "a") as dump:
        dump.write(str(update) + "\n")


def bot_log(message):
    """
    Store the bot sent update in a plain-text file.

    Args:
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        None
    """
    # Could be made into Bot's method for easy disable.

    chat_id = None
    try:
        chat_id = message.chat_id
    except AttributeError:
        pass

    if chat_id is None:
        try:
            chat_id = message.chat.id
        except AttributeError:
            return
    
    str_chat = str(chat_id)

    filename = str_chat if str_chat[0] != "-" else "a" + str_chat[1:]
    fname = op.join(op.dirname(__file__), "..", "message_history", filename + "_bot.txt")

    if not op.exists(fname):
        # TOUCH
        with open(fname, 'a'):
            os.utime(fname)

    with open(fname, "a") as dump:
        dump.write(str(message) + "\n")


def print_upd(update):
    """
    Print the update into terminal.

    Args:
        update (Telegram Update): Full description of the Telegram message.
    
    Returns:
        None
    """
    print("###############################")
    print(update)
    print("###############################")


def error_logger(bot, update, telegram_error):
    """
    Handle errors caught by the Telegram Bot

    Args:
        bot (Telegram Bot): Bot that caught the Error
        update (Telegram Update): Full description of the Telegram message.
        telegram_error (Telegram Error): Error-object containing information about the error.
    
    Returns:
        None
    """

    # Limit flooding of the log-file with NetworkErrors.
    # Polling-rate of the bot is high, and each poll can result in NetworkError.
    if isinstance(telegram_error, NetworkError):
        global __ERROR_BARRIER
        if __ERROR_BARRIER:
            return
        else:
            logging.log(logging.ERROR, "TelegramError: {} raised when processing following update: {}".format(telegram_error,
                                                                                                              update))
            __ERROR_BARRIER = True
            return

    logging.log(logging.ERROR, "TelegramError: {} raised when processing following update: {}".format(telegram_error,
                                                                                                      update))
