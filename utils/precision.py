
def set_precision(s, pr):
    assert (pr >= 0)
    if len(s) > pr:
        diff = len(s) - pr
        return s[:diff] + "." + s[diff:]

    return "0." + "0" * (pr - len(s)) + s