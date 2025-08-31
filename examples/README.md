# TheArk Comprehensive Demo

This directory contains a comprehensive demo script that showcases all major functionality of TheArk - ArXiv Paper Discovery and Summarization System.

## Demo Overview

The `theark_demo.py` script provides a complete demonstration of TheArk's capabilities, including:

- **Database Management**: Setting up and managing the demo database
- **Crawl Execution State**: Testing state management for background crawling
- **Category Parsing**: Validating ArXiv category parsing
- **Progress Tracking**: Testing crawl progress persistence
- **Paper Processing**: Real ArXiv API integration and paper discovery
- **Error Handling**: Retry mechanisms and error recovery
- **Background Service**: Full background paper discovery service
- **Database Statistics**: Viewing collected data and statistics

## Quick Start

### Prerequisites

- Python 3.11+
- Internet connection (for ArXiv API calls)
- TheArk project dependencies installed

### Running the Demo

```bash
# Run the comprehensive demo
uv run python examples/theark_demo.py
```

### Demo Database

The demo uses a dedicated database file: `db/theark.demo.db`

- **Location**: `db/theark.demo.db`
- **Purpose**: Isolated demo environment
- **Content**: Papers, summaries, crawl progress, and execution state
- **Persistence**: Data persists between demo runs

## Demo Features

### 1. Database Setup
- Creates demo database with all required tables
- Initializes database schema and connections
- Provides database information and statistics

### 2. Core Functionality Tests
- **CrawlExecutionState**: Tests state management for background crawling
- **Category Parsing**: Validates ArXiv category format and parsing
- **Progress Tracking**: Tests crawl progress saving and loading
- **Paper Processing**: Real ArXiv API integration with paper discovery
- **Error Handling**: Demonstrates retry mechanisms and error recovery

### 3. Background Service Demo
- Runs the full background paper discovery service
- Processes multiple ArXiv categories (cs.AI, cs.LG, cs.CL)
- Demonstrates real-time paper discovery and storage
- Shows graceful shutdown handling

### 4. Database Statistics
- Displays database size and file information
- Shows counts of papers, summaries, and progress entries
- Provides insights into collected data

## Expected Output

```
=== TheArk Comprehensive Demo ===
This demo will test all major functionality of TheArk
Database: db/theark.demo.db

=== Setting up Demo Database ===
Database path: db/theark.demo.db
Creating database engine for: sqlite:///db/theark.demo.db
Creating database tables...
✅ Database setup completed

=== Testing CrawlExecutionState ===
Created new state: historical_crawl_index=0 state_id=1...
Updated state: historical_crawl_index=10 state_id=1...
✅ CrawlExecutionState tests completed

=== Testing Category Parsing ===
Parsed categories: ['cs.AI', 'cs.LG', 'cs.CL']
Correctly caught invalid category: Invalid ArXiv category format: invalid.category
✅ Category parsing tests completed

=== Testing Progress Tracking ===
Progress tracking works: date=2024-01-15, index=5
New day progress: date=2024-01-16, index=0
✅ Progress tracking tests completed

=== Testing Paper Processing ===
Testing category processing (this may take a moment)...
Using date: 2025-08-30
Starting to process category cs.AI for date 2025-08-30
Category processing result: 3 processed, 0 failed
✅ Paper processing tests completed

=== Testing Error Handling ===
Retry result: success
✅ Error handling tests completed

=== Running Background Service Demo (2 minutes) ===
Press Ctrl+C to stop early
Starting ArXiv background explorer service
Processing categories: cs.AI, cs.LG, cs.CL
...
Demo finished. Total runtime: 0:02:00

=== Database Information ===
Database path: db/theark.demo.db
Database size: 245760 bytes
Papers in database: 15
Summaries in database: 0
Crawl progress entries: 6
✅ Database information displayed

🎉 Comprehensive demo completed successfully!
Check the database for detailed results:
  Database: db/theark.demo.db
  You can use the web interface to view papers and summaries
```

## Demo Configuration

The demo uses conservative settings for ArXiv API calls:

- **Paper interval**: 2 seconds between paper requests
- **Fetch interval**: 1 minute between category cycles
- **Retry attempts**: 3 attempts with exponential backoff
- **Categories**: cs.AI, cs.LG, cs.CL (Computer Science categories)
- **Duration**: 2 minutes (configurable)

## After the Demo

### Viewing Results

1. **Database**: Check `db/theark.demo.db` for collected data
2. **Web Interface**: Start the main application to view papers and summaries
3. **API**: Use the REST API to access collected data

### Starting the Web Interface

```bash
# Start the main application
./scripts/run/start.sh

# Access the web interface
# http://localhost:8000
```

### Database Inspection

```bash
# Use SQLite to inspect the demo database
sqlite3 db/theark.demo.db

# Example queries:
.tables                    # List all tables
SELECT COUNT(*) FROM paper;  # Count papers
SELECT * FROM paper LIMIT 5; # View recent papers
.quit                      # Exit
```

## Troubleshooting

### Common Issues

1. **Network Errors**: Ensure internet connectivity for ArXiv API calls
2. **Rate Limiting**: ArXiv has rate limits; the demo uses conservative timing
3. **Database Permissions**: Ensure write permissions for `db/` directory
4. **Dependencies**: Ensure all project dependencies are installed

### Demo Interruption

- Press `Ctrl+C` to stop the demo gracefully
- The demo will save progress and shut down cleanly
- Data collected before interruption is preserved

## Customization

### Modifying Demo Settings

Edit `theark_demo.py` to customize:

- **Categories**: Change the ArXiv categories to process
- **Duration**: Modify the background service runtime
- **Database Path**: Use a different database location
- **Logging Level**: Adjust verbosity of output

### Adding Features

The demo is designed to be extensible:

- Add new test functions to `TheArkDemo` class
- Integrate additional ArXiv categories
- Add custom database queries and statistics
- Extend error handling and retry logic

## Support

For issues with the demo:

1. Check the logs for detailed error messages
2. Verify network connectivity and ArXiv API access
3. Ensure all dependencies are properly installed
4. Review the main project documentation

The demo provides a comprehensive overview of TheArk's capabilities and serves as both a testing tool and a learning resource for understanding the system's architecture and functionality.
