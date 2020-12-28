from bot.ranking import Ranking
from telegram import Update, Message, Chat, ChatMember, User
import sqlite3
import json
from os import path as op


class DummyBot():
    def send_message(self, chat_id=0, text=""):
        pass
    
    def get_chat_administrators(self, chat_id):
        ADMIN_JSON = {'id': 1, 'first_name': 'X', 'is_bot': False,
                      'last_name': 'X', 'username': 'X', 'language_code': 'en'}
        return [ChatMember(User.de_json(ADMIN_JSON, self), "administrator")]


def read_updates_from_log(chat_name):
    history = []

    missed_posts = 0

    # TODO Update path at runtime.
    with open(op.join("backups", "110419", "message_history", chat_name + ".txt"), "r") as f:
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
    # TODO Use CLI-arguments.
    # TODO Create an automatic backup of the db
    # TODO Exclude bots

    # TODO Update at runtime.
    # In form [a|-]123123123
    chat_name = ""
    chat_id = chat_name if chat_name[0] != "a" else "-" + chat_name[1:]
    chat_id = int(chat_id)

    db_fp = op.join(op.dirname(__file__), "persistent_storage", chat_name+".db")
    conn = sqlite3.connect(db_fp)

    history = read_updates_from_log(chat_name)

    R = Ranking(chat_id, conn=conn)

    for update in history:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username
    
        if not update.effective_user.is_bot:
            try:
                R.add_user(user_id, username)
                print("Added user: {}, {}".format(user_id, username))
            except AssertionError:
                pass

        for user in update.message.new_chat_members:
            try:
                R.add_user(user.id, user.username)
                print("Added user: {}, {}".format(user.id, user.username))
            except AssertionError:
                pass
