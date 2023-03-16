import os
import random
import math
import numpy as np
import sys
import gzip
import shutil
import json

"""
RATIONALE: A fountain code is a type of encoding process that allows the original data to be recovered from sufficiently
large subsets of the encoded data. This property makes them highly desirable in hostile network environments, and thus
perfect for use in space.

https://en.wikipedia.org/wiki/Fountain_code

Arguably the most easily understandable method of encoding blocks involves combining them with the bitwise exclusive-or
operation. This is the foundation of a subclass of fountain codes called Luby transform (LT) codes. The exact methods of
encoding and decoding used by LT codes are fairly standardized and agreed upon, and this software prototype attempts to
implement those methods.

https://en.wikipedia.org/wiki/Luby_transform_code

More advanced and efficient subclasses of fountain code exist, such as Raptor codes, but as most of our research has
been focused on LT fountain codes, the prototype software below uses their methodology instead.

Implementations studied during research for this project those by:
    Anson Rosenthal (anrosent): https://github.com/anrosent/LT-Code
    Darren (darrenldl): https://github.com/darrenldl/ocaml-lt-code
    Spriteware: https://github.com/Spriteware/lt-codes-python
    Roberto Francescon (obolo) and Dominik Danelski (Etua): https://github.com/obolo/freeRaptor
    Daniel Chang (mwdchang): https://github.com/mwdchang/fountain-code
    Aman Tiwari: https://observablehq.com/@aman-tiwari/fountain-codes

ASSUMPTIONS:
This encoder assumes that HDTN has a way of designating ordering information with bundles when it creates them.
This encoder does not add any ordering information in its current iteration.
"""

BUNDLE_BYTES = 1000  # Number of bytes per bundle created from the original data. Must be a power of 2 greater than 8.
REDUNDANCY = 2  # Scalar for the encoded data's size
#TRANSMISSION_LOSS_PERCENTAGE = 56.25
TRANSMISSION_LOSS_PERCENTAGE = 0

def ideal_soliton(k):
    # The soliton probability distributions are designed to account for transmission errors by intelligently introducing
    # redundancy. Michael Luby, the namesake of Luby transform (LT) codes, is also the mastermind behind this algorithm.
    # A more robust version of this distribution exists and could be implemented later.
    # https://en.wikipedia.org/wiki/Erasure_code
    # https://en.wikipedia.org/wiki/Soliton_distribution
    dist = [0, 1 / k]
    for i in range(2, k + 1):
        dist.append(1 / (i * (i - 1)))
    return dist


def encode(bundles, original_size, encoded_size):
    # Start by obtaining an ideal soliton probability distribution that will be used to generate xor neighbor values
    # later.
    ideal_dist = ideal_soliton(original_size)
    xor_possibilities = []

    for i in range(0, original_size + 1):
        xor_possibilities.append(i)

    # Encode data by cycling through our bundles and XORing them together to create encoded bundles. These bundles
    # consist of an index number "index", the XORing result "value", an empty list of "components" to be used later,
    # and the block's number of XOR neighbors "to_solve".

    encoded_data = []

    for i in range(encoded_size):
        # Randomly choosing a number of xor neighbors, even from a probability distribution, will likely lead to
        # unsolvable encoding, so to ensure that the encoding is solvable, we start by creating a bundle with one xor
        # neighbor. In this way, the xor neighbors distribution is slightly less ideal, but it is far more important
        # that the encoded data is solvable.
        if i == 0:
            cur_xor_neighbors = 1
        else:
            cur_xor_neighbors = random.choices(xor_possibilities, ideal_dist)[0]

        # This is a FANTASTIC way to avoid having to transport the lists of components used to create each block!
        # Random.seed(i) will lead the random.sample to ALWAYS select the same "random" numbers from the range desired
        # in the same order for any given seed i. If we assign each encoded block a seed, we can reverse the process
        # during decoding by using the same random seeds! Idea discovered in ObservableHQ article "Fountain Codes" by
        # Aman Tiwari. Python does not have a method of randomly generating seeds other than using the unix timestamp,
        # which is still too slow to avoid duplicate seeds, so we simply use our loop index i.
        # https://observablehq.com/@aman-tiwari/fountain-codes
        random.seed(i)
        components = random.sample(range(original_size), cur_xor_neighbors)

        cur_encode = bundles[components[0]]
        for j in range(1, cur_xor_neighbors):
            cur_encode = cur_encode ^ bundles[components[j]]

        encoded_data.append(dict(value=cur_encode, components=components))

    return encoded_data


def main():
    if len(sys.argv) < 2:
        print("usage: encode.py (filename)")
        exit()

    try:
        input_file = open(sys.argv[1], "rb")
    except Exception as e:
        print(e)
        exit()

    # Using a text file as input instead of a numpy array because LT code implementation doesn't seem to play nicely
    # with the numpy arrays of random integers. Using files seems to be a popular method of simulating a data stream
    # into the LT code software, as was seen in many implementations studied during our research. Also, opening the file
    # in binary mode allows it to be compiled into a bytearray later, so we use the b mode.
    input_file_name = input_file.name
    # Only really need to get the file extension in this simulated environment, data can be sent without extensions in
    # practice
    _, extension = os.path.splitext(os.path.abspath(input_file.name))
    data = []

    # Read the text file into bundles of predefined size specified by BUNDLE_BYTES above
    for i in range(math.ceil(os.path.getsize(input_file_name) / BUNDLE_BYTES)):
        byte_array = input_file.read(BUNDLE_BYTES)
        # Testfile is transformed into an object of type bytearray so that it can be parsed by np.frombuffer later
        byte_array = bytearray(byte_array)
        byte_array_length = len(byte_array)

        # Just in case our text file does not have an exact multiple of BUNDLE_BYTES bytes (it probably doesn't) pad the
        # end of the last byte with zeros. This slightly increases the size of the original data, but it is necessary to
        # make it play nicely with the encoding and decoding process of LT code
        if byte_array_length < BUNDLE_BYTES:
            byte_array += bytearray(BUNDLE_BYTES - byte_array_length)

        # np.frombuffer takes our bytearray and interprets it as a buffer of elements of a specific type. The default
        # value for dtype is float, but since LT code uses XORs, it would be better to interpret these elements as
        # integers. The magic of how exactly these values are translated to unsigned 64 bit integers is handled by
        # numpy. If we want to forgo using any python packages (helpful if someone ever translates this to C), we will
        # need to uncover said magic methods.
        byte_array = np.frombuffer(byte_array, dtype=np.uint64)  # Also, maybe use np.uint32 if x86 systems? Ask Rachel
        data.append(byte_array)

    input_file.close()

    # For debugging purposes, we can output all our data sets. Could be added to a verbose option in the future.
    #print(f"ORIGINAL DATA: \n{data}")
    encoded_data = encode(data, len(data), round(REDUNDANCY * len(data)))  # Redundancy is introduce            d here
    #print(f"\n\n\nENCODED DATA: \n{encoded_data}")

    if TRANSMISSION_LOSS_PERCENTAGE > 0:
        encoded_data = random.sample(encoded_data, round(len(encoded_data) * (100 - TRANSMISSION_LOSS_PERCENTAGE) / 100))

    with open("temp_encodefile", "wb") as f:
        for i, bundle in enumerate(encoded_data):
            if i < len(encoded_data):
                bundle["value"] = bundle["value"].tolist()
        to_write = json.dumps(encoded_data).encode()
        f.write(to_write)

    with open("temp_encodefile", "rb") as uncompressed_file:
        with gzip.open("encodefile.gz", "wb") as compressed_file:
            shutil.copyfileobj(uncompressed_file, compressed_file)
    os.remove("temp_encodefile")

if __name__ == "__main__":
    main()
