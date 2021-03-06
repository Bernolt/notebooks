# flake8: noqa

import pyarrow.feather as feather
import pandas as pd
import json
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pandas.util.testing import rands
import gc
import time


def get_timing(f, niter):
    start = time.clock_gettime(time.CLOCK_REALTIME)
    for i in range(niter):
        f()
    result = (time.clock_gettime(time.CLOCK_REALTIME) - start) / niter
    return result


class Benchmarker:

    def __init__(self, file_info):
        self.base = file_info['base']
        (self.csv_path,
         self.sep,
         self.header) = unpack(file_info['source'], 'path', 'sep', 'header')

        self.parquet_unc_path = '{}_uncompressed.parquet'.format(self.base)
        self.parquet_snappy_path = '{}_snappy.parquet'.format(self.base)
        self.feather_unc_path = '{}_uncompressed.feather'.format(self.base)
        self.feather_lz4_path = '{}_lz4.feather'.format(self.base)
        self.feather_zstd_path = '{}_zstd.feather'.format(self.base)

    def bench_read(self, niter=5):
        cases = [
            ('parquet (UNC)', 'arrow Table',
             lambda: pq.read_table(self.parquet_unc_path, memory_map=False)),
            ('parquet (UNC)', 'pandas',
             lambda: (pq.read_table(self.parquet_unc_path, memory_map=False)
                      .to_pandas())),
            ('parquet (SNAPPY)', 'arrow Table',
             lambda: pq.read_table(self.parquet_snappy_path,
                                   memory_map=False)),
            ('parquet (SNAPPY)', 'pandas',
             lambda: (pq.read_table(self.parquet_snappy_path, memory_map=False)
                      .to_pandas())),
            ('feather V2 (UNC)', 'pandas',
             lambda: feather.read_feather(self.feather_unc_path,
                                          memory_map=False)),
            ('feather V2 (LZ4)', 'pandas',
             lambda: feather.read_feather(self.feather_lz4_path,
                                          memory_map=False)),
            ('feather V2 (ZSTD)', 'pandas',
             lambda: feather.read_feather(self.feather_zstd_path,
                                          memory_map=False)),
            ('feather V2 (UNC)', 'arrow Table',
             lambda: feather.read_table(self.feather_unc_path,
                                        memory_map=False)),
            ('feather V2 (LZ4)', 'arrow Table',
             lambda: feather.read_table(self.feather_lz4_path,
                                        memory_map=False)),
            ('feather V2 (ZSTD)', 'arrow Table',
             lambda: feather.read_table(self.feather_zstd_path,
                                        memory_map=False)),
        ]

        return self._bench_cases(cases, niter)

    def bench_write(self, niter=2):
        print("Reading text file: {}".format(self.csv_path))
        df = pd.read_csv(self.csv_path, sep=self.sep, header=self.header,
                         low_memory=False)
        if self.header is None:
            df.columns = ['f{}'.format(i) for i in range(len(df.columns))]

        def _get_table(df):
            return (pa.Table.from_pandas(df, preserve_index=False)
                    .replace_schema_metadata(None))

        t = _get_table(df)

        cases = [
            ('parquet (UNC)', 'arrow Table',
             lambda: pq.write_table(t, self.parquet_unc_path,
                                    compression='NONE')),
            ('parquet (UNC)', 'pandas',
             lambda: pq.write_table(_get_table(df), self.parquet_unc_path,
                                    compression='NONE')),
            ('parquet (SNAPPY)', 'arrow Table',
             lambda: pq.write_table(t, self.parquet_snappy_path)),
            ('parquet (SNAPPY)', 'pandas',
             lambda: pq.write_table(_get_table(df), self.parquet_snappy_path)),
            ('feather V2 (UNC)', 'pandas',
             lambda: feather.write_feather(df, self.feather_unc_path,
                                           compression='uncompressed')),
            ('feather V2 (UNC)', 'arrow Table',
             lambda: feather.write_feather(t, self.feather_unc_path,
                                           compression='uncompressed')),
            ('feather V2 (LZ4)', 'pandas',
             lambda: feather.write_feather(df, self.feather_lz4_path,
                                           compression='lz4')),
            ('feather V2 (LZ4)', 'arrow Table',
             lambda: feather.write_feather(t, self.feather_lz4_path,
                                           compression='lz4')),
            ('feather V2 (ZSTD)', 'pandas',
             lambda: feather.write_feather(df, self.feather_zstd_path,
                                           compression='zstd')),
            ('feather V2 (ZSTD)', 'arrow Table',
             lambda: feather.write_feather(t, self.feather_zstd_path,
                                           compression='zstd'))
        ]

        return self._bench_cases(cases, niter)

    def _bench_cases(self, cases, niter):
        results = []
        for name, output_type, f in cases:
            print(name)
            result = (name, output_type, get_timing(f, niter))
            print(result)
            results.append(result)
        return pd.DataFrame.from_records(results,
                                         columns=['expr', 'output_type',
                                                  'mean'])


def unpack(d, *fields):
    return (d[f] for f in fields)



files = {
    'fanniemae': {
        'base': '2016Q4',
        'source': {
            'path': 'data/2016Q4.csv',
            'sep': '|',
            'header': None
        }
    },
    'nyctaxi': {
        'base': 'yellow_tripdata_2010-01',
        'source': {
            'path': 'data/yellow_tripdata_2010-01.csv',
            'sep': ',',
            'header': 0
        }
    }
}


def run_benchmarks(num_threads, what='read'):
    pa.set_cpu_count(num_threads)

    all_results = []
    for name, info in files.items():
        benchmarker = Benchmarker(info)
        if what == 'read':
            print("Benchmarking reads")
            file_results = benchmarker.bench_read()
        elif what == 'write':
            print("Benchmarking writes")
            file_results = benchmarker.bench_write()
        else:
            raise ValueError(what)
        file_results['dataset'] = name
        all_results.append(file_results)

    print(all_results)
    return pd.concat(all_results, ignore_index=True)



# for i in range(5):
#     pq.read_table('yellow_tripdata_2010-01.parquet').to_pandas()

# write_files(files)

num_threads_cases = [1, 4]

for nthreads in num_threads_cases:
    write_results = run_benchmarks(nthreads, what='write')
    write_results.to_csv('py_write_results_{}.csv'.format(nthreads))

    read_results = run_benchmarks(nthreads, what='read')
    read_results.to_csv('py_read_results_{}.csv'.format(nthreads))

# for nthreads in num_threads_cases:
#     run_benchmarks(nthreads)

# ('pyarrow.parquet', 1.5470361709594727)
# ('pyarrow.parquet-pandas', 2.925654172897339)
# ('pyarrow.feather', 1.6384665012359618)
