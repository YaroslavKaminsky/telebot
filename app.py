from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import json


app = Flask(__name__)

ENV = 'dev'
TELEGRAMBOT_API = os.environ.get('TELEGRAMBOT_API')
ADMIN_ID = os.environ.get('ADMIN_ID')
COMMANDS = {
    '/start': 'pass'
}

if ENV =='dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class AuthError(Exception):
    pass


class UserList(db.Model):
    __tablename__ = 'userlist'

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, unique=True)


class ListNames(db.Model):
    __tablename__ = 'listnames'

    id = db.Column(db.Integer, primary_key=True)
    list_name = db.Column(db.String(100), unique=True)
    info = db.Column(db.Text())


class ItemNames(db.Model):
    __tablename__ = 'itemnames'

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), unique=True)


class ItemLists(db.Model):
    __tablename__ = 'itemlists'

    list_id = db.Column(db.Integer, db.ForeignKey('listnames.id', ondelete='CASCADE'), primary_key=True, autoincrement=False)
    item_id = db.Column(db.Integer, db.ForeignKey('itemnames.id', ondelete='CASCADE'), primary_key=True, autoincrement=False)

def auth(user_id):
    if int(user_id) == int(ADMIN_ID):
        return True
    return False


def get_all_lists():
    result = ListNames.query.order_by(ListNames.id).all()
    return result


def get_list_items(list_name):
    list_id = ListNames.query.filter_by(list_name=list_name).first().id
    result = ItemNames.query.join(ItemLists, ItemNames.id == ItemLists.item_id).filter(ItemLists.list_id == list_id).all()
    return result


def create_list(list_name, auth_id, description=None):
    if auth(auth_id):
        data = ListNames(list_name=list_name, info=description)
        db.session.add(data)
        db.session.commit()
    else:
        raise AuthError('You are not allowed to do that.')


def add_item(item_name, list_unit):
    item_data = ItemNames.query.filter_by(item_name=item_name).first()
    if item_data is None:
        item_data = ItemNames(item_name=item_name)
        db.session.add(item_data)
        db.session.commit()
    item_id = item_data.id
    list_data = ListNames.query.filter_by(id=list_unit).first()
    if list_data is not None:
        list_id = list_data.id
        data = ItemLists.query.filter_by(list_id=list_id, item_id=item_id).first()
        if data is None:
            data = ItemLists(list_id=list_id, item_id=item_id)
            db.session.add(data)
            db.session.commit()


def delete_item(item_name):
    item_data = ItemNames.query.filter_by(item_name=item_name).first()
    if item_data is not None:
        db.session.delete(item_data)
        db.session.commit()


def delete_list(list_name, auth_id):
    if auth(auth_id):
        list_data = ListNames.query.filter_by(list_name=list_name).first()
        if list_data is not None:
            db.session.delete(list_data)
            db.session.commit()
    else:
        raise AuthError('You are not allowed to do that.')


def add_user(user_id, user_name, auth_id):
    if auth(auth_id):
        data = UserList(user_name=user_name, user_id=user_id)
        db.session.add(data)
        db.session.commit()
    else:
        raise AuthError('You are not allowed to do that.')


def exist_user(user_id):
    if UserList.query.filter_by(user_id=int(user_id)).first() is not None:
        return True
    return False


def create_keyboard(list_of_buttons, type_):
    keyboard = []
    if type_ == 'list':
        for button in list_of_buttons:
            keyboard.append(
                [{
                    'text': f'{button.list_name} ({button.id})',
                    'callback_data': f'/get_list {button.list_name}'
                }]
            )
    elif type_ == 'item':
        for button in list_of_buttons:
            keyboard.append(
               [{
                    'text': f'{button.item_name}',
                    'callback_data': f'/delete_item {button.item_name}'
                }]
            )
    result = json.dumps({
        'inline_keyboard':
            keyboard

    })
    return result


def get_set_of_nums(some_list):
    result = set()
    for item in some_list:
        if item.isdigit():
            result.add(int(item))
    return result


def send_message(chat_id, text, markup=None):
    method = 'sendMessage'
    token = TELEGRAMBOT_API
    url = f'https://api.telegram.org/bot{token}/{method}'
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'reply_markup': markup}
    requests.post(url, data=data)


markup1 = {
    'inline_keyboard': [[
        {
            'text': 'button1',
            'callback_data': 'callbackdata1'
        }
        # {
        #     'text': 'button2',
        #     'callback_data': 'callbackdata2'
        # }
    ]]
}


def show_lists_bot(command_line, auth_id):
    if exist_user(auth_id):
        text = 'Наразі ви маєте наступні списки:'
        list_of_lists = get_all_lists()
        mark_up = create_keyboard(list_of_lists, 'list')
    else:
        text = 'You are not welcome here.'
        mark_up = None
    return text, mark_up


def add_item_bot(command_line, auth_id):
    if len(command_line) > 2 and command_line[-1].isdigit():
        if exist_user(auth_id):
            # lists = get_set_of_nums(command_line[2:])
            item_name = " ".join(command_line[1:(len(command_line)-1)])
            add_item(item_name, int(command_line[-1]))
            text = f'{item_name} додано до вказаного списку'
        else:
            text = 'You are not welcome here.'
    else:
        text = 'Неправильно написана команда.'
    mark_up = None
    return text, mark_up


def delete_list_bot(command_line, auth_id):
    if len(command_line) > 1:
        if exist_user(auth_id):
            list_name = " ".join(command_line[1:])
            delete_list(list_name, auth_id)
            text = f'{list_name} has been deleted'
        else:
            text = 'You are not welcome here.'
    else:
        text = 'Command is incorrect'
    mark_up = None
    return text, mark_up


def add_user_bot(command_line, auth_id):
    if len(command_line) == 3 and command_line[1].isdigit():
        add_user(int(command_line[1]), command_line[2], auth_id)
        text = f'User {command_line[2]} has been successfully added'
    else:
        text = 'Command is incorrect'
    mark_up = None
    return text, mark_up


def add_list_bot(command_line, auth_id):
    if len(command_line) > 1:
        list_name = ' '.join(command_line[1:])
        create_list(list_name, auth_id)
        text = f'List {list_name} has been successfully created'
    else:
        text = 'Command is incorrect'
    mark_up = None
    return text, mark_up


commands = {
    '/lists': show_lists_bot,
    '/+': add_item_bot,
    '+': add_item_bot,
    '/delete_list': delete_list_bot,
    '/add_list': add_list_bot,
    '/add_user': add_user_bot
}


def get_list_bot(list_name):
    text = f'{list_name}:'
    list_of_items = get_list_items(list_name)
    markup = create_keyboard(list_of_items, 'item')
    return text, markup


def delete_item_bot(item_name):
    delete_item(item_name)
    text = f'{item_name} видалено.'
    markup = None
    return text, markup


callback_commands = {
    '/delete_item': delete_item_bot,
    '/get_list': get_list_bot
}


@app.route('/', methods=['POST'])
def process():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        auth_id = data['message']['from']['id']
        command_line = data['message']['text']
        command_line = command_line.strip()
        command = command_line.split(' ')
        if command[0] in commands:
            try:
                text, keyboard = commands[command[0]](command, auth_id)
            except AuthError as er:
                text, keyboard = er, None
        else:
            text, keyboard = 'Не знаю такої команди', None
        send_message(chat_id=chat_id, text=text, markup=keyboard)
    elif 'callback_query' in data:
        chat_id = data['callback_query']['message']['chat']['id']
        callback_command = data['callback_query']['data'].split(' ')
        if callback_command[0] in callback_commands:
            text, keyboard = callback_commands[callback_command[0]](" ".join(callback_command[1:]))
        else:
            text, keyboard = 'Something wrong.', None
        send_message(chat_id=chat_id, text=text, markup=keyboard)
    return 'True'


# dict(update_id=35348070, callback_query={'id': '2764136112009630711',
#                                          'from': {'id': 643575590, 'is_bot': False, 'first_name': 'Yaroslav',
#                                                   'last_name': 'Kaminsky', 'language_code': 'uk'},
#                                          'message': {'message_id': 133, 'from': {'id': 1822993895, 'is_bot': True,
#                                                                                  'first_name': 'Списки Пукеничів',
#                                                                                  'username': 'TrueAssistBot'},
#                                                      'chat': {'id': 643575590, 'first_name': 'Yaroslav',
#                                                               'last_name': 'Kaminsky', 'type': 'private'},
#                                                      'date': 1642070351, 'text': 'text', 'reply_markup': {
#                                                  'inline_keyboard': [
#                                                      [{'text': 'button1', 'callback_data': 'callbackdata1'}]]}},
#                                          'chat_instance': '-1283722557476116626', 'data': 'callbackdata1'})

if __name__ == '__main__':
    # db.create_all()
    app.run()