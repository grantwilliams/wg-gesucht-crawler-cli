import json
import getpass


def save_details(file, login_info):
    with open(file, 'w', encoding='utf-8') as save:
        json.dump(login_info, indent=4, sort_keys=True, fp=save)


def change_email():
    email = input('Email address used on wg-gesucht.de? ')
    return email


def change_password():
    password = getpass.getpass('Password used for wg-gesucht.de? ')
    return password


def change_phone():
    phone = input('What is your phone number? (optional) ')
    return phone


def change_all():
    return {
        'email': change_email(),
        'password': change_password(),
        'phone': change_phone()
    }
