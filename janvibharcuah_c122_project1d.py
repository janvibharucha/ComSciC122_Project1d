# -*- coding: utf-8 -*-
"""JanviBharcuah_C122_Project1d.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1XElicqna98ZLGDIhkrT04UT0JHhEz_om
"""

from collections import defaultdict
import os
import re
from google.colab import drive
import zipfile
!pip install bitarray mmh3
from bitarray import bitarray
import mmh3

def load_fasta(file_path):
    sequences = {}
    with open(file_path, 'r') as file:
        current_seq_id = None
        current_seq = []
        for line in file:
            line = line.strip()
            if line.startswith(">"):
                if current_seq_id:
                    sequences[current_seq_id] = ''.join(current_seq)
                current_seq_id = line[1:]
                current_seq = []
            else:
                current_seq.append(line)
        if current_seq_id:
            sequences[current_seq_id] = ''.join(current_seq)

    if len(sequences) == 1:
        return list(sequences.values())[0]
    return sequences

class BloomFilter:
    def __init__(self, size=1000000, hash_count=3):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = bitarray(size)
        self.bit_array.setall(0)

    def add(self, item):
        for i in range(self.hash_count):
            index = mmh3.hash(str(item), i) % self.size
            self.bit_array[index] = 1

    def check(self, item):
        return all(self.bit_array[mmh3.hash(str(item), i) % self.size] for i in range(self.hash_count))

def build_genome_bloom_filters(directory, kmer_size=50):
    genome_files = [f for f in os.listdir(directory) if "project1d_genome_" in f]
    genome_filters = {}

    for file_name in genome_files:
        file_path = os.path.join(directory, file_name)
        genome_data = load_fasta(file_path)
        bloom = BloomFilter()
        for i in range(len(genome_data) - kmer_size + 1):
            bloom.add(genome_data[i:i+kmer_size])
        genome_filters[file_name] = bloom
    return genome_filters

def identify_present_genomes(reads, genome_filters):
    genome_counts = defaultdict(int)

    for read_seq in reads.values():
      for genome, bloom in genome_filters.items():
          if bloom.check(read_seq):
              genome_counts[genome] += 1
    print(genome_counts)
    print(f"length: {len(genome_counts)}")
    threshold = 0.05*len(reads)
    print(threshold)
    present_genomes = {g for g, count in genome_counts.items() if count > threshold}
    print("Genomes identified:", present_genomes)
    return present_genomes

def creating_genomes_list(directory):

    max_genome_num = 0
    genome_files = [
        file_name for file_name in os.listdir(directory)
        if "project1d_genome_" in file_name
    ]


    for file_name in genome_files:
        genome_num = int(re.search(r'genome_(\d+)', file_name).group(1))
        max_genome_num = max(max_genome_num, genome_num)

    genomes = [None] * (max_genome_num + 1)

    for file_name in genome_files:
        file_path = os.path.join(directory, file_name)
        genome_num = int(re.search(r'genome_(\d+)', file_name).group(1))
        genomes[genome_num] = load_fasta(file_path)

    return genomes

def list_of_reads(reads):
  reads_list = []
  for read_id, sequence in reads.items():
    reads_list.append(sequence)
  return reads_list

def build_index(genome, kmer_size=15):
    genome_index = defaultdict(list)
    for i in range(len(genome) - kmer_size + 1):
        kmer = genome[i:i + kmer_size]
        genome_index[kmer].append(i)
    return genome_index

def needleman_wunsch(seq1: str, seq2: str, match=1, mismatch=-1, gap=-1):
    m, n = len(seq1), len(seq2)
    score_matrix = [[0] * (n + 1) for _ in range(m + 1)]
    traceback = [[None] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        score_matrix[i][0] = gap * i
        traceback[i][0] = 'up'
    for j in range(1, n + 1):
        score_matrix[0][j] = gap * j
        traceback[0][j] = 'left'

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match_score = score_matrix[i - 1][j - 1] + (match if seq1[i - 1] == seq2[j - 1] else mismatch)
            delete = score_matrix[i - 1][j] + gap
            insert = score_matrix[i][j - 1] + gap
            score_matrix[i][j], traceback[i][j] = max(
                (match_score, 'diag'), (delete, 'up'), (insert, 'left')
            )

    aligned_seq1, aligned_seq2 = "", ""
    i, j = m, n
    while i > 0 or j > 0:
        if traceback[i][j] == 'diag':
            aligned_seq1 += seq1[i - 1]
            aligned_seq2 += seq2[j - 1]
            i, j = i - 1, j - 1
        elif traceback[i][j] == 'up':
            aligned_seq1 += seq1[i - 1]
            aligned_seq2 += '-'
            i -= 1
        elif traceback[i][j] == 'left':
            aligned_seq1 += '-'
            aligned_seq2 += seq2[j - 1]
            j -= 1

    return aligned_seq1[::-1], aligned_seq2[::-1]

def hamming_distance(read, reference):
    return sum(1 for a, b in zip(read, reference) if a != b)

def map_reads_to_genome(reads, genome):

    kmer_size = 15
    genome_index = build_index(genome, kmer_size)
    read_to_genome = {}

    for read_id, sequence in reads.items():
        read_length = len(sequence)
        best_hamming = float('inf')
        matched = False

        for i in range(len(sequence) - kmer_size + 1):
            kmer = sequence[i:i + kmer_size]
            if kmer in genome_index:

                for pos in genome_index[kmer]:

                    start_pos = max(0, pos - i)
                    end_pos = min(len(genome), start_pos + read_length + 2)

                    if end_pos - start_pos < read_length - 1:
                        continue

                    genome_segment = genome[start_pos:end_pos]

                    if len(genome_segment) == len(sequence):
                        ham_dist = sum(1 for a, b in zip(sequence, genome_segment) if a != b)
                        if ham_dist <= 5:
                            read_to_genome[read_id] = [start_pos]
                            matched = True
                            break

                    if not matched:
                        aligned_read, aligned_genome = needleman_wunsch(sequence, genome_segment)
                        ham_dist = sum(1 for a, b in zip(aligned_read, aligned_genome) if a != b)
                        if ham_dist <= 5:
                            read_to_genome[read_id] = [start_pos]
                            matched = True
                            break

            if matched:
                break

    return read_to_genome

def genome_threshold_checker(reads, genomes):
    actual_genomes = {}
    genome_number_pattern = re.compile(r'genome_(\d+)')

    for genome_filename, genome in genomes.items():
        match = genome_number_pattern.search(genome_filename)
        if not match:
            continue
        genome_index = int(match.group(1))

        read_genome_map = map_reads_to_genome(reads, genome)

        if len(read_genome_map) > 100:

            for read_id, positions in read_genome_map.items():
                read_genome_map[read_id] = ["Genome_Number_" + str(genome_index)] * len(positions)


            for read_id, genome_labels in read_genome_map.items():
                if read_id not in actual_genomes:
                    actual_genomes[read_id] = genome_labels[0]

    sorted_actual_genomes = {
        k: actual_genomes[k]
        for k in sorted(actual_genomes, key=lambda x: int(re.search(r'\d+', x).group()))
    }

    return sorted_actual_genomes

def output_file_generator(reads, genomes, output_file):
  final_genomes = genome_threshold_checker(reads, genomes)

  with open(output_file, 'w') as f:
        for read_id, genome_label in final_genomes.items():
            f.write(f">{read_id}\t{genome_label}\n")

def main():
    zip_path = "project1d-files.zip"
    extract_to = "project1d-files"

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    directory = "project1d-files"
    reads_file = "project1d_reads.fasta"
    output_file = "output_project1d.txt"

    reads = load_fasta(reads_file)
    genome_filters = build_genome_bloom_filters(directory)
    present_genomes = identify_present_genomes(reads, genome_filters)
    genomes = {g: load_fasta(os.path.join(directory, g)) for g in present_genomes}
    print(f"genomes: {genomes}")
    # Now classify reads only against identified genomes
    output_file_generator(reads, genomes, "output_genomes_project1d.txt")


if __name__ == "__main__":
    main()