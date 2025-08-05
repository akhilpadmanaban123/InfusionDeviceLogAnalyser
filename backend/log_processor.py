import os
import glob
import gzip
import shutil
import re
from datetime import datetime

def sort_log_files(files):
    """
    #Summary:
    Sorts a list of log files based on the numeric suffix in their filenames.
    Files with no numeric suffix are sorted to the end.
     """
    def get_key(file_path):
        # This regex is designed to find the number at the end of the filename, even if it has .gz
        match = re.search(r'\.(\d+)(?:\.gz)?$', os.path.basename(file_path))
        if match:
            return int(match.group(1))
        return float('inf') # Assign infinity to files without a numeric suffix, so they come last (newest)

    # Sort files in ascending order based on the extracted number.
    # Smaller numbers (older files) come first, and files with no number come last.
    files.sort(key=get_key, reverse=False)
    return files

def decompress_and_merge(files, output_path):
    """
    Decompresses .gz files and merges them with plain text files into a single file.
    The input 'files' are assumed to be sorted from oldest to newest.
    """
    with open(output_path, 'wb') as f_out:
        for file_path in files:
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rb') as f_in:
                    shutil.copyfileobj(f_in, f_out)
            else:
                with open(file_path, 'rb') as f_in:
                    shutil.copyfileobj(f_in, f_out)

def process_logs_from_path(log_path, dataset_folder):
    """
    Finds, decompresses, sorts, and merges PowerlogFile and messages files
    from a given directory path.
    Returns the paths to the two final merged files.
    """
    message_files_raw = glob.glob(os.path.join(log_path, 'messages*'))
    powerlog_files_raw = glob.glob(os.path.join(log_path, 'PowerlogFile*'))

    # Create a set of uncompressed file paths for quick lookup
    uncompressed_message_names = {f for f in message_files_raw if not f.endswith('.gz')}
    uncompressed_powerlog_names = {f for f in powerlog_files_raw if not f.endswith('.gz')}

    final_message_files_to_process = []
    for f in message_files_raw:
        if f.endswith('.gz'):
            uncompressed_counterpart = f[:-3]
            if uncompressed_counterpart in uncompressed_message_names:
                # If uncompressed version exists, skip the .gz file
                continue
            else:
                final_message_files_to_process.append(f)
        else:
            final_message_files_to_process.append(f)

    final_powerlog_files_to_process = []
    for f in powerlog_files_raw:
        # Exclude PowerlogFile.txt.0 and its .gz version
        if re.search(r'PowerlogFileName\.txt\.0(?:\.gz)?', f):
            continue

        if f.endswith('.gz'):
            uncompressed_counterpart = f[:-3]
            if uncompressed_counterpart in uncompressed_powerlog_names:
                # If uncompressed version exists, skip the .gz file
                continue
            else:
                final_powerlog_files_to_process.append(f)
        else:
            final_powerlog_files_to_process.append(f)

    sorted_message_files = sort_log_files(list(final_message_files_to_process))
    sorted_powerlog_files = sort_log_files(list(final_powerlog_files_to_process))

    # Create a temporary directory for the merged files within the dataset_folder
    temp_dir = os.path.join(dataset_folder, 'temp_merged_logs')
    os.makedirs(temp_dir, exist_ok=True)

    merged_messages_path = os.path.join(temp_dir, 'messages')
    merged_powerlog_path = os.path.join(temp_dir, 'PowerlogFile.txt')

    # Decompress and merge the sorted files
    decompress_and_merge(sorted_message_files, merged_messages_path)
    decompress_and_merge(sorted_powerlog_files, merged_powerlog_path)

    return merged_powerlog_path, merged_messages_path