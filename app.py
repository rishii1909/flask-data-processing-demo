from flask import Flask, Response, request, jsonify
from cachetools import LRUCache
import os
import threading

app = Flask(__name__)

DATA_FILE_PATH = "mock_data.txt"
DATA_FILE_SIZE = 1024 * 1024 * 200  # ~200 MB
file_lock = threading.Lock()

data_cache = LRUCache(maxsize=DATA_FILE_SIZE)

def stream_data(lines):
    for line in lines:
        yield line + '\n'

@app.route('/generate-mock-data', methods=['GET'])
def generate_mock_data():
    with file_lock:
        if os.path.exists(DATA_FILE_PATH):
            return jsonify({"message": f"{DATA_FILE_PATH} already exists", "size": os.path.getsize(DATA_FILE_PATH)}), 200
        
        with open(DATA_FILE_PATH, 'w', buffering=1024*1024) as f:
            num_lines = DATA_FILE_SIZE // 20  # Each line is about 20 bytes
            num_lines = int(num_lines) 
            step = 1.0 / num_lines
            value = 0.0
            for i in range(num_lines):
                f.write(f"[{i+1}] : {value:.15f}\n")
                value += step
        return jsonify({"message": f"{DATA_FILE_PATH} created", "size": DATA_FILE_SIZE}), 201

@app.route('/get-data', methods=['GET'])
def get_data():
    start = int(request.args.get('start', 0))
    end = int(request.args.get('end', 100))

    if start < 0 or end < start:
        return jsonify({"error": "Invalid range: 'end' should be greater than or equal to 'start' and both should be non-negative."}), 400

    if start >= DATA_FILE_SIZE:
        return jsonify({"error": "Start index is out of bounds."}), 400
    
    ensure_cache(start, end)

    data = [data_cache.get(i, "") for i in range(start, end+1)]

    return Response(stream_data(data), mimetype='text/plain')

@app.route('/fetch-data', methods=['GET'])
def fetch_data():
    if is_cache_populated():
        return jsonify({"message": f"Data already processed", "size": DATA_FILE_SIZE}), 200
    
    upsert_data_to_cache()
    return jsonify({"message": "Data processed and stored in cache", "size": DATA_FILE_SIZE}), 201

def ensure_cache(start, end):
    for i in range(start, end + 1):
        if i not in data_cache:
            with file_lock:
                try:
                    num_lines = DATA_FILE_SIZE // 20
                    step = 1.0 / num_lines
                    value = 0.0

                    for j in range(num_lines):
                        line = f"[{j}] : {value:.15f}"
                        if not line.endswith(" processed"):
                            line += " processed"
                        data_cache[j] = line
                        value += step

                    if any(k not in data_cache for k in range(start, end + 1)):
                        return False
                except Exception as e:
                    print(f"Error while populating cache: {e}")
                    return False
                return True

    print('Data already exists in cache')
    return True

def upsert_data_to_cache():
    if is_cache_populated():
        return

    with file_lock:
        try:
            num_lines = int(DATA_FILE_SIZE // 20)
            step = 1.0 / num_lines
            value = 0.0

            for i in range(num_lines):
                line = f"[{i}] : {value:.15f}"
                if not line.endswith(" processed"):
                    line += " processed"
                data_cache[i] = line
                value += step
        except Exception as e:
            print(f"Error while upserting cache: {e}")
            return

def is_cache_populated():
    cache_size = len(data_cache)
    return cache_size > 0

if __name__ == '__main__':
    app.run(debug=True)
