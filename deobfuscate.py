import ctypes

def deobfuscate_sub_even(a1, a2, a3):
    return str(a1 * (a2 % a3)) + "?" + str(a1 * a3)

def deobfuscate_sub_odd(a1, a2, a3):
    return str(a2) + ")" + str(a1 * (a2 % a3))

def deobfuscate_numberify(string):
    string += "/"

    output = 0
    for char in string:
        output = (output << 5) - output + ord(char)
        output = ctypes.c_int(output).value

    return abs(output)

def deobfuscate(appid, reports, timestamp):
    func = None

    if appid % 2 == 1:
        func = deobfuscate_sub_odd
    else:
        func = deobfuscate_sub_even

    return deobfuscate_numberify(func(appid, reports, timestamp))