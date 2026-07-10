---
name: ebook-search
description: 'Search and manage ebooks across local filesystems and online resources. Use when Claude needs to: (1) Find ebook files (PDF, EPUB, MOBI, etc.) on local disk or network drives, (2) Search for ebooks online from various sources, (3) Organize and catalog ebook collections, (4) Extract metadata from ebook files, or (5) Find related ebook resources and recommendations.'
---

# Ebook Search

## Overview

This skill enables comprehensive ebook search and management capabilities, covering both local file systems and online resources. It provides workflows for finding, organizing, and managing ebook collections efficiently.

## Quick Start

When asked to search for ebooks, follow these general steps:

1. **Understand the user's need**: Determine if they're looking for local files, online resources, or both
2. **Identify search criteria**: Title, author, keywords, file types, or specific content
3. **Choose appropriate search method**: Local file search, online API search, or combined approach
4. **Present results clearly**: Organized by source, relevance, or file properties

## Local Ebook Search

Search for ebook files on the local filesystem or network drives.

### Supported File Formats
- **PDF** (.pdf) - Most common ebook format
- **EPUB** (.epub) - Open standard ebook format
- **MOBI** (.mobi) - Kindle format
- **AZW/AZW3** (.azw, .azw3) - Amazon Kindle formats
- **DJVU** (.djvu) - Scanned document format
- **CHM** (.chm) - Compiled HTML help
- **CBR/CBZ** (.cbr, .cbz) - Comic book archives (may contain ebook content)

### Search Methods

#### File Name Search
Use `find` or `ls` commands to search by filename patterns:
```bash
find /path/to/search -name "*.pdf" -o -name "*.epub" -o -name "*.mobi"
```

#### Content Search
For text-based formats (PDF, EPUB), use text extraction tools:
```bash
# For PDF files using pdftotext (requires poppler-utils)
pdftotext file.pdf - | grep -i "search term"
```

#### Directory Organization Patterns
Common ebook storage locations:
- User directories: `~/Documents/`, `~/Downloads/`, `~/Desktop/`
- Dedicated folders: `~/Books/`, `~/Ebooks/`, `~/Library/`
- Cloud storage: Dropbox, Google Drive, OneDrive sync folders

### Metadata Extraction
Extract metadata from ebook files to better identify and organize them:
- PDF metadata: Use `exiftool` or `pdfinfo`
- EPUB metadata: Parse `content.opf` file or use `epubcheck`
- File properties: Size, modification date, file type

## Online Ebook Search

Search for ebooks from online sources and repositories.

### Public Domain Sources
- **Project Gutenberg**: Over 70,000 free ebooks (use `curl` or web search)
- **Internet Archive**: Millions of scanned books (search via `ia` command)
- **Open Library**: Free ebook lending library
- **Google Books**: Partial previews and some free ebooks

### Search Techniques
1. **Web search queries**: Use specific site searches
   - `site:gutenberg.org "book title"`
   - `filetype:pdf "book title" author:name`
2. **API-based search**: When available, use structured APIs
3. **Library catalogs**: Search university and public library digital collections

### Common Patterns
- Add "free download" or "PDF download" to search terms for downloadable content
- Include filetype in search: `"book title" filetype:pdf`
- Search author name plus "ebook" or "PDF"

## Combined Search Workflow

When searching both local and online resources:

1. **First check local files** - Quickest and most reliable
2. **Search online for missing items** - Use specific criteria
3. **Cross-reference results** - Avoid duplicates, note availability
4. **Provide clear source attribution** - Indicate where each result was found

## Organization and Cataloging

Help users organize their ebook collections:

### Directory Structure Suggestions
```
~/Ebooks/
├── Fiction/
│   ├── Science Fiction/
│   ├── Fantasy/
│   └── Mystery/
├── Non-Fiction/
│   ├── Technology/
│   ├── Science/
│   └── History/
└── Reference/
    ├── Programming/
    └── Technical/
```

### File Naming Conventions
- `Author - Title (Year).pdf`
- `Author_Last, Author_First - Title.epub`
- Include ISBN or other identifiers when available

## Advanced Features

### Batch Processing
For large collections, consider:
- Renaming files in bulk to follow naming conventions
- Moving files to organized directory structures
- Creating catalog files (CSV/JSON) with metadata

### Deduplication
Identify duplicate files by:
- File hash comparison (MD5, SHA-256)
- File size and name comparison
- Content similarity checking

### Integration with Ebook Readers
Common ebook management software:
- Calibre (supports all major formats, metadata editing)
- Adobe Digital Editions (EPUB/PDF management)
- Kindle management tools

## Resources

This skill includes bundled resources to support ebook search and management tasks:

### scripts/search_ebooks.py
Python script for searching ebook files on the local filesystem.

**Usage:**
```bash
python scripts/search_ebooks.py [directory] [options]

# Examples:
python scripts/search_ebooks.py ~/Documents
python scripts/search_ebooks.py . -e .pdf .epub
python scripts/search_ebooks.py /path/to/search -r false -d
```

**Options:**
- `directory`: Directory to search (default: current directory)
- `-e, --extensions`: File extensions to search for (e.g., .pdf .epub)
- `-r, --recursive`: Search subdirectories (default: True)
- `-d, --details`: Show detailed file information
- `-l, --limit`: Maximum number of results (default: 100)

**Features:**
- Supports all major ebook formats (PDF, EPUB, MOBI, AZW, etc.)
- Recursive or non-recursive search
- File size display
- Detailed metadata output option

### references/online_sources.md
Comprehensive guide to online ebook sources, APIs, and search techniques.

**Contents:**
- Public domain and free ebook sources (Project Gutenberg, Internet Archive, etc.)
- Search techniques and patterns
- API access examples
- Legal considerations
- Advanced search strategies

**When to use:** Load this reference when searching for ebooks online or when users need information about legal ebook sources.

### assets/ebook_catalog_template.csv
Template CSV file for cataloging ebook collections.

**Usage:**
- Copy and modify for personal ebook catalogs
- Use as a template for organizing ebook metadata
- Import into spreadsheet software or database systems

**Columns included:**
- Title, Author, Year, Format, File_Path, File_Size_MB, ISBN, Category, Notes, Source

**Tips:**
- Customize columns based on your needs
- Use as a starting point for more detailed catalogs
- Can be converted to other formats (JSON, SQL, etc.) as needed