# SimpleSyntenyViewer

A web-based synteny visualization tool using D3.js to visualize synteny blocks between assembly contigs and reference genomes. Supports both static file viewing and dynamic comparison generation via Flask backend.

## Features

- **Interactive synteny visualization** showing links between assembly contigs and reference chromosomes
- **File upload and management** - Upload multiple FASTA files
- **Dynamic comparison generation** - Run minimap2 alignments and create comparisons on-the-fly
- **Multiple comparison support** - Compare any pair of uploaded genomes
- **Color-coded links** based on alignment identity:
  - Green: ≥95% identity
  - Blue: ≥90% identity
  - Orange: ≥85% identity
  - Red: <85% identity
- **Filterable by minimum identity threshold**
- **Hover tooltips** showing detailed alignment information
- **Image export** - Download visualizations as PNG
- **Horizontal scrolling** for large genomes

## Files

- `app.py` - Flask backend server for file uploads and alignment
- `convert_paf_to_json.py` - Python script to convert PAF alignment files to JSON format
- `index.html` - Interactive HTML visualization using D3.js
- `requirements.txt` - Python dependencies
- `run.sh` - Script to run static file server
- `run_flask.sh` - Script to run Flask server
- `run_ngrok.sh` - Script to run with ngrok tunnel
- `synteny_data.json` - Example JSON data file

## Setup

### Prerequisites

- Python 3.7+
- [minimap2](https://github.com/lh3/minimap2) installed and in PATH
- [samtools](https://github.com/samtools/samtools) installed and in PATH

### Installation

1. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Verify minimap2 and samtools are installed:**

   ```bash
   minimap2 --version
   samtools --version
   ```

## Usage

### Option 1: Flask Server (Recommended for file uploads and comparisons)

1. **Start the Flask server:**

   ```bash
   ./run_flask.sh
   ```
   
   Or manually:
   ```bash
   python3 app.py
   ```

2. **Open in browser:**
   
   Navigate to `http://localhost:5000`

3. **Upload FASTA files:**
   - Click "Choose Files" and select one or more FASTA files
   - Click "Upload"
   - Files will appear in the file list

4. **Create a comparison:**
   - Select a query (assembly) file from the first dropdown
   - Select a target (reference) file from the second dropdown
   - Click "Align & Generate"
   - Wait for minimap2 to complete (may take a while for large files)

5. **View comparison:**
   - Select a comparison from the dropdown
   - The visualization will load automatically

### Option 2: Static File Server (For pre-generated data)

1. **Generate the JSON data file (if needed):**

   ```bash
   python convert_paf_to_json.py <paf_file> <query_fai> <target_fai> synteny_data.json
   ```

   Example:
   ```bash
   python convert_paf_to_json.py ../runs_3511/alignment.paf ../runs_3511/assembly.fasta.fai ../C_glabrata_CBS138_current_chromosomes.fasta.fai synteny_data.json
   ```

2. **Start the static server:**

   ```bash
   ./run.sh
   ```

3. **Open in browser:**
   
   Navigate to `http://localhost:8000`

### Option 3: Share via ngrok

1. **Start Flask server with ngrok:**

   ```bash
   ./run_ngrok.sh
   ```

2. **Share the ngrok URL** shown in the terminal

## Features

- Interactive synteny visualization showing links between assembly contigs and reference chromosomes
- Color-coded links based on alignment identity:
  - Green: ≥95% identity
  - Blue: ≥90% identity
  - Orange: ≥85% identity
  - Red: <85% identity
- Filterable by minimum identity threshold
- Hover tooltips showing detailed alignment information
- Linear genome view with sequences arranged horizontally

## Usage

1. Use the slider to adjust the minimum identity threshold
2. Hover over synteny links to see detailed information
3. The visualization shows:
   - Blue rectangles: Assembly contigs (top)
   - Red rectangles: Reference chromosomes (bottom)
   - Colored curves: Synteny links between them

## Customization

You can modify the visualization by editing `index.html`:
- Adjust `width` and `height` variables to change plot size
- Modify color schemes in the `getColorForIdentity()` function
- Change filtering parameters in `convert_paf_to_json.py`
