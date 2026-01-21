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

def create_genomed3plot_json(synteny_blocks, query_fai, target_fai, output_file):
    """Create JSON data structure for GenomeD3Plot."""
    
    # Get sequence lengths
    query_lengths = parse_fai(query_fai)
    target_lengths = parse_fai(target_fai)
    
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
    
    # Create genome data structure
    genomes = {}
    
    # Query genome
    query_genome = {
        'name': 'Assembly',
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
        'name': 'Reference (C_glabrata_CBS138)',
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
