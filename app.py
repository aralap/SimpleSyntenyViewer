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
METADATA_FILE = os.path.join(UPLOAD_FOLDER, '.file_metadata.json')
ALLOWED_EXTENSIONS = {'fasta', 'fa', 'fna'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPARISONS_FOLDER, exist_ok=True)

def load_file_metadata():
    """Load file metadata (labels) from JSON file"""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_file_metadata(metadata):
    """Save file metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

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
    
    # Check if file already exists and handle naming
    original_filename = file.filename
    filename = original_filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # Save to temporary location first to calculate hash
    temp_path = os.path.join(UPLOAD_FOLDER, f'.temp_{filename}')
    file.save(temp_path)
    
    # Calculate hash of uploaded file
    new_file_hash = get_file_hash(temp_path)
    
    # Check if file with same name exists
    if os.path.exists(filepath):
        existing_hash = get_file_hash(filepath)
        
        # If it's the same file (same hash), just return existing metadata
        if existing_hash == new_file_hash:
            os.remove(temp_path)  # Remove temp file
            metadata = load_file_metadata()
            file_info = metadata.get(filename, {})
            return jsonify({
                'filename': filename,
                'label': file_info.get('label', filename),
                'hash': existing_hash,
                'size': os.path.getsize(filepath),
                'path': filepath,
                'message': 'File already exists (same content)'
            })
        
        # Different file with same name - rename with suffix
        base_name, ext = os.path.splitext(original_filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
    
    # Move temp file to final location
    os.rename(temp_path, filepath)
    
    # Get file info
    file_hash = new_file_hash  # Use the hash we already calculated
    file_size = os.path.getsize(filepath)
    
    # Create index if it doesn't exist (optional - we can parse FASTA directly)
    # Indexing with samtools is faster for large files, but not required
    index_file = filepath + '.fai'
    if not os.path.exists(index_file):
        try:
            # Try samtools first (faster for large files)
            subprocess.run(['samtools', 'faidx', filepath], check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # If samtools fails or isn't available, we'll parse FASTA directly when needed
            # This is fine - the index is just an optimization
            pass
    
    # Load and update metadata
    metadata = load_file_metadata()
    if filename not in metadata:
        metadata[filename] = {'label': filename}  # Default label is filename
    save_file_metadata(metadata)
    
    return jsonify({
        'filename': filename,
        'label': metadata[filename].get('label', filename),
        'hash': file_hash,
        'size': file_size,
        'path': filepath,
        'renamed': filename != original_filename
    })

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded FASTA files"""
    metadata = load_file_metadata()
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if allowed_file(filename) and not filename.endswith('.fai') and filename != '.file_metadata.json':
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file_info = metadata.get(filename, {})
            files.append({
                'filename': filename,
                'label': file_info.get('label', filename),
                'size': os.path.getsize(filepath),
                'hash': get_file_hash(filepath)
            })
    return jsonify({'files': files})

@app.route('/api/files/<filename>/label', methods=['PUT'])
def update_file_label(filename):
    """Update the label for a file"""
    data = request.json
    new_label = data.get('label', '').strip()
    
    if not new_label:
        return jsonify({'error': 'Label cannot be empty'}), 400
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    # Update metadata
    metadata = load_file_metadata()
    if filename not in metadata:
        metadata[filename] = {}
    metadata[filename]['label'] = new_label
    save_file_metadata(metadata)
    
    return jsonify({
        'filename': filename,
        'label': new_label,
        'status': 'success'
    })

@app.route('/api/align', methods=['POST'])
def run_alignment():
    """Run minimap2 alignment between two FASTA files"""
    data = request.json
    query_file = data.get('query_file')
    target_file = data.get('target_file')
    comparison_label = data.get('label', None)
    
    # Get minimap2 parameters
    preset = data.get('preset', 'asm5')
    no_long_join = data.get('no_long_join', False)
    min_occ_floor = data.get('min_occ_floor', None)
    output_cigar = data.get('output_cigar', True)
    
    if not query_file or not target_file:
        return jsonify({'error': 'Both query_file and target_file are required'}), 400
    
    query_path = os.path.join(UPLOAD_FOLDER, query_file)
    target_path = os.path.join(UPLOAD_FOLDER, target_file)
    
    if not os.path.exists(query_path):
        return jsonify({'error': f'Query file not found: {query_file}'}), 404
    
    if not os.path.exists(target_path):
        return jsonify({'error': f'Target file not found: {target_file}'}), 404
    
    # Build minimap2 command
    minimap2_cmd = ['minimap2', '-x', preset]
    
    if output_cigar:
        minimap2_cmd.append('-c')
    
    if no_long_join:
        minimap2_cmd.extend(['--no-long-join', '-r', '200'])
    
    if min_occ_floor is not None:
        minimap2_cmd.extend(['--min-occ-floor', str(min_occ_floor)])
    
    # Add target and query paths
    minimap2_cmd.extend([target_path, query_path])
    
    # Create comparison ID including parameters for uniqueness
    query_hash = get_file_hash(query_path)[:8]
    target_hash = get_file_hash(target_path)[:8]
    params_hash = hashlib.md5(
        f"{preset}_{no_long_join}_{min_occ_floor}_{output_cigar}".encode()
    ).hexdigest()[:6]
    comparison_id = f"{query_hash}_{target_hash}_{params_hash}"
    
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
                minimap2_cmd,
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
    
    # Get index files (optional - we can parse FASTA directly if they don't exist)
    query_fai = query_path + '.fai'
    target_fai = target_path + '.fai'
    
    # Try to create indexes if they don't exist (optional optimization)
    if not os.path.exists(query_fai):
        try:
            subprocess.run(['samtools', 'faidx', query_path], check=True, timeout=60, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass  # Will parse FASTA directly if index doesn't exist
    
    if not os.path.exists(target_fai):
        try:
            subprocess.run(['samtools', 'faidx', target_path], check=True, timeout=60, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass  # Will parse FASTA directly if index doesn't exist
    
    # Convert PAF to JSON
    try:
        synteny_blocks = parse_paf(paf_file)
        # Pass FASTA paths as fallback if FAI files don't exist
        # Also pass metadata with file names so labels can be retrieved
        create_genomed3plot_json(
            synteny_blocks, 
            query_fai or query_path, 
            target_fai or target_path, 
            json_file,
            metadata={'query_file': query_file, 'target_file': target_file}
        )
        
        # Add parameters and label to JSON metadata
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        json_data['parameters'] = {
            'preset': preset,
            'no_long_join': no_long_join,
            'min_occ_floor': min_occ_floor,
            'output_cigar': output_cigar,
            'minimap2_command': ' '.join(minimap2_cmd)
        }
        if comparison_label:
            json_data['label'] = comparison_label
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
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
        'label': comparison_label,
        'paf_file': paf_file,
        'json_file': json_file,
        'parameters': {
            'preset': preset,
            'no_long_join': no_long_join,
            'min_occ_floor': min_occ_floor,
            'output_cigar': output_cigar
        }
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
                    
                    # Try to get parameters from filename or metadata
                    params_info = ''
                    if '_' in comparison_id:
                        # Parameters hash is in the ID, but we can't decode it easily
                        # Store params in a separate file or in JSON metadata
                        pass
                    
                    comparisons.append({
                        'comparison_id': comparison_id,
                        'label': data.get('label', None),
                        'query_name': genomes.get('query', {}).get('name', 'Unknown'),
                        'target_name': genomes.get('target', {}).get('name', 'Unknown'),
                        'total_blocks': metadata.get('total_blocks', 0),
                        'query_sequences': metadata.get('query_sequences', 0),
                        'target_sequences': metadata.get('target_sequences', 0),
                        'parameters': data.get('parameters', {})
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

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a FASTA file and its associated files"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    # Check if file is used in any comparisons
    metadata = load_file_metadata()
    comparisons = []
    for comp_file in os.listdir(COMPARISONS_FOLDER):
        if comp_file.endswith('.json'):
            try:
                with open(os.path.join(COMPARISONS_FOLDER, comp_file), 'r') as f:
                    comp_data = json.load(f)
                    if comp_data.get('metadata', {}).get('query_file') == filename or \
                       comp_data.get('metadata', {}).get('target_file') == filename:
                        comparisons.append(comp_file)
            except:
                pass
    
    if comparisons:
        return jsonify({
            'error': 'File is used in comparisons and cannot be deleted',
            'comparisons': comparisons
        }), 400
    
    # Delete the file and associated files
    deleted = []
    if os.path.exists(filepath):
        os.remove(filepath)
        deleted.append('file')
    
    # Delete index file if it exists
    index_file = filepath + '.fai'
    if os.path.exists(index_file):
        os.remove(index_file)
        deleted.append('index')
    
    # Remove from metadata
    if filename in metadata:
        del metadata[filename]
        save_file_metadata(metadata)
    
    return jsonify({'status': 'success', 'deleted': deleted})

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
    print("Make sure minimap2 is installed and in your PATH")
    print("Note: samtools is optional (used for faster FASTA indexing)")
    app.run(debug=True, host='0.0.0.0', port=5005)
