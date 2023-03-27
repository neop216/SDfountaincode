#!/usr/bin/env python3

import os
import numpy as np
import sys
import json
import gzip
import re
import argparse
import time

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
"""


def decode(data):
    encoded_data = []
    for bundle in data:
        encoded_data.append(bundle)

    # First, initialize the decoded_data list as a list of -1s with length equal to the number of original bundles.
    # Since we XORed unsigned integers together, the values of encoded blocks should NEVER be negative. Thus,
    # initializing the decoded_data list with -1s gives an easy way to check whether an original bundle has been solved.
    decoded_data = []

    # Iterate through the encoded_data. If the current encoded bundle has 1 component left, it does not need to wait for
    # any other bundles to be processed before it can be considered solved. If the decoded_data bundle we're looking at
    # is unsolved, its value is added to the decoded_data at the appropriate index. Afterwards, we iterate through the
    # rest of the encoded_data bundles to see if any of them used the solved decoded_data as a component. Upon finding
    # such a bundle, we can't assign any new decoded_data values, but we can update the bundle's value by XORing it with
    # the newly-decoded bundle's value. The component can then be considered to have been "removed" from the encoded
    # bundle, so we remove it from the bundle's component list.

    solved = -1  # Python doesn't have "do-while", so we need to initialize this solved variable here. Can't use "None".
    while solved != 0:
        solved = 0
        for i, bundle in enumerate(encoded_data):
            if len(bundle["components"]) == 1:
                solved += 1
                component_index = bundle["components"][0]
                encoded_data.pop(i)

                if component_index >= len(decoded_data):
                    for i in range(component_index - len(decoded_data) + 1):
                        decoded_data.append(-1)

                cur_decode = decoded_data[component_index]


                # Encoding results in some elements of decoded_data being ints and others being numpy arrays. Here, we
                # would only need the sum of the numpy array as a way to generate an integer to represent it. We're
                # just checking to make sure that the decoded_data entry we're looking at isn't already solved for
                # efficiency purposes.
                if not isinstance(cur_decode, int):
                    cur_decode = sum(cur_decode)

                if cur_decode < 0:
                    cur_value = bundle["value"]
                    decoded_data[component_index] = cur_value
                    solved += 1

                    for other_bundle in encoded_data:
                        if len(other_bundle["components"]) > 1 and component_index in other_bundle["components"]:
                            other_bundle["value"] = cur_value ^ other_bundle["value"]
                            other_bundle["components"].remove(component_index)

    return decoded_data


def main():
    print("<decoder> setting up...")

    parser = argparse.ArgumentParser(description="Fountain code decoder for use with NASA's HDTN")

    parser.add_argument("filename", help="Input file path")
    parser.add_argument("--x86", help="Use 32-bit unsigned int datatype for the encoded data buffer",
                        action="store_true")

    args = parser.parse_args()

    if not os.path.exists(sys.argv[1]):
        print(f"file {sys.argv[1]} does not exist")
        exit(1)

    DATATYPE = np.uint64 if not args.x86 else np.uint32

    # Each bundle from the encoded data file is already the correct bundle size, so we do not need to worry about
    # each segment read below being the same size. The entire file is read into a string, which is then decoded from
    # bytes and split into individual bundles using regex. Each individual bundle is still a string, so we load them
    # into dictionaries.

    with gzip.open(args.filename, "rb") as f:
        bundle_list = f.read()

    bundle_list = bundle_list.decode()
    bundles = re.findall(r'\{.*?\}', bundle_list)

    data = []
    for bundle in bundles:
        bundle = json.loads(bundle)

        # Bundle values were stored as lists instead of numpy arrays so that the decoder can read them. Now that they
        # have been parsed, they can be converted back into numpy arrays.
        bundle["value"] = np.array(bundle["value"], dtype=DATATYPE)
        data.append(bundle)

    print(f"<decoder> setup finished!\n<decoder> decoding data...")

    start = time.time()
    decoded_data = decode(data)
    end = time.time()
    print(f"<decoder> data decoded! elapsed time: {round((end - start) * 1000, 1)} ms\n<decoder> writing decoded data...")
    # print(f"\n\n\nDECODED DATA: \n{decoded_data}")

    # Recompile the decoded_data bundles into an output file.

    with open("temp_outfile", "wb") as f:
        for bundle in decoded_data:
            f.write(bundle)

    # Remember that we padded the end of our original file with zeros, so we strip them off. A more intelligent
    # solution would involve making sure we aren't stripping off intended nulls terminating the original data,
    # but this works as a proof of concept.

    with open("outfile", "wb") as output_file:
        with open("temp_outfile", "rb") as f:
            output_file.write(f.read().rstrip(b'\0'))
    os.remove("temp_outfile")

    print(f"<decoder> writing finished!")

if __name__ == "__main__":
    main()
