import unittest
from telegram import Update, Message, Chat, ChatMember, User
from commands import start, game, dual, parse_game_update, parse_dual_update, user_tracker, _drop_mentions, normal_messages
from ranking import Ranking, UnacceptedMatch
import commands
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)

class DummyBot():
    def send_message(self, chat_id=0, text=""):
        print("\nBot message: {}".format(text))

    
    def get_chat_administrators(self, chat_id):
        admin_json = {'id': 1, 'first_name': '_', 'is_bot': False,
                      'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}
        return [ChatMember(User.de_json(admin_json, self), "administrator")]
    
    def get_chat_member(self, chat_id, uid):
        pass

MESSAGE_GROUP = Update.de_json({'update_id': 770304501, 'message': {'message_id': 48, 'date': 1548512407, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 48, 'date': 1548512407, 'chat':{'id': 1, 'type': 'group', 'username': 'uname_A', 'first_name': '_', 'last_name': '_'}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
MESSAGE_PRIVATE = Update.de_json({'update_id': 770304501, 'message': {'message_id': 48, 'date': 1548512407, 'chat': {'id': 1, 'type': 'private', 'username': 'uname_A', 'first_name': '_', 'last_name': '_'}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 48, 'date': 1548512407, 'chat':{'id': 1, 'type': 'private', 'username': 'uname_A', 'first_name': '_', 'last_name': '_'}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())

BOT_REMOVED_FROM_CHAT = Update.de_json({'update_id': 770304551, 'message': {'message_id': 123, 'date': 1548604463, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 2, 'first_name': 'Table Soccer Ranker', 'is_bot': True, 'username': 'uname_b'}, 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 123, 'date': 1548604463, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 2, 'first_name': 'Table Soccer Ranker', 'is_bot': True, 'username': 'uname_b'}, 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
BOT_ADDED_TO_CHAT = Update.de_json({'update_id': 770304553, 'message': {'message_id': 125, 'date': 1548604507, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id': 2, 'first_name': 'Table Soccer Ranker', 'is_bot': True, 'username': 'uname_b'}], 'new_chat_photo':[], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 125, 'date': 1548604507, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id':2, 'first_name': 'Table Soccer Ranker', 'is_bot': True, 'username': 'uname_b'}], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())

USER_JOINED_CHAT = Update.de_json({'update_id': 770304591, 'message': {'message_id': 186, 'date': 1548795012, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id': 3, 'first_name': '_', 'is_bot': False}], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 186, 'date': 1548795012, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id': 3, 'first_name': '_', 'is_bot': False}], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
USER_KICKED = Update.de_json({'update_id': 770304592, 'message': {'message_id': 187, 'date': 1548795056, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 3, 'first_name': '_', 'is_bot': False}, 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 187, 'date': 1548795056, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 3, 'first_name': '_', 'is_bot': False}, 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
USER_LEFT_CHAT = Update.de_json({'update_id': 770304594, 'message': {'message_id': 189, 'date': 1548795190, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 3, 'first_name': '_', 'is_bot': False}, 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 3, 'first_name': '_', 'is_bot': False}}, '_effective_message': {'message_id': 189, 'date': 1548795190, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'left_chat_member': {'id': 3, 'first_name': '_', 'is_bot': False}, 'new_chat_photo': [],'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from':{'id': 3, 'first_name': '_', 'is_bot': False}}}, DummyBot())

GROUP_POSTS = {"message_admin": Update.de_json({'update_id': 770304560, 'message': {'message_id': 133, 'date': 1548606732, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'test message', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 133, 'date': 1548606732, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'test message', 'entities':[], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())}

MENTIONS = {"no_username": Update.de_json({'update_id': 770304620, 'message': {'message_id': 223, 'date': 1549999267, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '_ _K Moip. Saatko pistettyä jonkun viestin tänne', 'entities': [{'type': 'text_mention', 'offset': 0, 'length': 4, 'user': {'id': 3, 'first_name': '_', 'is_bot': False}}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 223, 'date': 1549999267, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '_ _K Moip. Saatko pistettyä jonkun viestin tänne', 'entities': [{'type': 'text_mention', 'offset': 0, 'length': 4, 'user': {'id': 3, 'first_name': '_', 'is_bot': False}}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
            "not_user": Update.de_json({'update_id': 770304621, 'message': {'message_id': 224, 'date': 1550000117, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'muh @_O', 'entities': [{'type': 'mention', 'offset': 4, 'length': 3}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 224, 'date': 1550000117, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'muh @_O', 'entities': [{'type': 'mention', 'offset': 4, 'length': 3}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())}

START_PROPER = Update.de_json({'update_id': 770304487, 'message': {'message_id': 30,
                                  'date': 1548510660, 'chat': {'id': -1, 'type': 'group',
                                  'title':'channel_A', 'all_members_are_administrators': True},
                                  'text': '/start', 'entities': [{'type': 'bot_command', 'offset': 0,
                                  'length': 6}], 'caption_entities': [], 'photo': [], 'new_chat_members': [],
                                  'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False,
                                  'supergroup_chat_created': False, 'channel_chat_created': False,
                                  'from': {'id': 1, 'first_name': '_', 'is_bot': False,
                                  'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
START_NON_ADMIN = Update.de_json({'update_id': 770304487, 'message': {'message_id': 30,
                                  'date': 1548510660, 'chat': {'id': -1, 'type': 'group',
                                  'title':'channel_A', 'all_members_are_administrators': True},
                                  'text': '/start', 'entities': [{'type': 'bot_command', 'offset': 0,
                                  'length': 6}], 'caption_entities': [], 'photo': [], 'new_chat_members': [],
                                  'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False,
                                  'supergroup_chat_created': False, 'channel_chat_created': False,
                                  'from': {'id': 4, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_d'}}}, DummyBot())
GAME_INSUFFICIENT = {"just_game": Update.de_json({'update_id': 770304488, 'message': {'message_id': 32, 'date': 1548511271, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name':'_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 32, 'date': 1548511271, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_player": Update.de_json({'update_id': 770304489, 'message': {'message_id': 33, 'date': 1548511319, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [],'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 33, 'date': 1548511319, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False,'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_bot": Update.de_json({'update_id': 770304490, 'message': {'message_id': 34, 'date': 1548511372, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_b', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 34, 'date': 1548511372, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_b', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False,'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_result": Update.de_json({'update_id': 770304491, 'message': {'message_id': 35, 'date': 1548511401, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message':{'message_id': 35, 'date': 1548511401, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities':[], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_over_result": Update.de_json({'update_id': 770304492, 'message': {'message_id': 36, 'date': 1548511433, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles 11 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message':{'message_id': 36, 'date': 1548511433, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles 11 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}], 'caption_entities':[], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_player_partial_result": Update.de_json({'update_id': 770304494, 'message': {'message_id': 38, 'date': 1548511481, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A 10', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 38, 'date': 1548511481, 'chat': {'id': -1, 'type':'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A 10', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())}

GAME_MALFORMATTED = {"game_submitter_results": Update.de_json({'update_id': 770304507, 'message': {'message_id': 59, 'date': 1548516312, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_bot_results": Update.de_json({'update_id': 770304529, 'message': {'message_id': 94, 'date': 1548520319, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_b 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 24}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created':False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
                     "game_bot_draw": Update.de_json({'update_id': 770304531, 'message': {'message_id': 97, 'date': 1548520407, 'chat': {'id': -1, 'type': 'group', 'title':'channel_A', 'all_members_are_administrators': True}, 'text': '/singles @uname_A 5 5', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members':[], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())}


GAME_PROPER = [Update.de_json({'update_id': 770305007, 'message': {'message_id': 731, 'date': 1553632022, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/singles @uname_E 10 7', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 8}, {'type': 'mention', 'offset': 9, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 6, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_F'}}, '_effective_message': {'message_id': 731, 'date': 1553632022, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/singles @uname_E 10 7', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 8}, {'type': 'mention', 'offset': 9, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 6, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_F'}}}, DummyBot())]

DUAL_MALFORMATTED = {"dual_bot_self_self_results": Update.de_json({'update_id': 770304587, 'message': {'message_id': 181, 'date': 1548794305, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/dual @uname_b @uname_A @uname_A 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}, {'type': 'mention', 'offset': 15, 'length': 8}, {'type': 'mention', 'offset': 24, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 181, 'date': 1548794305, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/dual @uname_b @uname_A @uname_A 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}, {'type': 'mention', 'offset': 15, 'length': 8}, {'type': 'mention', 'offset': 24, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())}

DUAL_PROPER = [Update.de_json({'update_id': 770305169, 'message': {'message_id': 934, 'date': 1553799484, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/duals @uname_G _T @uname_H 10 6', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}, {'type': 'mention', 'offset': 7, 'length': 8}, {'type': 'text_mention', 'offset': 16, 'length': 2, 'user': {'id': 9, 'first_name': '_T', 'is_bot': False, 'username': 'uname_I', 'language_code': 'fi'}}, {'type': 'mention', 'offset': 19, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 934, 'date': 1553799484, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/duals @uname_G _T @uname_H 10 6', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}, {'type': 'mention', 'offset': 7, 'length': 8}, {'type': 'text_mention', 'offset': 16, 'length': 2, 'user': {'id': 9, 'first_name': '_T', 'is_bot': False, 'username': 'uname_I', 'language_code': 'fi'}}, {'type': 'mention', 'offset': 19, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot()),
               Update.de_json({'update_id': 770305159, 'message': {'message_id': 921, 'date': 1553794678, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/duals @uname_J @uname_K @uname_L 10 2', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}, {'type': 'mention', 'offset': 7, 'length': 8}, {'type': 'mention', 'offset': 16, 'length': 8}, {'type': 'mention', 'offset': 25, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 9, 'first_name': '_T', 'is_bot': False, 'username': 'uname_I', 'language_code': 'fi'}}, '_effective_message': {'message_id': 921, 'date': 1553794678, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/duals @uname_J @uname_K @uname_L 10 2', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}, {'type': 'mention', 'offset': 7, 'length': 8}, {'type': 'mention', 'offset': 16, 'length': 8}, {'type': 'mention', 'offset': 25, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 9, 'first_name': '_T', 'is_bot': False, 'username': 'uname_I', 'language_code': 'fi'}}}, DummyBot())]

INVITED_JOIN = {(13, 14): Update.de_json({'update_id': 770305034, 'message': {'message_id': 763, 'date': 1553640660, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id': 13, 'first_name': '_', 'is_bot': False, 'username': 'uname_M'}], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 14, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_N'}}, '_effective_message': {'message_id': 763, 'date': 1553640660, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [{'id': 13, 'first_name': '_', 'is_bot': False, 'username': 'uname_M'}], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 14, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_N'}}}, DummyBot())}

USER_WITHOUT_USERNAME = [Update.de_json({'update_id': 770305043, 'message': {'message_id': 773, 'date': 1553679783, 'chat': {'id': 9, 'type': 'private', 'first_name': '_T'}, 'text': '/start', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 9, 'first_name': '_T', 'is_bot': False, 'language_code': 'fi'}}, '_effective_message': {'message_id': 773, 'date': 1553679783, 'chat': {'id': 9, 'type': 'private', 'first_name': '_T'}, 'text': '/start', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 9, 'first_name': '_T', 'is_bot': False, 'language_code': 'fi'}}}, DummyBot())]


class TestUpdateLogging(unittest.TestCase):
    def test_update_logging_should_be_explicit(self):

        # Check that the logging directory does not contain logging file for tested chat
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(__file__), "..", "message_history", "1.txt")))

        start_update = Update.de_json({'update_id': 770304487, 'message': {'message_id': 30,
                                       'date': 1548510660, 'chat': {'id': 1, 'type': 'group',
                                       'title':'channel_A', 'all_members_are_administrators': True},
                                       'text': '/start', 'entities': [{'type': 'bot_command', 'offset': 0,
                                       'length': 6}], 'caption_entities': [], 'photo': [], 'new_chat_members': [],
                                       'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False,
                                       'supergroup_chat_created': False, 'channel_chat_created': False,
                                       'from': {'id': 1, 'first_name': '_', 'is_bot': False,
                                       'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())

        start(DummyBot(), start_update)

        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(__file__), "..", "message_history", "1.txt")))


class TestRankingCreation(unittest.TestCase):
    def test_non_user_create(self):
        self.assertFalse(start(DummyBot(), START_NON_ADMIN), "Non admin should not be able to start a Ranking")


    def test_admin_create(self):
        commands.RANKINGS = {}
        res = start(DummyBot(), START_PROPER)
        self.assertTrue((START_PROPER.message.chat.id in commands.RANKINGS.keys() and res))

# TODO Requires rewriting
class TestUserTracking(unittest.TestCase):
    def setUp(self):
        start(DummyBot(), START_PROPER)
        commands.PRINT_UPDATES = False

    def test_add_sender_id(self):
        for msg in [MESSAGE_GROUP]:
            normal_messages(DummyBot(), msg)
            in_id = msg.effective_user.id in commands.RANKINGS[msg.effective_chat.id].known_users
            self.assertTrue(in_id, "Added userid should appear in the Ranking.id_to_user.")

    def test_add_sender_username(self):
        for msg in [MESSAGE_GROUP]:
            normal_messages(DummyBot(), msg)
            known_usernames = [player.username for player in commands.RANKINGS[msg.effective_chat.id].known_users.values()]
            in_name = msg.effective_user.username.lower() in known_usernames
            self.assertTrue(in_name, "Added username should appear in the Ranking.user_to_id.")

    def test_add_joining_user(self):
        for users, msg in INVITED_JOIN.items():
            users = list(users)
            
            normal_messages(DummyBot(), msg)
            
            in_ranking = [u in commands.RANKINGS[msg.effective_chat.id].known_users.keys() for u in users]
            self.assertTrue(all(in_ranking), "All the users should appear in known users in ranking.")

    
    def tearDown(self):
        commands.RANKINGS = {}

class TestSingles(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.c = self.conn.cursor()
        self.R = Ranking(START_PROPER.message.chat_id, conn=self.conn)
        self.R2 = Ranking(GAME_PROPER[0].message.chat_id, conn=self.conn)
        
        commands.RANKINGS[DUAL_PROPER[0].message.chat_id] = self.R
        commands.RANKINGS[GAME_PROPER[0].message.chat_id] = self.R2

        start(DummyBot(), START_PROPER)
        commands.PRINT_UPDATES = False

    def test_game_format_insufficient(self):
        for case, upd in GAME_INSUFFICIENT.items():
            with self.assertRaises(ValueError, msg="Game was accepted with insufficient parameters. Case {}".format(case)):
                parse_game_update(upd)

    def test_game_malformatted(self):
        for case, upd in GAME_MALFORMATTED.items():
            with self.assertRaises(ValueError, msg="Game was accepted with malformatted parameters. Case {}".format(case)):
                parse_game_update(upd)


    def test_parse_multispace(self):
        mentioned_users = [(631509301, "uname_K")]
        
        for user in mentioned_users:
            self.R2.add_user(user[0], user[1])

        upd = Update.de_json({'update_id': 770305759, 'message': {'message_id': 1840, 'date': 1555341079, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/singles @uname_K  10 3', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 8}, {'type': 'mention', 'offset': 9, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 13, 'first_name': '_', 'is_bot': False, 'username': 'uname_M'}}, '_effective_message': {'message_id': 1840, 'date': 1555341079, 'chat': {'id': -2, 'type': 'group', 'title': 'channel_B', 'all_members_are_administrators': True}, 'text': '/singles @uname_K  10 3', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 8}, {'type': 'mention', 'offset': 9, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 13, 'first_name': '_', 'is_bot': False, 'username': 'uname_M'}}}, DummyBot())

        try:
            parse_game_update(upd)
        except ValueError as err:
            self.fail("Singles with extra spaces should be parsed correctly. Error: {}".format(err))


    def test_accept_proper(self):
        mentioned_users = [(5, "uname_E")]
        
        for user in mentioned_users:
            self.R2.add_user(user[0], user[1])


        from collections import deque

        for upd in GAME_PROPER:
            # Reset rate-limit
            for k in self.R2.rate_limits.keys():
                self.R2.rate_limits[k] = deque()

        for upd in GAME_PROPER:
            try:
                resp = game(DummyBot(), upd)
                if resp is None:
                    self.fail("Response from 'game' was None.")
            except Exception as err:
                self.fail("Proper singles submissions should be accepted. {}".format(err))
        


    def test_reject_duplicate_single(self):
        R = Ranking(GAME_PROPER[0].message.chat_id, conn=self.conn)
        commands.RANKINGS[GAME_PROPER[0].message.chat_id] = R
        from collections import deque

        for upd in GAME_PROPER:
            # Reset rate-limit
            for k in R.rate_limits.keys():
                R.rate_limits[k] = deque()

            try:
                # Proper matches should be allowed.
                game(DummyBot(), upd)
            except UnacceptedMatch:
                pass

            # Second one should be rejected
            self.assertIsNone(game(DummyBot(), upd), msg="Multiple single-submissions with same Update should be rejected.")




    # TODO Check order of the arguments
    # TODO Check value support
    # TODO Check digits
    # TODO Check int

    def tearDown(self):
        commands.RANKINGS = {}

class TestGameNoRanking(unittest.TestCase):
    def test_game_no_ranking(self):
        commands.PRINT_UPDATES = False
        for case, upd in GAME_MALFORMATTED.items():
            self.assertFalse(game(DummyBot(), upd), "Game was accepted without ranking. Case: '{}'".format(case))

class TestDuals(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.c = self.conn.cursor()
        self.R = Ranking(DUAL_PROPER[0].message.chat_id, conn=self.conn)
        commands.RANKINGS[DUAL_PROPER[0].message.chat_id] = self.R

    def test_game_malformatted(self):
        for case, upd in DUAL_MALFORMATTED.items():
            with self.assertRaises(ValueError, msg="Dual was accepted with malformatted parameters. Case {}".format(case)):
                parse_dual_update(upd)
    
    def test_parse_proper(self):
        mentioned_users = [(7, "uname_G"), (8, "uname_H"), (10, "uname_J"),
                           (11, "uname_K"), (12, "uname_L"), (9, None)]
        for user in mentioned_users:
            self.R.add_user(user[0], user[1])
        
        for upd in DUAL_PROPER:
            # All of the updates should be allowed
            try:
                parse_dual_update(upd)
            except ValueError as err:
                self.fail("Proper duals match was not allowed. Error: {}".format(err))


    def test_accept_proper(self):
        mentioned_users = [(7, "uname_G"), (8, "uname_H"), (10, "uname_J"),
                           (11, "uname_K"), (12, "uname_L"), (9, None)]
        for user in mentioned_users:
            self.R.add_user(user[0], user[1])

        for upd in DUAL_PROPER:
            # All of the updates should be allowed
            try:
                dual(DummyBot(), upd)
            except ValueError as err:
                self.fail("Proper duals match was not allowed. Error: {}".format(err))


    def test_reject_duplicate_dual(self):
        # Reset rate-limit
        from collections import deque
        for k in self.R.rate_limits.keys():
            self.R.rate_limits[k] = deque()

        for upd in DUAL_PROPER:
            try:
                # Proper matches should be allowed.
                dual(DummyBot(), upd)
            except UnacceptedMatch:
                pass

            self.assertIsNone(dual(DummyBot(), upd), msg="Multiple dual-submissions with same Update should be rejected.")


    def tearDown(self):
        commands.RANKINGS = {}


class TestPrivateFunctions(unittest.TestCase):
    def test_drop_mentions(self):
        for k, upd in MENTIONS.items():
            self.assertTrue(upd.message.text != _drop_mentions(upd), "Text did not change after __drop_mention. Case: {}, {}".format(k, upd.message.text))

    def test_drop_mentions_two_part_name(self):
        upd = Update.de_json({'update_id': 770304620, 'message': {'message_id': 223, 'date': 1549999267, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '_ _K Moip. Saatko pistettyä jonkun viestin tänne', 'entities': [{'type': 'text_mention', 'offset': 0, 'length': 4, 'user': {'id': 3, 'first_name': '_', 'is_bot': False}}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 223, 'date': 1549999267, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '_ _K Moip. Saatko pistettyä jonkun viestin tänne', 'entities': [{'type': 'text_mention', 'offset': 0, 'length': 4, 'user': {'id': 3, 'first_name': '_', 'is_bot': False}}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
        replaced = _drop_mentions(upd)
        target = "MENTION Moip. Saatko pistettyä jonkun viestin tänne"
        self.assertTrue(replaced == target, "Two part mention was not handled correctly by __drop_mention. Case: {}".format(upd.message.text))

    def test_drop_mentions_multiple_mentions(self):
        upd = Update.de_json({'update_id': 770304587, 'message': {'message_id': 181, 'date': 1548794305, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/dual @uname_b @uname_A @uname_A 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}, {'type': 'mention', 'offset': 15, 'length': 8}, {'type': 'mention', 'offset': 24, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 181, 'date': 1548794305, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': '/dual @uname_b @uname_A @uname_A 10 0', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 5}, {'type': 'mention', 'offset': 6, 'length': 8}, {'type': 'mention', 'offset': 15, 'length': 8}, {'type': 'mention', 'offset': 24, 'length': 8}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
        replaced = _drop_mentions(upd)
        target = "MENTION MENTION MENTION MENTION 10 0"
        self.assertTrue(replaced == target, "Multiple mentions was not handled correctly by __drop_mention. Case: {}".format(upd.message.text))

    def test_drop_mentions_no_mentions(self):
        upd = Update.de_json({'update_id': 770304501, 'message': {'message_id': 48, 'date': 1548512407, 'chat': {'id': -1, 'type': 'group', 'title': 'channel_A', 'all_members_are_administrators': True}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}, '_effective_message': {'message_id': 48, 'date': 1548512407, 'chat':{'id': 1, 'type': 'group', 'username': 'uname_A', 'first_name': '_', 'last_name': '_'}, 'text': 'asd', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 1, 'first_name': '_', 'is_bot': False, 'last_name': '_', 'username': 'uname_A', 'language_code': 'en'}}}, DummyBot())
        replaced = _drop_mentions(upd)
        self.assertTrue(replaced == upd.message.text, "Message with no mentions was not handled correctly by __drop_mention. Case: {}".format(upd.message.text))


if __name__ == '__main__':
    unittest.main()