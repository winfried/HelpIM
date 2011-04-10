## {{{ http://code.activestate.com/recipes/59873/ (r1)
def gen_token():
    from random import choice
    import string
    chars = string.letters + string.digits
    newpasswd = ''
    for i in range(16):
        newpasswd = newpasswd + choice(chars)
    return newpasswd
## end of http://code.activestate.com/recipes/59873/ }}}
