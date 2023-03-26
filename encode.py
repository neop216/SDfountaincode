#!/usr/bin/env python3

import os
import random
import math
import numpy as np
import sys
import gzip
import shutil
import json
import argparse

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

        components = random.sample(range(original_size), cur_xor_neighbors)

        cur_encode = bundles[components[0]]
        for j in range(1, cur_xor_neighbors):
            cur_encode = cur_encode ^ bundles[components[j]]

        encoded_data.append(dict(value=cur_encode, components=components))

    return encoded_data


def main():
    parser = argparse.ArgumentParser(description="Fountain code encoder for use with NASA's HDTN")

    parser.add_argument("filename", help="Input file path")
    parser.add_argument("-b", "--bytes", help="Number of bytes per bundle >= 8", default=1000, type=int)
    parser.add_argument("-r", "--redundancy",
                        help="Scalar for the encoded data's size >= 1.3; higher values will increase redundancy as well as file size",
                        default=2.0, type=float)
    parser.add_argument("-tlp", "--transmission-loss-percentage", help="Simulate transmission loss; percentage from 0 to 100",
                        default=0.0, type=float)
    parser.add_argument("--x86", help="Use 32-bit unsigned int datatype for the encoded data buffer",
                        action="store_true")

    args = parser.parse_args()

    try:
        input_file = open(args.filename, "rb")
    except Exception as e:
        print(e)
        exit()

    BUNDLE_BYTES = args.bytes
    REDUNDANCY = args.redundancy
    TRANSMISSION_LOSS_PERCENTAGE = args.transmission_loss_percentage
    DATATYPE = np.uint64 if not args.x86 else np.uint32

    if BUNDLE_BYTES < 8:
        raise argparse.ArgumentError("Minimum bundle size is 8 bytes")

    if REDUNDANCY < 1.3:
        raise argparse.ArgumentError("Minimum redundancy scalar is 1.3")

    if TRANSMISSION_LOSS_PERCENTAGE < 0.0 or TRANSMISSION_LOSS_PERCENTAGE > 100.0:
        raise argparse.ArgumentError("Transmission loss percentage must be a value from 0.0 to 100.0, inclusive")

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
        byte_array = np.frombuffer(byte_array, dtype=DATATYPE)  # Also, maybe use np.uint32 if x86 systems? Ask Rachel
        data.append(byte_array)

    input_file.close()

    # For debugging purposes, we can output all our data sets. Could be added to a verbose option in the future.
    #print(f"ORIGINAL DATA: \n{data}")
    encoded_data = encode(data, len(data), round(REDUNDANCY * len(data)))  # Redundancy is introduce            d here
    #print(f"\n\n\nENCODED DATA: \n{encoded_data}")

    # Simulate data loss, if necessary
    if TRANSMISSION_LOSS_PERCENTAGE > 0.0:
        encoded_data = random.sample(encoded_data, round(len(encoded_data) * (100 - TRANSMISSION_LOSS_PERCENTAGE) / 100))

    # Write each bundle to the temporary output file. Since HDTN will be fragmenting this encoded file into bundles,
    # we should not write these bundles to the file all at once in a unified data structure like a list.
    # As long as each bundle is surrounded by curly braces {}, the decoder can recover them using regex.
    with open("temp_encodefile", "wb") as f:
        for bundle in encoded_data:
            # For the purposes of reading these bundles later, we should write them with lists instead of numpy arrays.
            # The lists are converted back into numpy arrays by the decoder.
            bundle["value"] = bundle["value"].tolist()
            to_write = json.dumps(bundle).encode()
            f.write(to_write)

    # Temporary method of data compression. Another method may be more desirable as design constraints are enumerated.
    # Also, delete the temporary output file after using it since it is not needed.
    with open("temp_encodefile", "rb") as uncompressed_file:
        with gzip.open("encodefile.gz", "wb") as compressed_file:
            shutil.copyfileobj(uncompressed_file, compressed_file)
    os.remove("temp_encodefile")

if __name__ == "__main__":
    main()
