from os import path as op
from add_users_from_log import read_updates_from_log, DummyBot

import json
from telegram import Update

if __name__ == "__main__":

    # TODO Update at runtime.
    # In form [a|-]123123123
    chat_name = ""

    pre_accepted = []
    pre_refused = []

    # COllect the already accepted ones
    with open("accepted_matches.txt", "r") as f:
        for line in f:
            line = line.replace("\'", "\"")
            line = line.replace("True", "true")
            line = line.replace("False", "false")
            
            d = json.loads(line)
            pre_accepted.append(Update.de_json(d, DummyBot()))

    # COllect the already accepted ones
    with open("refused_matches.txt", "r") as f:
        for line in f:
            line = line.replace("\'", "\"")
            line = line.replace("True", "true")
            line = line.replace("False", "false")
            
            d = json.loads(line)
            pre_refused.append(Update.de_json(d, DummyBot()))


    hist = read_updates_from_log(chat_name)

    post_accepted = []
    post_refused = []

    for upd in hist[:]:
        if not upd.message.entities:
            continue
        elif upd.message.entities[0].type != "bot_command":
            continue
        elif len(upd.message.entities) < 2:
            continue
        else:
            if upd not in pre_accepted and upd not in pre_refused:
                print("---------------------------------------------")
                print(upd.message.text)
                inp = input()
                while True:
                    if inp == "y":
                        post_accepted.append(upd)
                        break
                    elif inp == "n":
                        post_refused.append(upd)
                        break
                    else:
                        inp=input()

    with open("accepted_matches.txt", "a") as w:
        for m in post_accepted:
            w.write(str(m) + "\n")
    
    with open("refused_matches.txt", "a") as w:
        for m in post_refused:
            w.write(str(m) + "\n")
    