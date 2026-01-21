#!/usr/bin/env python3
"""
Flask backend for SimpleSyntenyViewer
Handles file uploads, minimap2 alignment, and comparison management
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json
import hashlib
from pathlib import Path
from convert_paf_to_json import parse_paf, create_genomed3plot_json

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
COMPARISONS_FOLDER = 'comparisons'
ALLOWED_EXTENSIONS = {'fasta', 'fa', 'fna'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPARISONS_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_hash(filepath):
    """Get MD5 hash of file for unique identification"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_fasta():
    """Upload a FASTA file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only FASTA files are allowed.'}), 400
    
    # Save file
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Get file info
    file_hash = get_file_hash(filepath)
    file_size = os.path.getsize(filepath)
    
    # Create index if it doesn't exist
    index_file = filepath + '.fai'
    if not os.path.exists(index_file):
        try:
            subprocess.run(['samtools', 'faidx', filepath], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            return jsonify({'error': 'Failed to index FASTA file. Make sure samtools is installed.'}), 500
        except FileNotFoundError:
            return jsonify({'error': 'samtools not found. Please install samtools.'}), 500
    
    return jsonify({
        'filename': filename,
        'hash': file_hash,
        'size': file_size,
        'path': filepath
    })

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded FASTA files"""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if allowed_file(filename):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            files.append({
                'filename': filename,
                'size': os.path.getsize(filepath),
                'hash': get_file_hash(filepath)
            })
    return jsonify({'files': files})

@app.route('/api/align', methods=['POST'])
def run_alignment():
    """Run minimap2 alignment between two FASTA files"""
    data = request.json
    query_file = data.get('query_file')
    target_file = data.get('target_file')
    
    if not query_file or not target_file:
        return jsonify({'error': 'Both query_file and target_file are required'}), 400
    
    query_path = os.path.join(UPLOAD_FOLDER, query_file)
    target_path = os.path.join(UPLOAD_FOLDER, target_file)
    
    if not os.path.exists(query_path):
        return jsonify({'error': f'Query file not found: {query_file}'}), 404
    
    if not os.path.exists(target_path):
        return jsonify({'error': f'Target file not found: {target_file}'}), 404
    
    # Create comparison ID
    query_hash = get_file_hash(query_path)[:8]
    target_hash = get_file_hash(target_path)[:8]
    comparison_id = f"{query_hash}_{target_hash}"
    
    # Check if comparison already exists
    paf_file = os.path.join(COMPARISONS_FOLDER, f"{comparison_id}.paf")
    json_file = os.path.join(COMPARISONS_FOLDER, f"{comparison_id}.json")
    
    if os.path.exists(json_file):
        return jsonify({
            'comparison_id': comparison_id,
            'status': 'exists',
            'message': 'Comparison already exists'
        })
    
    # Run minimap2
    try:
        with open(paf_file, 'w') as outfile:
            result = subprocess.run(
                ['minimap2', '-x', 'asm5', '-c', target_path, query_path],
                stdout=outfile,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
    except subprocess.CalledProcessError as e:
        return jsonify({
            'error': 'Minimap2 alignment failed',
            'details': e.stderr
        }), 500
    except FileNotFoundError:
        return jsonify({'error': 'minimap2 not found. Please install minimap2.'}), 500
    
    # Get index files
    query_fai = query_path + '.fai'
    target_fai = target_path + '.fai'
    
    if not os.path.exists(query_fai):
        try:
            subprocess.run(['samtools', 'faidx', query_path], check=True)
        except:
            return jsonify({'error': 'Failed to index query file'}), 500
    
    if not os.path.exists(target_fai):
        try:
            subprocess.run(['samtools', 'faidx', target_path], check=True)
        except:
            return jsonify({'error': 'Failed to index target file'}), 500
    
    # Convert PAF to JSON
    try:
        synteny_blocks = parse_paf(paf_file)
        create_genomed3plot_json(synteny_blocks, query_fai, target_fai, json_file)
    except Exception as e:
        return jsonify({
            'error': 'Failed to convert PAF to JSON',
            'details': str(e)
        }), 500
    
    return jsonify({
        'comparison_id': comparison_id,
        'status': 'success',
        'query_file': query_file,
        'target_file': target_file,
        'paf_file': paf_file,
        'json_file': json_file
    })

@app.route('/api/comparisons', methods=['GET'])
def list_comparisons():
    """List all available comparisons"""
    comparisons = []
    for filename in os.listdir(COMPARISONS_FOLDER):
        if filename.endswith('.json'):
            comparison_id = filename[:-5]  # Remove .json extension
            json_path = os.path.join(COMPARISONS_FOLDER, filename)
            
            # Load metadata from JSON
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    metadata = data.get('metadata', {})
                    genomes = data.get('genomes', {})
                    
                    comparisons.append({
                        'comparison_id': comparison_id,
                        'query_name': genomes.get('query', {}).get('name', 'Unknown'),
                        'target_name': genomes.get('target', {}).get('name', 'Unknown'),
                        'total_blocks': metadata.get('total_blocks', 0),
                        'query_sequences': metadata.get('query_sequences', 0),
                        'target_sequences': metadata.get('target_sequences', 0)
                    })
            except:
                comparisons.append({
                    'comparison_id': comparison_id,
                    'query_name': 'Unknown',
                    'target_name': 'Unknown'
                })
    
    return jsonify({'comparisons': comparisons})

@app.route('/api/comparison/<comparison_id>/data', methods=['GET'])
def get_comparison_data(comparison_id):
    """Get JSON data for a specific comparison"""
    json_file = os.path.join(COMPARISONS_FOLDER, f"{comparison_id}.json")
    
    if not os.path.exists(json_file):
        return jsonify({'error': 'Comparison not found'}), 404
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    return jsonify(data)

@app.route('/api/comparison/<comparison_id>/delete', methods=['DELETE'])
def delete_comparison(comparison_id):
    """Delete a comparison"""
    json_file = os.path.join(COMPARISONS_FOLDER, f"{comparison_id}.json")
    paf_file = os.path.join(COMPARISONS_FOLDER, f"{comparison_id}.paf")
    
    deleted = []
    if os.path.exists(json_file):
        os.remove(json_file)
        deleted.append('json')
    
    if os.path.exists(paf_file):
        os.remove(paf_file)
        deleted.append('paf')
    
    if deleted:
        return jsonify({'status': 'success', 'deleted': deleted})
    else:
        return jsonify({'error': 'Comparison not found'}), 404

if __name__ == '__main__':
    print("Starting SimpleSyntenyViewer Flask server...")
    print("Make sure minimap2 and samtools are installed and in your PATH")
    app.run(debug=True, host='0.0.0.0', port=5000)
