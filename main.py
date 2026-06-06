import argparse
import heapq
import os
import struct
import tempfile
from multiprocessing import Pool, cpu_count


INT_SIZE = 4
# В тестовом файле числа неотрицательные, поэтому использую unsigned int.
INT_FORMAT = "<I"


def get_result_name(file_name):
    directory = os.path.dirname(os.path.abspath(file_name))
    name = os.path.basename(file_name)
    return os.path.join(directory, name + ".sorted")


def check_file(file_name, max_numbers):
    if max_numbers <= 0:
        raise ValueError("max_numbers must be positive")

    if not os.path.isfile(file_name):
        raise FileNotFoundError(file_name)

    file_size = os.path.getsize(file_name)
    if file_size % INT_SIZE != 0:
        raise ValueError("file size must be a multiple of 4 bytes")


def read_numbers(f, count):
    data = f.read(count * INT_SIZE)
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
    # Каждый процесс сортирует только свою часть файла.
    part_number, numbers, temp_dir = task
    numbers.sort()

    part_file = os.path.join(temp_dir, "part_" + str(part_number) + ".bin")
    with open(part_file, "wb") as f:
        write_numbers(f, numbers)

    return part_file


def make_sorted_parts(file_name, max_numbers, temp_dir):
    part_files = []
    tasks = []
    part_number = 0

    # Делим разрешенный объем памяти между доступными процессами.
    workers = min(cpu_count(), max_numbers)
    part_size = max(1, max_numbers // workers)

    with Pool(workers) as pool:
        with open(file_name, "rb") as f:
            while True:
                numbers = read_numbers(f, part_size)
                if not numbers:
                    break

                tasks.append((part_number, numbers, temp_dir))
                part_number += 1

                if len(tasks) == workers:
                    # Передаем задачи worker-процессам.
                    part_files.extend(pool.map(sort_part, tasks))
                    tasks = []

        if tasks:
            part_files.extend(pool.map(sort_part, tasks))

    return part_files


def read_one_number(f):
    data = f.read(INT_SIZE)
    if not data:
        return None
    return struct.unpack(INT_FORMAT, data)[0]


def merge_files(part_files, result_file):
    files = [open(name, "rb") for name in part_files]
    heap = []

    try:
        # В куче лежит по одному текущему числу из каждого временного файла.
        for file_index, f in enumerate(files):
            number = read_one_number(f)
            if number is not None:
                heapq.heappush(heap, (number, file_index))

        with open(result_file, "wb") as out:
            while heap:
                # Достаем минимальное число и сразу записываем его в результат.
                number, file_index = heapq.heappop(heap)
                out.write(struct.pack(INT_FORMAT, number))

                next_number = read_one_number(files[file_index])
                if next_number is not None:
                    heapq.heappush(heap, (next_number, file_index))
    finally:
        for f in files:
            f.close()


def sort_file(file_name, max_numbers):
    check_file(file_name, max_numbers)
    result_file = get_result_name(file_name)
    directory = os.path.dirname(os.path.abspath(file_name))

    with tempfile.TemporaryDirectory(dir=directory) as temp_dir:
        part_files = make_sorted_parts(file_name, max_numbers, temp_dir)
        merge_files(part_files, result_file)

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
