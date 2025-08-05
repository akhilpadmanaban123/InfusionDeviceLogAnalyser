import os
import shutil
import json
import re
from PowerLogAnalyser import powerLogAnalysis
from chunker.powerchunk import generate_chunks
from log_processor import process_logs_from_path
from config import UPLOAD_FOLDER, DATASET_FOLDER


# Summary: This service handles the analysis of log files, including merging logs from a 
# directory, generating chunks, and analyzing power logs. 
# It supports both direct file uploads and path-based analysis.
class LogAnalysisService:
    def __init__(self, dataset_folder):
        self.dataset_folder = dataset_folder
        self.pending_analysis = {}

    def is_awaiting_issue_name(self, session_id):
        return self.pending_analysis.get(session_id, {}).get('status') == 'awaiting_name'

    def initiate_path_analysis(self, session_id, raw_log_path):
        log_path = os.path.normpath(raw_log_path)

        if not os.path.isdir(log_path):
            return {'error': 'The provided path does not exist or is not a directory.'}

        normalized_log_path = os.path.normcase(log_path)
        expected_suffix = os.path.normcase(os.path.join('var', 'log'))

        if not normalized_log_path.endswith(expected_suffix):
            expected_path_suffix = os.path.join("var", "log")
            return {'error': f'Invalid /analyze command. The provided path must end with \'{expected_path_suffix}\'.'}
        
        merged_powerlog_path, merged_messages_path = process_logs_from_path(log_path, self.dataset_folder)
        self.pending_analysis[session_id] = {
            'powerlog_path': merged_powerlog_path,
            'message_path': merged_messages_path,
            'status': 'awaiting_name'
        }
        return {'response': "Analysis of the logs is complete. Please provide a name for this issue."}

    def finalize_analysis(self, session_id, issue_name):
        analysis_data = self.pending_analysis.pop(session_id)
        powerlog_path = analysis_data['powerlog_path']
        message_path = analysis_data['message_path']

        issue_dir = os.path.join(self.dataset_folder, issue_name)
        os.makedirs(issue_dir, exist_ok=True)

        final_powerlog_path = os.path.join(issue_dir, 'PowerlogFile.txt')
        final_message_path = os.path.join(issue_dir, 'messages')
        shutil.copy(powerlog_path, final_powerlog_path)
        shutil.copy(message_path, final_message_path)

        chunks_json_path = generate_chunks(final_powerlog_path, issue_dir, issue_name)
        if chunks_json_path is None:
            raise Exception("Failed to generate chunks.")

        powerLogAnalysis.analyze_power_log(chunks_json_path)
        
        temp_merged_logs_dir = os.path.dirname(powerlog_path)
        if os.path.exists(temp_merged_logs_dir):
            shutil.rmtree(temp_merged_logs_dir)

        return {
            'response': f'Analysis complete. Report \'{issue_name}\' is ready.',
            'report_ready': True,
            'issue_name': issue_name
        }

    def analyze_uploaded_logs(self, powerlog_file, message_file, issue_name):
        temp_upload_dir = os.path.join(UPLOAD_FOLDER, 'temp_upload_' + str(os.getpid()))
        os.makedirs(temp_upload_dir, exist_ok=True)

        temp_powerlog_path = os.path.join(temp_upload_dir, 'PowerlogFile.txt')
        powerlog_file.save(temp_powerlog_path)

        temp_message_path = None
        if message_file and message_file.filename != '':
            temp_message_path = os.path.join(temp_upload_dir, 'messages')
            message_file.save(temp_message_path)

        issue_dir = os.path.join(self.dataset_folder, issue_name)
        os.makedirs(issue_dir, exist_ok=True)

        final_powerlog_path = os.path.join(issue_dir, 'PowerlogFile.txt')
        final_message_path = os.path.join(issue_dir, 'messages')
        shutil.copy(temp_powerlog_path, final_powerlog_path)
        if temp_message_path:
            shutil.copy(temp_message_path, final_message_path)

        chunks_json_path = generate_chunks(final_powerlog_path, issue_dir, issue_name)
        if chunks_json_path is None:
            raise Exception("Failed to generate chunks.")

        powerLogAnalysis.analyze_power_log(chunks_json_path)
        
        if os.path.exists(temp_upload_dir):
            shutil.rmtree(temp_upload_dir)

        return {'message': 'Analysis complete', 'issue_name': issue_name}