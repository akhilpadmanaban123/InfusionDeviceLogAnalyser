
import os, sys, json
from datetime import datetime
import re
import traceback
from flask import Flask, request, jsonify, send_from_directory, send_file, render_template
from flask_cors import CORS

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.log_analysis_service import LogAnalysisService
from services.chat_service import ChatService
from services.live_log_service import LiveLogService
from PowerLogAnalyser.powerLogAnalysis import get_parameter_definitions
from config import PROJECT_ROOT, UPLOAD_FOLDER, DATASET_FOLDER, RAG_DATA_FOLDER

app = Flask(__name__, static_folder=os.path.join(PROJECT_ROOT, 'frontend'), static_url_path='/static', template_folder=os.path.join(PROJECT_ROOT, 'frontend'))
CORS(app)

# Ensure the 'uploaded_files' directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize services
log_analysis_service = LogAnalysisService(DATASET_FOLDER)
chat_service = ChatService(RAG_DATA_FOLDER)
live_log_service = LiveLogService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_and_analyze', methods=['POST'])
def upload_and_analyze():
    if 'powerlogFile' not in request.files:
        return jsonify({'error': 'No powerlogFile part in the request'}), 400

    powerlog_file = request.files['powerlogFile']
    message_file = request.files.get('messageFile')  # messageFile is optional
    issue_name = request.form.get('issueName')

    if powerlog_file.filename == '':
        return jsonify({'error': 'No selected powerlog file'}), 400

    if not issue_name:
        return jsonify({'error': 'Issue name is required'}), 400

    try:
        result = log_analysis_service.analyze_uploaded_logs(powerlog_file, message_file, issue_name)
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred during analysis.', 'details': str(e)}), 500

@app.route('/get_summary_csv/<issue_name>', methods=['GET'])
def get_summary_csv(issue_name):
    summary_file_name = f'chunk_summary_{issue_name}.csv'
    issue_dir = os.path.join(DATASET_FOLDER, issue_name)
    
    if not os.path.exists(issue_dir):
        return jsonify({'error': 'Issue directory not found'}), 404

    try:
        return send_from_directory(issue_dir, summary_file_name, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'Summary CSV file not found for this issue'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_chunk_soc/<issue_name>/<chunk_id>', methods=['GET'])
def get_chunk_soc(issue_name, chunk_id):
    chunks_file_name = f'chunks_{issue_name}.json'
    issue_dir = os.path.join(DATASET_FOLDER, issue_name)
    chunks_file_path = os.path.join(issue_dir, chunks_file_name)

    if not os.path.exists(chunks_file_path):
        return jsonify({'error': 'Chunks file not found'}), 404

    try:
        with open(chunks_file_path, 'r') as f:
            chunks = json.load(f)
        
        for chunk in chunks:
            if chunk.get('ChunkID') == chunk_id:
                return jsonify({
                    'perc_values': chunk.get('Perc', []),
                    'soh_values': chunk.get('SOH', []),
                    'perc_time_series': chunk.get('Perc_Time_Series', []),
                    'volt_values': chunk.get('Volt', []),
                    'curr_values': chunk.get('Curr', []),
                    'temp_values': chunk.get('Temp', [])
                })
        
        return jsonify({'error': 'Chunk not found'}), 404

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error', 'details': str(e)}), 500

@app.route('/get_message_logs/<issue_name>', methods=['GET'])
def get_message_logs(issue_name):
    start_time_str = request.args.get('startTime')
    end_time_str = request.args.get('endTime')

    if not start_time_str or not end_time_str:
        return jsonify({'error': 'startTime and endTime parameters are required'}), 400

    message_file_path = os.path.join(DATASET_FOLDER, issue_name, 'messages')

    if not os.path.exists(message_file_path):
        return jsonify({'error': 'Message file not found for this issue'}), 404

    try:
        start_dt_req = datetime.strptime(start_time_str, '%m/%d/%Y %H:%M:%S')
        end_dt_req = datetime.strptime(end_time_str, '%m/%d/%Y %H:%M:%S')

        filtered_logs = []
        with open(message_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    match = re.match(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\.\d{3}', line)
                    if match:
                        log_time_str_partial = match.group(1)
                        log_time_str_full = f"{start_dt_req.year} {log_time_str_partial}"
                        log_dt = datetime.strptime(log_time_str_full, '%Y %b %d %H:%M:%S')
                        
                        if start_dt_req <= log_dt <= end_dt_req:
                            filtered_logs.append(line.strip())
                    else:
                        if filtered_logs and not re.match(r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3}', line.strip()):
                            filtered_logs.append(line.strip())

                except ValueError:
                    pass
                except Exception as e:
                    print(f"Error processing log line: {line.strip()} - {e}")
                    continue

        return jsonify({'logs': filtered_logs})

    except ValueError as ve:
        return jsonify({'error': f'Invalid time format in request or log file: {ve}. Expected MM/DD/YYYY HH:MM:SS for request parameters and Mon DD HH:MM:SS.ms for log timestamps.'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error', 'details': str(e)}), 500

@app.route('/get_powerlog_file/<issue_name>', methods=['GET'])
def get_powerlog_file(issue_name):
    powerlog_file_name = 'PowerlogFile.txt'
    issue_dir = os.path.join(DATASET_FOLDER, issue_name)
    powerlog_file_path = os.path.join(issue_dir, powerlog_file_name)

    if not os.path.exists(powerlog_file_path):
        return jsonify({'error': 'PowerlogFile.txt not found for this issue'}), 404

    try:
        return send_file(powerlog_file_path, mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_query = data.get('query')
        session_id = data.get('session_id', 'default_session')

        if not user_query:
            return jsonify({'error': 'No query provided'}), 400

        # Scenario 1: User is providing an issue name for a pending analysis
        if log_analysis_service.is_awaiting_issue_name(session_id):
            issue_name = user_query
            result = log_analysis_service.finalize_analysis(session_id, issue_name)
            return jsonify(result)

        # Scenario 2: User is requesting analysis from a local path via /analyze command
        if user_query.strip().startswith('/analyze'):
            parts = user_query.strip().split(' ', 1)
            if len(parts) > 1:
                raw_log_path = parts[1]
                result = log_analysis_service.initiate_path_analysis(session_id, raw_log_path)
                return jsonify(result)
            else:
                return jsonify({'error': "Invalid /analyze command. Please provide a valid path to the '\\logpaTH' directory."}), 400

        # Scenario 3: User is requesting a live power log stream
        elif user_query.strip().startswith('/livepower'):
            parts = user_query.strip().split(' ', 1)
            if len(parts) > 1:
                pump_ip = parts[1]
                # Validate IP address format
                if re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", pump_ip):
                    return jsonify({'action': 'open_live_log', 'pump_ip': pump_ip})
                else:
                    return jsonify({'error': 'Invalid IP address format.'}), 400
            else:
                return jsonify({'error': 'Invalid /livepower command. Please provide a device address.'}), 400

        # Scenario 4: Normal conversational query
        else:
            result = chat_service.handle_chat_query(user_query)
            return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred in the chat endpoint.', 'details': str(e)}), 500

@app.route('/get_power_log_definitions', methods=['GET'])
def get_power_log_definitions():
    param_defs, bitfield_defs = get_parameter_definitions()
    return jsonify({'parameter_definitions': param_defs, 'bitfield_definitions': bitfield_defs})

@app.route('/live_power_log/<pump_ip>')
def live_power_log(pump_ip):
    from flask import Response
    # Use the dedicated service to stream logs
    return Response(live_log_service.stream_log_for_ip(pump_ip), mimetype='text/event-stream')

@app.route('/depth_view')
def depth_view():
    return render_template('depth_view.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
