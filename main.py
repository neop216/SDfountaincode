from encoder import *
from decoder import *

"""
TODO: Encode does not ensure that all original blocks will be used in the encoding process, leading to major data loss.
This issue preempts the one below due to obvious importance and because it may also solve it.

TODO: The random distribution of xor neighbors seems to lead the algorithm to impossible results, no matter how small 
MAX_XOR_NEIGHBORS is. Maybe use a more intelligent distribution (robust soliton)?

https://en.wikipedia.org/wiki/Erasure_code
https://en.wikipedia.org/wiki/Soliton_distribution
"""

BUNDLE_COUNT = 500
ENCODED_DATA_SIZE = 200
MAX_XOR_NEIGHBORS = 20

data = np.random.randint(100, size=BUNDLE_COUNT)  # placeholder data until we can integrate with HDTN

print(data)
print("encoding")
encoded_data = encode(data, ENCODED_DATA_SIZE, BUNDLE_COUNT, MAX_XOR_NEIGHBORS)
print(encoded_data)
print("decoding")
decoded_data = decode(encoded_data, ENCODED_DATA_SIZE, BUNDLE_COUNT)
print(data)
print(decoded_data)
print(len(decoded_data))

unsolved = 0
errors = 0
for i, o in enumerate(data):
    if decoded_data[i] == -1:
        unsolved += 1
    elif o != decoded_data[i]:
        errors += 1

print(f"data loss was {(errors + unsolved) * 100 / len(data)}% with {errors} errors and {unsolved} unsolved")
