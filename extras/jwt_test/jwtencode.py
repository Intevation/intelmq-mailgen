import pyjwt.jwt as jwt
import datetime


class JWTEncode(object):

    Backend = None
    secretkey = None

    def __init__(self, backend, secretkey):
        self.Backend = backend
        self.secretkey = secretkey

    def encode_token(self, user, expsec=3600):
        # Generates JWT Payload from a User-Object
        username = user.username
        roles = user.get_roles()
        expiration = None

        if not username:
            raise ValueError("The user was expected to contain a user but it did not")
        if not roles:
            raise ValueError("The user was expected to contain roles but it did not")

        if expsec:
            # set expiration time
            expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=expsec)

        token = {
            "user": username,
            "roles": roles
        }

        if expiration:
            token["exp"] = expiration

        return jwt.encode(token, self.secretkey)

    def decode_token(self, token):
        # Decodes the token and returns a User-Object
        try:
            t = jwt.decode(token, self.secretkey)

        except jwt.ExpiredSignatureError:
            # The token expired.
            # TODO Most likely someone wants to log in again.
            return None

        # the token is expected to contain:
        # * user
        # * roles
        username = t.get("user")
        roles = t.get("roles")

        if not username:
            raise ValueError("The token was expected to contain a user but it did not")
        if not roles:
            raise ValueError("The token was expected to contain roles but it did not")

        user = self.Backend.get_user(username)

        if not user.get_roles() == roles:
            # TODO the User changed in the meantime. reauthentication might be required
            return None

        return user
