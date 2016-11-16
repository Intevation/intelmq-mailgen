import pyjwt.jwt as jwt

from backend import FileBackend as Backend
from jwtencode import JWTEncode


def main():

    be = Backend("conf.json")
    key = "lohl6Yueg0Duhie3Ahleezee0fei0ahr4Doorei5EiGaimi5chaiv8thiFaiD2ay6ooHeeCooxeeph3i"
    encoder = JWTEncode(be, key)

    usernames=["a", "b", "c"]

    tokens=[]

    print()
    print("Generating Tokens for a subset of usernames")
    print()
    for name in usernames:
        if be.check_password(name, "qwertz"):
            u = be.get_user(name)
            print("Password matches for: " + name + " Your token is:")
            t = encoder.encode_token(u)
            print(t)
            tokens.append(t)
        else:
            print("Password doesn't match for: " + name)
            print("not generating a token")

        print("----")


    print()
    print("Deriving Usernames from a Subset of Tokens")
    for token in tokens:
        user = encoder.decode_token(token)
        print("Retrieved username: "+ user.username + " from token")
        print(user.username + " is member of:")
        print(user.get_roles())


if __name__ == '__main__':
    main()