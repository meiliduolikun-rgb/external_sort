import argparse
import heapq
import os
import struct
import tempfile
from multiprocessing import Pool, cpu_count


INT_SIZE = 4
INT_FORMAT = "<I"
MERGE_LIMIT = 64


def get_result_name(file_name):
    directory = os.path.dirname(os.path.abspath(file_name))
    name = os.path.basename(file_name)
    return os.path.join(directory, name + ".sorted")


def check_file(file_name, max_numbers):
    if max_numbers < 2:
        raise ValueError("max_numbers must be at least 2")

    if not os.path.isfile(file_name):
        raise FileNotFoundError(file_name)

    file_size = os.path.getsize(file_name)
    if file_size % INT_SIZE != 0:
        raise ValueError("file size must be a multiple of 4 bytes")


def read_numbers(f, number_count):
    data = f.read(number_count * INT_SIZE)
    numbers = []

    for i in range(0, len(data), INT_SIZE):
        number = struct.unpack(INT_FORMAT, data[i:i + INT_SIZE])[0]
        numbers.append(number)

    return numbers


def write_numbers(f, numbers):
    for number in numbers:
        data = struct.pack(INT_FORMAT, number)
        f.write(data)


def sort_part(task):
    # Sort one chunk
    part_number, file_name, start_number, number_count, temp_dir = task

    with open(file_name, "rb") as f:
        f.seek(start_number * INT_SIZE)
        numbers = read_numbers(f, number_count)

    numbers.sort()

    part_file = os.path.join(temp_dir, "part_" + str(part_number) + ".bin")
    with open(part_file, "wb") as f:
        write_numbers(f, numbers)

    return part_file


def split_file(file_name, max_numbers, temp_dir):
    part_files = []
    part_number = 0
    start_number = 0
    file_size = os.path.getsize(file_name)
    total_numbers = file_size // INT_SIZE

    process_count = min(cpu_count(), max_numbers)
    part_size = max(1, max_numbers // process_count)

    with Pool(process_count) as pool:
        while start_number < total_numbers:
            tasks = []

            for _ in range(process_count):
                if start_number >= total_numbers:
                    break

                number_count = min(part_size, total_numbers - start_number)
                tasks.append((part_number, file_name, start_number, number_count, temp_dir))
                part_number += 1
                start_number += number_count

            part_files.extend(pool.map(sort_part, tasks))

    return part_files


def read_one_number(f):
    data = f.read(INT_SIZE)
    if not data:
        return None
    return struct.unpack(INT_FORMAT, data)[0]


def merge_group(part_files, result_file):
    files = [open(name, "rb") for name in part_files]
    heap = []

    try:
        for file_index, f in enumerate(files):
            number = read_one_number(f)
            if number is not None:
                heapq.heappush(heap, (number, file_index))

        with open(result_file, "wb") as out:
            while heap:
                number, file_index = heapq.heappop(heap)
                out.write(struct.pack(INT_FORMAT, number))

                next_number = read_one_number(files[file_index])
                if next_number is not None:
                    heapq.heappush(heap, (next_number, file_index))
    finally:
        for f in files:
            f.close()


def merge_files(part_files, result_file, temp_dir, max_numbers):
    current_files = part_files
    # Limit files per merge round to prevent handle exhaustion
    merge_limit = min(MERGE_LIMIT, max_numbers)
    round_number = 0

    while len(current_files) > merge_limit:
        next_files = []

        for i in range(0, len(current_files), merge_limit):
            group = current_files[i:i + merge_limit]
            group_number = len(next_files)
            temp_file = os.path.join(
                temp_dir,
                "merge_" + str(round_number) + "_" + str(group_number) + ".bin"
            )

            merge_group(group, temp_file)
            next_files.append(temp_file)

        current_files = next_files
        round_number += 1

    merge_group(current_files, result_file)


def sort_file(file_name, max_numbers):
    check_file(file_name, max_numbers)
    result_file = get_result_name(file_name)
    directory = os.path.dirname(os.path.abspath(file_name))

    with tempfile.TemporaryDirectory(dir=directory) as temp_dir:
        part_files = split_file(file_name, max_numbers, temp_dir)
        merge_files(part_files, result_file, temp_dir, max_numbers)

    return result_file


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name")
    parser.add_argument("max_numbers", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    result = sort_file(args.file_name, args.max_numbers)
    print("result file:", result)
