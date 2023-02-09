def ideal_soliton(k):
    dist = []
    for i in range(1, k + 1):
        dist.append(1 / k if i == 1 else 1 / (i * (i - 1)))
    return dist


def scale_dist(dist, size):
    # peak of ideal soliton is at 2
    if len(dist) < 2:
        return dist
    # scale distribution according to original size and make the minimum value 1 if the scaled value is still less than 1
    # then, round each number to the nearest integer
    dist = [round((i * ((size / 2) / dist[1]) if i * ((size / 2) / dist[1]) >= 1 else 1)) for i in dist]

    return dist


def ratio_adjust(dist, size, orig_ratios):
    # adjust distribution to match the desired size if it does not already
    # determine which elements to adjust based on the difference between the original and adjusted ratios
    while sum(dist) < size:
        adj_ratios = [(i / sum(dist)) for i in dist]
        min_diff = -1
        min_diff_index = -1

        for i in range(len(adj_ratios)):
            diff = adj_ratios[i] - orig_ratios[i]
            if diff > min_diff and dist[i] > 1:
                min_diff_index = i
                min_diff = diff

        dist[min_diff_index] += 1

    while sum(dist) > size:
        adj_ratios = [(i / sum(dist)) for i in dist]
        max_diff = -1
        max_diff_index = -1

        for i in range(len(adj_ratios)):
            diff = adj_ratios[i] - orig_ratios[i]
            if diff > max_diff and dist[i] > 1:
                max_diff_index = i
                max_diff = diff

        dist[max_diff_index] -= 1

    return dist


def xor_scale(dist, size):
    scalar = size / sum(dist)
    dist = [round(i * scalar) for i in dist]

    return dist


def scale_sum(dist):
    scale_sum = 0
    for index, cur in enumerate(dist):
        scale_sum += (index + 1) * cur

    return scale_sum

'''
size = 500
encodedsize = 200
xorsize = 8

ideal_xordist = ideal_soliton(xorsize)
opt_xordist = scale_dist(ideal_xordist, xorsize)
opt_xordist = xor_scale(opt_xordist, encodedsize)
adj_xordist = ratio_adjust(opt_xordist, encodedsize, ideal_xordist)

print(adj_xordist)
print(sum(adj_xordist))

scalar = scale_sum(adj_xordist)
print(scalar)

ideal_dist = ideal_soliton(size)
opt_dist = scale_dist(ideal_dist, scalar)
adj_dist = ratio_adjust(opt_dist, scalar, ideal_dist)

print(adj_dist)
print(sum(adj_dist))
'''