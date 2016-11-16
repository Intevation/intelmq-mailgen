"""
Prototype of a Usermodel
"""


class User(object):
    # This is a very simple User
    username = None
    password = None
    roles = None

    def __init__(self, username, password, roles):
        self.username = username
        self.password = password
        self.roles = roles

    def get_role(self, rolename):
        for role in self.roles:
            if role["name"] == rolename:
                return role
        return None

    def has_role(self, rolename):
        if self.get_role(rolename):
            return True
        else:
            return False

    def get_roles(self):
        rolenames = []
        for r in self.roles:
            rolenames.append(r.get("name"))

        return rolenames


class Role(object):
    # this is how a role looks like
    name = None

    def __init__(self, roleid, rolename):
        self.name = rolename
