#!/bin/bash

# Convert all presentations to HTML, PDF, and PNG slides

PRESENTATIONS_DIR="presentations"
OUTPUT_DIR="output"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "Converting all presentations..."
echo ""

# Find all markdown files in presentation folders
find "$PRESENTATIONS_DIR" -mindepth 2 -maxdepth 2 -name "*.md" -type f | while read md_file; do
    # Get presentation directory and name
    pres_dir=$(dirname "$md_file")
    pres_name=$(basename "$pres_dir")

    echo "Processing: $pres_name"
    echo "  Markdown file: $md_file"

    # Convert to HTML
    echo "  → Converting to HTML..."
    marp "$md_file" -o "$OUTPUT_DIR/$pres_name.html" --html --allow-local-files

    # Convert to PDF
    echo "  → Converting to PDF..."
    marp "$md_file" -o "$OUTPUT_DIR/$pres_name.pdf" --pdf --allow-local-files

    # Export individual slide images
    echo "  → Exporting slide images..."
    marp "$md_file" -o "$pres_dir/slide.png" --images png --allow-local-files

    # Copy HTML and PDF to presentation folder
    echo "  → Copying files to presentation folder..."
    cp "$OUTPUT_DIR/$pres_name.html" "$pres_dir/"
    cp "$OUTPUT_DIR/$pres_name.pdf" "$pres_dir/"

    echo "  ✓ Completed: $pres_name"
    echo ""
done

echo "All presentations converted successfully!"
echo ""
echo "Updating presentations.json..."
python3 scripts/generate_index.py

echo ""
echo "Done!"
