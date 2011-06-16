initdone = False

def newHash():
    """Creates an unpredictable hash.
       Returns an 64 character long string, containing an
       hexadecimal encoded hash.
       Usage: hash = newHash()
    """
    import datetime
    import random
    from hashlib import sha256
    global initdone
    if not initdone:
        random.seed()
        initdone = True
    string = str(datetime.datetime.now()) + str(random.random())
    hash = sha256(string).hexdigest()
    return hash
