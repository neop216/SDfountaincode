import numpy as np


def solve(cur_block, decoded_data):
    components = cur_block["components"]  # list of dictionaries
    value = cur_block["value"]
    solved = components[0]
    if len(components) == 1:  # block only had one component, so no need to solve, just take value
        decoded_data[solved] = value
    else:
        cur_decode = value
        for component in components:
            if decoded_data[component] == -1:  # this is the unsolved component, note for later
                solved = component
            else:
                component_value = decoded_data[component]
                cur_decode ^= component_value

        decoded_data[solved] = cur_decode
    return solved


def decode(encoded_data, encoded_size, original_size):
    to_solve = encoded_size
    # print(f"{to_solve} left to solve")
    decoded_data = np.full(original_size, -1)
    run_count = 0
    while len(encoded_data) > 0:
        run_count += 1
        print(f"run {run_count}")
        print(f"{len(encoded_data)} encoded blocks left to solve")
        # print(encoded_data)
        # print(decoded_data)
        encoded_len = -1
        decoded_len = -1
        for index, cur_block in enumerate(encoded_data):
            encoded_len = len(encoded_data)
            decoded_len = 0
            for d in decoded_data:
                if d != -1:
                    decoded_len += 1
            steps_to_solve = cur_block["steps_to_solve"]  # int

            if steps_to_solve == 0:  # a block is ready to be solved
                # print(f"{len(encoded_data) - 1} left to solve")
                solved = solve(cur_block, decoded_data)

                if solved != -1:
                    print(f"    original block {solved} has been decoded")
                block_components = cur_block["components"]
                block_steps = cur_block["steps_to_solve"]
                print(f"    popping encoded block {block_components} with {block_steps} moves left to solve")
                encoded_data.remove(cur_block)  # every component in this encoded block is solved, so we don't need it anymore
                for other_block in encoded_data:
                    # decrease steps_to_solve for every encoded block with the component we just solved
                    other_block_components = other_block["components"]
                    if solved in other_block_components:
                        other_block["steps_to_solve"] = max(-1, other_block["steps_to_solve"] - other_block_components.count(solved))
                        other_block_steps = other_block["steps_to_solve"]
                        if other_block_steps == -1:
                            print(f"    encoded block {other_block_components} was also solved by this solution and is being popped")
                            solve(other_block, decoded_data)
                            encoded_data.remove(other_block)
                            encoded_len = len(encoded_data)
                            decoded_len = 0
                            for d in decoded_data:
                                if d != -1:
                                    decoded_len += 1
                        else:
                            print(f"    encoded block {other_block_components} has {other_block_steps} moves left to solve")
        if encoded_len == len(encoded_data):
            print("unsolvable")
            print(encoded_data)
            return decoded_data

    return decoded_data