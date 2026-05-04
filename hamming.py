def hamming_encode(data):
    data = list(map(int, data))

    # позиции (с 1)
    res = [0, 0, data[0], 0, data[1], data[2], data[3]]

    # P1
    res[0] = (res[2] + res[4] + res[6]) % 2

    # P2
    res[1] = (res[2] + res[5] + res[6]) % 2

    # P4
    res[3] = (res[4] + res[5] + res[6]) % 2

    return "".join(map(str, res))


print(hamming_encode("1011"))