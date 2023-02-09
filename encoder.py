import numpy as np
import random
from soliton import *

def encode(data, encoded_size, original_size, neighbors):
    encoded_data = []

    # create distributions for values based on ideal soliton
    ideal_xor_dist = ideal_soliton(neighbors)
    xor_dist = scale_dist(ideal_xor_dist, neighbors)
    xor_dist = xor_scale(xor_dist, encoded_size)
    xor_dist = ratio_adjust(xor_dist, encoded_size, ideal_xor_dist)
    print(xor_dist)

    # get the scale value to see how many total uses of the original data blocks we need
    scale = scale_sum(xor_dist)

    # data_dist = ([scale // encoded_size + (1 if x < scale % encoded_size else 0) for x in range(encoded_size)])
    ideal_data_dist = ideal_soliton(original_size)
    data_dist = scale_dist(ideal_data_dist, scale)
    data_dist = ratio_adjust(data_dist, scale, ideal_data_dist)
    print(data_dist)


    # expand the distributions into lists for the encoding process
    xor_list = []

    for i, freq in enumerate(xor_dist):
        for j in range(freq):
            xor_list.append(i)

    data_list = []

    for i, freq in enumerate(data_dist):
        for j in range(freq):
            data_list.append(dict(value=data[i], index=i))

    random.shuffle(data_list)

    for cur_xor_num in xor_list:
        cur_xor_num += 1
        print(f"encoding with {cur_xor_num}")
        components = []
        cur_block = random.choice(data_list)
        value = cur_block["value"]
        index = cur_block["index"]
        components.append(index)
        data_list.remove(cur_block)
        cur_encode = value

        for j in range(1, cur_xor_num):
            cur_block = random.choice(data_list)
            value = cur_block["value"]
            index = cur_block["index"]
            components.append(index)
            cur_encode = cur_encode ^ value
            data_list.remove(cur_block)

        encoded_data.append(dict(value=cur_encode, components=components, steps_to_solve=len(components) - 1))

    verify(data, encoded_data)

    return encoded_data


def verify(original_data, encoded_data):
    original_data = original_data.tolist()
    for i in range(len(original_data)):
        o = original_data.pop()
        for e in encoded_data:
            components = e["components"]
            if o in components:
                print(f"block {o} found in encoded block {e}")
                break

    if len(original_data) > 0:
        print("verification complete, encoding failed")
        exit(1)
    else:
        print("verification complete, encoding succeeded")