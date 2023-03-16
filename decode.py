import os
import numpy as np
import sys
import json
import gzip

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

TODO: ARM-Based weirdness? Also introduction of arguments would be nice.
"""

BUNDLE_BYTES = 1000  # Number of bytes per bundle created from the original data. Must be a power of 2 greater than 8.
REDUNDANCY = 2  # Scalar for the encoded data's size
TRANSMISSION_LOSS_PERCENTAGE = 20


def decode(encoded_data, original_size):
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
    if len(sys.argv) < 2:
        print("usage: decode.py (filename)")
        exit(-1)

    if not os.path.exists(sys.argv[1]):
        print(f"file {sys.argv[1]} does not exist")
        exit(1)

    # Using a text file as input instead of a numpy array because LT code implementation doesn't seem to play nicely
    # with the numpy arrays of random integers. Using files seems to be a popular method of simulating a data stream
    # into the LT code software, as was seen in many implementations studied during our research. Also, opening the file
    # in binary mode allows it to be compiled into a bytearray later, so we use the b mode.
    data = []

    # Read the text file into bundles of predefined size specified by BUNDLE_BYTES above

    with gzip.open(sys.argv[1], "rb") as f:
        bundles = f.read()

    # Json library convert string dictionary to real dictionary type.
    # Double quotes is standard format for json
    bundles = bundles.decode()
    bundles = json.loads(bundles)

    for bundle in bundles:
        bundle["value"] = np.array(bundle["value"], dtype=np.uint64)
        data.append(bundle)

    decoded_data = decode(data, round(len(data) / REDUNDANCY))
    # print(f"\n\n\nDECODED DATA: \n{decoded_data}")

    # To more easily show that decoding was successful, recompile the decoded_data bundles into an output file.

    with open("temp_outfile", "wb") as f:
        for i, bundle in enumerate(decoded_data):
            if i < len(decoded_data):
                f.write(bundle)

    # Remember that we padded the end of our original file with zeros.

    with open("outfile.txt", "wb") as output_file:
        with open("temp_outfile", "rb") as f:
            output_file.write(f.read().rstrip(b'\0'))
    os.remove("temp_outfile")

if __name__ == "__main__":
    main()
