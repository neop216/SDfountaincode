import os
import random
import math
import numpy as np

"""
RATIONALE: A fountain code is a type of encoding process that allows the original data to be recovered from sufficiently
large subsets of the encoded data. This property makes them highly desirable in hostile network environments, and thus
perfect for use with NASA's HDTN.

https://en.wikipedia.org/wiki/Fountain_code

Arguably the most easily understandable method of encoding blocks involves combining them with the bitwise exclusive-or
operation. This is the foundation of a subclass of fountain codes called Luby transform (LT) codes. The exact methods of
encoding and decoding used by LT codes are fairly standardized and agreed upon, and this software prototype attempts to
implement those methods.

https://en.wikipedia.org/wiki/Luby_transform_code

More advanced and efficient subclasses of fountain code exist, such as Raptor codes, but as most of our research has
been focused on LT fountain codes, the prototype software below uses their methodology instead.
"""

BUNDLE_BYTES = 128  # Number of bytes per bundle created from the original data
REDUNDANCY = 2  # Scalar for the encoded data's size


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
    rand_sequence = list(range(0, original_size + 1))

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
            cur_xor_neighbors = random.choices(rand_sequence, ideal_dist)[0]

        # This is a FANTASTIC way to avoid having to transport the lists of components used to create each block!
        # Random.seed(i) will lead the random.sample to ALWAYS select the same "random" numbers from the range desired
        # in the same order for any given seed i. If we assign each encoded block an index and use that index as our
        # random seed, we can reverse the process during decoding by using the same random seeds!
        # Idea discovered in ObservableHQ article "Fountain Codes" by Aman Tiwari. Tiwari's implementation passes the
        # randomly generated seed with each encoded block, but passing the smaller index value will be more efficient.
        # https://observablehq.com/@aman-tiwari/fountain-codes
        random.seed(i)
        encoded_subset = random.sample(range(original_size), cur_xor_neighbors)

        cur_encode = bundles[encoded_subset[0]]
        for j in range(1, cur_xor_neighbors):
            cur_encode = cur_encode ^ bundles[encoded_subset[j]]

        encoded_data.append(dict(index=i, value=cur_encode, components=[], to_solve=cur_xor_neighbors))

    return encoded_data


def decode(encoded_data, original_size):
    # First, initialize the decoded_data list as a list of -1s with length equal to the number of original bundles.
    # Since we XORed unsigned integers together, the values of encoded blocks should NEVER be negative. Thus,
    # initializing the decoded_data list with -1s gives an easy way to check whether an original bundle has been solved.
    decoded_data = original_size * [-1]

    for bundle in encoded_data:
        # "Abuse" random.seed as discussed in the encode method and fill each encoded block's components key with its
        # actual components.
        random.seed(bundle["index"])
        bundle["components"] = random.sample(range(original_size), bundle["to_solve"])

    # Iterate through the encoded_data. If the current encoded bundle has 1 left to solve (to_solve), it does not need
    # to wait for any other bundles to be processed before it can be considered solved. If the decoded_data bundle we're
    # looking at is unsolved, its value is added to the decoded_data at the appropriate index. Afterwards, we iterate
    # through the rest of the encoded_data bundles to see if any of them used the solved decoded_data as a component.
    # Upon finding such a bundle, we can't assign any new decoded_data values, but we can update the bundle's value
    # by XORing it with the newly-decoded bundle's value. Doing so bring the bundle one step closer to being decoded,
    # so its "to_solve" value is decreased by one. This process is repeated until all encoded blocks are solved!

    solved = -1  # Python doesn't have "do-while", so we need to initialize this solved variable here. Can't use "None".
    while solved != 0:
        solved = 0
        for i, bundle in enumerate(encoded_data):
            if bundle["to_solve"] == 1:
                solved += 1
                bundle_index = next(iter(bundle["components"]))
                encoded_data.pop(i)
                cur_decode = decoded_data[bundle_index]

                # Encoding results in some elements of decoded_data being ints and others being numpy arrays. Here, we
                # would only need the sum of the numpy array as a way to generate an integer to represent it. We're
                # just checking to make sure that the decoded_data entry we're looking at isn't already solved for
                # efficiency purposes.
                if not isinstance(cur_decode, int):
                    cur_decode = sum(cur_decode)

                if cur_decode < 0:
                    cur_value = bundle["value"]
                    decoded_data[bundle_index] = cur_value
                    solved += 1

                    for other_bundle in encoded_data:
                        if other_bundle["to_solve"] > 1 and bundle_index in other_bundle["components"]:
                            other_bundle["value"] = cur_value ^ other_bundle["value"]
                            other_bundle["to_solve"] -= 1

    return decoded_data


def main():
    input_file = open("infile.txt", "rb")
    # Using a text file as input instead of a numpy array because LT code implementation doesn't seem to play nicely
    # with bundles with values that are different lengths of bits. We could try to pad numbers in a numpy array in a way
    # that would simulate the division of an actual hunk of data, but I think this is actually more accurate anyway!
    # Also, opening the file in binary mode allows it to be compiled into a bytearray later, so we use the b mode.
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
    print(f"ORIGINAL DATA: \n\n\n{data}")
    encoded_data = encode(data, len(data), REDUNDANCY * len(data))  # Redundancy is introduced here
    print(f"ENCODED DATA: \n\n\n{encoded_data}")
    decoded_data = decode(encoded_data, len(data))
    print(f"DECODED DATA: \n\n\n{decoded_data}")

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
