"""
Prototype and mockup of a Backend to retrieve users
"""

import usermodel as um
import json


class Backend(object):

    def __init__(self):
        pass

    def get_user(self, username):
        pass

    def del_user(self, username):
        pass

    def add_user(self, username, password):
        pass

    def add_user_role(self, user, role):
        pass

    def del_user_role(self, user, role):
        pass

    def check_password(self, username, passtocheck):
        u = self.get_user(username)
        return u.password == passtocheck


class FileBackend(Backend):

    users = None
    configfile = None

    def __init__(self, conf):
        with open(conf, 'r') as cf:
            # Read File
            self.configfile = cf.read()

        users = json.loads(self.configfile)
        self.users=users.get("users")

    def get_user(self, username):
        for u in self.users:
            if u.get("username") == username:
                user = u
                break

        if user:
            return um.User(username=user.get("username"),
                           password=user.get("password"),
                           roles=user.get("roles"))
        else:
            return None