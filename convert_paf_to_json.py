#!/usr/bin/env python3
"""
Convert PAF alignment files to JSON format for GenomeD3Plot synteny visualization.
"""

import json
import sys
import os
from collections import defaultdict

def parse_fai(fai_file):
    """Parse FASTA index file to get sequence lengths."""
    lengths = {}
    if os.path.exists(fai_file):
        with open(fai_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    lengths[parts[0]] = int(parts[1])
    return lengths

def parse_fasta_lengths(fasta_file):
    """Parse FASTA file directly to get sequence lengths (alternative to samtools faidx)."""
    lengths = {}
    current_seq = None
    current_length = 0
    
    try:
        with open(fasta_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('>'):
                    # Save previous sequence
                    if current_seq is not None:
                        lengths[current_seq] = current_length
                    # Start new sequence
                    current_seq = line[1:].split()[0]  # Get sequence name (first word after >)
                    current_length = 0
                else:
                    # Add to current sequence length
                    current_length += len(line)
            # Don't forget the last sequence
            if current_seq is not None:
                lengths[current_seq] = current_length
    except Exception as e:
        print(f"Warning: Could not parse FASTA file {fasta_file}: {e}")
    
    return lengths

def parse_paf(paf_file, min_length=1000, min_identity=0.8):
    """Parse PAF file and extract synteny blocks."""
    synteny_blocks = []
    
    with open(paf_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            parts = line.strip().split('\t')
            if len(parts) < 12:
                continue
            
            # PAF format: query_name, query_len, query_start, query_end, strand,
            #             target_name, target_len, target_start, target_end, matches, block_len, mapq
            query_name = parts[0]
            query_len = int(parts[1])
            query_start = int(parts[2])
            query_end = int(parts[3])
            strand = parts[4]
            target_name = parts[5]
            target_len = int(parts[6])
            target_start = int(parts[7])
            target_end = int(parts[8])
            matches = int(parts[9])
            block_len = int(parts[10])
            mapq = int(parts[11])
            
            # Calculate identity
            if block_len > 0:
                identity = matches / block_len
            else:
                identity = 0
            
            # Filter by length and identity
            if (query_end - query_start) >= min_length and identity >= min_identity:
                synteny_blocks.append({
                    'query_name': query_name,
                    'query_start': query_start,
                    'query_end': query_end,
                    'query_len': query_len,
                    'target_name': target_name,
                    'target_start': target_start,
                    'target_end': target_end,
                    'target_len': target_len,
                    'strand': strand,
                    'identity': identity,
                    'matches': matches,
                    'block_len': block_len,
                    'mapq': mapq
                })
    
    return synteny_blocks

def create_genomed3plot_json(synteny_blocks, query_fai, target_fai, output_file, metadata=None):
    """Create JSON data structure for GenomeD3Plot.
    
    Args:
        synteny_blocks: List of synteny block dictionaries
        query_fai: Path to query FASTA index file or FASTA file
        target_fai: Path to target FASTA index file or FASTA file
        output_file: Path to output JSON file
        metadata: Optional dictionary with 'query_file', 'target_file', and file labels
    """
    
    # Get sequence lengths - try FAI first, fall back to parsing FASTA directly
    query_lengths = parse_fai(query_fai)
    target_lengths = parse_fai(target_fai)
    
    # If FAI files don't exist or are empty, try to get from FASTA directly
    if not query_lengths and query_fai.endswith('.fai'):
        fasta_file = query_fai[:-4]  # Remove .fai extension
        if os.path.exists(fasta_file):
            query_lengths = parse_fasta_lengths(fasta_file)
    
    if not target_lengths and target_fai.endswith('.fai'):
        fasta_file = target_fai[:-4]  # Remove .fai extension
        if os.path.exists(fasta_file):
            target_lengths = parse_fasta_lengths(fasta_file)
    
    # Group synteny blocks by query and target
    query_tracks = defaultdict(list)
    target_tracks = defaultdict(list)
    synteny_links = []
    
    for block in synteny_blocks:
        query_name = block['query_name']
        target_name = block['target_name']
        
        # Add query track region
        query_tracks[query_name].append({
            'start': block['query_start'],
            'end': block['query_end'],
            'strand': block['strand'],
            'identity': block['identity']
        })
        
        # Add target track region
        target_tracks[target_name].append({
            'start': block['target_start'],
            'end': block['target_end'],
            'strand': block['strand'],
            'identity': block['identity']
        })
        
        # Add synteny link
        synteny_links.append({
            'query_name': query_name,
            'query_start': block['query_start'],
            'query_end': block['query_end'],
            'target_name': target_name,
            'target_start': block['target_start'],
            'target_end': block['target_end'],
            'strand': block['strand'],
            'identity': block['identity']
        })
    
    # Get labels from metadata if available
    query_label = 'Assembly'
    target_label = 'Reference'
    if metadata:
        # Try to get labels from file metadata
        query_file = metadata.get('query_file')
        target_file = metadata.get('target_file')
        
        # Metadata file is always in the uploads folder
        # Try to find uploads folder - check common locations
        uploads_folders = ['uploads', os.path.join(os.path.dirname(output_file), '..', 'uploads')]
        if query_fai:
            query_dir = os.path.dirname(query_fai)
            if 'uploads' in query_dir:
                uploads_folders.insert(0, query_dir)
        
        metadata_file = None
        for folder in uploads_folders:
            candidate = os.path.join(folder, '.file_metadata.json')
            if os.path.exists(candidate):
                metadata_file = candidate
                break
        
        if metadata_file and os.path.exists(metadata_file):
            try:
                import json
                with open(metadata_file, 'r') as f:
                    file_metadata = json.load(f)
                    if query_file and query_file in file_metadata:
                        query_label = file_metadata[query_file].get('label', query_file)
                    if target_file and target_file in file_metadata:
                        target_label = file_metadata[target_file].get('label', target_file)
            except:
                pass
    
    # Create genome data structure
    genomes = {}
    
    # Query genome
    query_genome = {
        'name': query_label,
        'sequences': []
    }
    for seq_name, length in sorted(query_lengths.items(), key=lambda x: -x[1]):
        query_genome['sequences'].append({
            'name': seq_name,
            'length': length,
            'tracks': [{
                'name': 'Synteny',
                'type': 'standard',
                'regions': query_tracks.get(seq_name, [])
            }]
        })
    genomes['query'] = query_genome
    
    # Target genome (reference)
    target_genome = {
        'name': target_label,
        'sequences': []
    }
    for seq_name, length in sorted(target_lengths.items(), key=lambda x: -x[1]):
        target_genome['sequences'].append({
            'name': seq_name,
            'length': length,
            'tracks': [{
                'name': 'Synteny',
                'type': 'standard',
                'regions': target_tracks.get(seq_name, [])
            }]
        })
    genomes['target'] = target_genome
    
    # Synteny links
    output_data = {
        'genomes': genomes,
        'synteny_links': synteny_links,
        'metadata': {
            'total_blocks': len(synteny_blocks),
            'query_sequences': len(query_lengths),
            'target_sequences': len(target_lengths)
        }
    }
    
    # Write JSON file
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Created JSON file: {output_file}")
    print(f"Total synteny blocks: {len(synteny_blocks)}")
    print(f"Query sequences: {len(query_lengths)}")
    print(f"Target sequences: {len(target_lengths)}")
    
    return output_data

def main():
    if len(sys.argv) < 4:
        print("Usage: python convert_paf_to_json.py <paf_file> <query_fai> <target_fai> [output_json]")
        print("Example: python convert_paf_to_json.py ../runs_3511/alignment.paf ../runs_3511/assembly.fasta.fai ../C_glabrata_CBS138_current_chromosomes.fasta.fai")
        sys.exit(1)
    
    paf_file = sys.argv[1]
    query_fai = sys.argv[2]
    target_fai = sys.argv[3]
    output_file = sys.argv[4] if len(sys.argv) > 4 else 'synteny_data.json'
    
    if not os.path.exists(paf_file):
        print(f"Error: PAF file not found: {paf_file}")
        sys.exit(1)
    
    print(f"Parsing PAF file: {paf_file}")
    synteny_blocks = parse_paf(paf_file)
    
    print(f"Creating JSON data structure...")
    create_genomed3plot_json(synteny_blocks, query_fai, target_fai, output_file)

if __name__ == '__main__':
    main()
