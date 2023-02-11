import os
import random
import math
import numpy as np
from time import time_ns

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

BUNDLE_BYTES = 8  # Number of bytes per bundle created from the original data. Must be a power of 2 greater than 8.
REDUNDANCY = 2  # Scalar for the encoded data's size
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
        seed = i
        random.seed(seed)
        components = random.sample(range(original_size), cur_xor_neighbors)

        cur_encode = bundles[components[0]]
        for j in range(1, cur_xor_neighbors):
            cur_encode = cur_encode ^ bundles[components[j]]

        encoded_data.append(dict(seed=seed, value=cur_encode, components=[], xor_neighbors=cur_xor_neighbors))

    return encoded_data


def decode(encoded_data, original_size):
    # First, initialize the decoded_data list as a list of -1s with length equal to the number of original bundles.
    # Since we XORed unsigned integers together, the values of encoded blocks should NEVER be negative. Thus,
    # initializing the decoded_data list with -1s gives an easy way to check whether an original bundle has been solved.
    decoded_data = original_size * [-1]

    for bundle in encoded_data:
        # "Abuse" random.seed as discussed in the encode method and fill each encoded block's components key with its
        # actual components.
        random.seed(bundle["seed"])
        bundle["components"] = random.sample(range(original_size), bundle["xor_neighbors"])

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
    input_file = open("infile.txt", "rb")
    # Using a text file as input instead of a numpy array because LT code implementation doesn't seem to play nicely
    # with the numpy arrays of random integers. Using files seems to be a popular method of simulating a data stream
    # into the LT code software, as was seen in many implementations studied during our research. Also, opening the file
    # in binary mode allows it to be compiled into a bytearray later, so we use the b mode.
    input_file_name = input_file.name
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

    # For debugging purposes, we can output all our data sets. Could be added to a verbose option in the future.
    print(f"ORIGINAL DATA: \n{data}")
    encoded_data = encode(data, len(data), round(REDUNDANCY * len(data)))  # Redundancy is introduced here
    print(f"\n\n\nENCODED DATA: \n{encoded_data}")

    # Create a file to show what the sent encoded data looks like! Optional, but interesting.

    sent_encoded_file = open("sent_encodefile.txt", "wb")

    for i, bundle in enumerate(encoded_data):
        if i < len(encoded_data) - 1:
            sent_encoded_file.write(bundle["value"])

    # Simulate data loss by removing TRANSMISSION_LOSS_PERCENTAGE% of the encoded data. Works as long as
    # TRANSMISSION_LOSS_PERCENTAGE is less than 37.5% for redundancy 2. Could potentially artificially introduce
    # transmission loss to decrease transmitted filesize. More research required.
    if TRANSMISSION_LOSS_PERCENTAGE > 0:
        encoded_data = random.sample(encoded_data, round(len(encoded_data) * (100 - TRANSMISSION_LOSS_PERCENTAGE) / 100))

    # Create a file to show what the received encoded data looks like! Optional, but interesting.

    recv_encoded_file = open("recv_encodefile.txt", "wb")

    for i, bundle in enumerate(encoded_data):
        if i < len(encoded_data) - 1:
            recv_encoded_file.write(bundle["value"])

    decoded_data = decode(encoded_data, len(data))
    print(f"\n\n\nDECODED DATA: \n{decoded_data}")

    # Calculate how many inconsistencies exist between the original and decoded bundles.

    errors = 0
    for i, o in (enumerate(data)):
        d = decoded_data[i]
        compare = (o == d)
        for j in compare:
            if not j:
                errors += 1

    print(f"\n\nResults: {errors * 100 / len(data)}% data loss with {errors} errors")

    # To more easily show that decoding was successful, recompile the decoded_data bundles into an output file.
    output_file = open("outfile.txt", "wb")

    for i, bundle in enumerate(decoded_data):
        if i < len(decoded_data) - 1:
            output_file.write(bundle)

    # Remember that we padded the end of our original file with zeros. We need to remove them. Essentially, we reverse
    # the steps performed to read the file into a bytearray in the first place.
    decoded_data = decoded_data[-1]  # Get the last bundle in decoded_data
    padded_bundle = bytes(decoded_data)
    output_file.write(padded_bundle[:os.path.getsize(input_file_name) % BUNDLE_BYTES])


if __name__ == "__main__":  # Was told to do this in CIS 390? Not sure why
    main()
