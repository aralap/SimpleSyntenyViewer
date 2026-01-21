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
- [minimap2](https://github.com/lh3/minimap2) installed and in PATH (required)
- [samtools](https://github.com/samtools/samtools) installed and in PATH (optional, but recommended for faster FASTA indexing)

### Installation

1. **Create virtual environment and install Python dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Install minimap2 (required) and optionally samtools:**

   **Option A: Automatic installation (recommended if you have conda/mamba):**
   
   ```bash
   python3 install.py  # Installs minimap2 and samtools
   python3 install.py --no-optional  # Installs only minimap2 (samtools optional)
   ```
   
   This will create a conda environment with the required tools. Follow the instructions to activate it or add it to your PATH.
   
   **Option B: Manual installation:**
   
   - **macOS (Homebrew):** `brew install minimap2` (add `samtools` if desired)
   - **Linux (apt):** `sudo apt-get install minimap2` (add `samtools` if desired)
   - **Conda:** `conda install -c bioconda minimap2` (add `samtools` if desired)
   
   **Note:** samtools is optional. If not installed, the app will parse FASTA files directly (slower for large files but works fine).
   
3. **Verify installation:**

   ```bash
   python3 install.py --check-only
   minimap2 --version
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

## API Endpoints

The Flask server provides the following REST API endpoints:

- `GET /` - Serve the main HTML page
- `POST /api/upload` - Upload a FASTA file
- `GET /api/files` - List all uploaded files
- `POST /api/align` - Run minimap2 alignment between two files
- `GET /api/comparisons` - List all available comparisons
- `GET /api/comparison/<id>/data` - Get JSON data for a comparison
- `DELETE /api/comparison/<id>/delete` - Delete a comparison

## Usage Tips

1. **Adjust identity threshold:** Use the slider to filter synteny links by minimum identity
2. **Hover for details:** Hover over synteny ribbons to see alignment details
3. **Download images:** Click "Download Image" to export the visualization as PNG
4. **Multiple comparisons:** Upload multiple FASTA files to compare different assemblies
5. **Large files:** Be patient when aligning large genomes - minimap2 may take several minutes

## Visualization Details

The visualization shows:
- **Blue rectangles:** Query/Assembly sequences (top row)
- **Red rectangles:** Target/Reference sequences (bottom row)
- **Colored ribbons:** Synteny links connecting aligned regions
- **Ribbon width:** Proportional to alignment block length
- **Ribbon color:** Based on alignment identity percentage

## Customization

You can modify the visualization by editing `index.html`:
- Adjust `width` and `height` variables to change plot size
- Modify color schemes in the `getColorForIdentity()` function
- Change filtering parameters in `convert_paf_to_json.py`
- Adjust alignment parameters in `app.py` (minimap2 options)

## Troubleshooting

- **"minimap2 not found"**: Make sure minimap2 is installed and in your PATH (required)
- **"samtools not found"**: This is optional. The app will work without it, but FASTA indexing will be slower for large files
- **Upload fails**: Check file size limits and ensure files are valid FASTA format
- **Alignment takes too long**: Large genomes (>100MB) may take 10+ minutes to align
- **No visualization appears**: Check browser console for errors, ensure JSON data is valid