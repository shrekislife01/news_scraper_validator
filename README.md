# Hungarian News Scraper & Validation Framework

A modular Python-based system for extracting, normalizing, storing, and validating articles from Hungarian news websites.

This repository combines two closely related projects:

1. **Automated Hungarian News Scraper**  
   A prototype pipeline that collects articles from multiple Hungarian news portals, extracts structured content and metadata, cleans the results, and stores them in a relational database.

2. **Hungarian News Scraper Validation Framework**  
   A web-based manual testing and feedback system built around the existing `NewsExtractor`, designed to evaluate extraction quality, log errors, measure scraper accuracy, and support semi-automated rule learning for improving robustness over time.

---

## Project Goal

Hungarian news websites publish a large volume of articles every day, but their HTML structures, metadata conventions, and tagging practices vary significantly. This makes unified collection and analysis difficult.

The goal of this project is to provide:

- automated article collection from multiple Hungarian news portals,
- robust article and metadata extraction,
- preprocessing and deduplication,
- structured storage for later querying and analysis,
- a simple browser-based interface for viewing or validating extracted results,
- and a validation/rule-learning layer that helps improve scraper quality over time.

The long-term vision is to create a maintainable and extensible foundation for analysis use cases such as trend tracking, source comparison, semantic search, and scraper quality evaluation.

---

## Main Features

### Automated scraping pipeline
- Collects article URLs from predefined Hungarian news portals
- Downloads article pages and extracts:
  - title
  - publication date
  - source
  - article body
  - optional metadata such as author and keywords
- Handles multiple site structures with generalized extraction logic
- Filters already processed URLs to keep the pipeline idempotent

### Content extraction
- Uses heuristic DOM scoring rather than relying only on fixed CSS selectors
- Scores candidate content blocks using signals such as:
  - text length
  - link density
  - punctuation density
  - HTML tag type preference (for example `article`)
- Tries multiple strategies for metadata extraction:
  - meta tags
  - structured JSON-LD data
  - heuristic and regex-based fallbacks

### Data cleaning and preprocessing
- Removes irrelevant HTML elements
- Normalizes textual fields
- Handles encoding issues
- Filters missing or low-quality records
- Detects and removes duplicate articles
- Ensures only consistent and queryable data is stored

### Storage and retrieval
- Stores processed articles in a relational database
- Separates metadata and content in a structured way
- Supports later filtering, browsing, and analysis
- Designed for scalability and maintainability

### Automation
- Runs the scraping and processing workflow on a schedule
- Logs execution status and failures
- Supports reruns and safe repeated execution
- Originally planned around scheduled DAG-style execution with Apache Airflow

### Manual validation framework
- Accepts a user-provided article URL from a web interface
- Runs the existing `NewsExtractor` on demand
- Displays extracted fields such as:
  - title
  - content
  - author
  - date
  - keywords
- Lets users mark each field as:
  - correct
  - incorrect
  - missing
- Allows manual correction of extracted values
- Stores validation results and comments

### Error analysis and rule-learning support
- Tracks structured error categories such as:
  - `TITLE_MISSING`
  - `AUTHOR_WRONG`
- Aggregates errors by source
- Computes field-level and source-level accuracy metrics
- Supports rule configuration, enable/disable logic, and rule testing
- Provides the basis for generating suggested new rules from frequent error patterns
- Aims to improve scraper robustness through a semi-automated feedback loop

---

## High-Level Architecture

The system is built as a modular processing pipeline with clearly separated components:

- **Scraping layer**  
  Collects article URLs and downloads article pages

- **Extraction layer**  
  Parses HTML and extracts article content and metadata using the `NewsExtractor`

- **Preprocessing layer**  
  Cleans, normalizes, filters, and deduplicates records

- **Storage layer**  
  Writes processed data into a relational database

- **Automation layer**  
  Executes scraping and processing on a schedule

- **Validation layer**  
  Runs extractor tests manually through a UI and captures feedback

- **Rule engine / metrics layer**  
  Applies post-processing rules, tracks performance, and prepares analytics

This separation keeps the codebase maintainable and makes individual parts easier to test and extend.

---

## Typical Pipeline Flow

### Automated scraper flow
1. Collect homepage article links from configured news sources
2. Filter out URLs already present in the database
3. Download and parse new article pages
4. Extract structured content and metadata
5. Clean and normalize results
6. Store processed records in the database
7. Repeat on a scheduled basis

### Validation framework flow
1. Paste a news article URL into the web interface
2. Run the scraper/extractor on that URL
3. Review the extracted fields
4. Mark field-level correctness
5. Save corrected values and notes
6. Store validation data
7. Update metrics and error statistics
8. Optionally apply or propose rules for post-processing improvements
