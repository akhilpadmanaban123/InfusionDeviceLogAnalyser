# SilverLogsAgent

## About the Project

The SilverLogsAgent is a comprehensive application designed to analyze power log files from embedded medical devices, provide insights into battery and power-related issues, and offer a conversational interface for querying log data and system requirements. It aims to streamline the process of diagnosing device behavior by automating log analysis and providing an intelligent assistant for engineers.

## Tech Stack

*   **Backend:**
    *   **Python:** Primary programming language.
    *   **Flask:** Web framework for building RESTful APIs.
    *   **OpenRouterAI Python Client:** For interacting with Large Language Models (LLMs) for chat and summarization.
    *   **LanceDB:** An open-source, columnar, in-process database for storing and querying embeddings, used for the RAG (Retrieval Augmented Generation) system and semantic searching of requirement data
    *   **`os`, `sys`, `json`, `re`, `datetime`, `shutil`, `glob`, `gzip`, `subprocess`, `select`:** Standard Python libraries for file system operations, data handling, regular expressions, date/time manipulation, file archiving, and process management.
*   **Frontend:**
    *   **HTML, CSS:** For structuring and styling the web interface.
    *   **JavaScript (ES6 Modules):** For interactive elements, API communication, and UI manipulation.

## Design 

### 1. Service Layer (Backend)

*   **Description:** Core business logic is encapsulated within dedicated service modules (`LogAnalysisService`, `ChatService`, `LiveLogService`).
*   **Benefits:** Promotes separation of concerns, modularity, testability, and scalability by isolating specific functionalities.

### 2. Repository Pattern (Backend)

*   **Description:** The `LanceDBManager` (now `RequirementDatabase`) abstracts the data access layer for LanceDB.
*   **Benefits:** Decouples application logic from the database technology, centralizes data operations, and enhances testability.

### 3. Strategy Pattern (Backend)

*   **Description:** The `PowerLogAnalyzer` class in `powerLogAnalysis.py` uses different methods (`analyze_numeric_param`, `analyze_bitfield_param`) to handle various types of log parameters. This allows for flexible and extensible analysis.
*   **Benefits:** Enables easy addition of new analysis algorithms, improves maintainability by self-containing algorithms, and allows runtime selection of analysis strategies.

## Project Flow

1.  **Log Upload/Ingestion:**
    *   Users can upload power log files and optional message files via the `/upload_and_analyze` API endpoint.
    *   Alternatively, users can provide a local directory path containing log files using the `/analyze` chat command.
    *   The `LogAnalysisService` handles temporary storage, processing (decompression, merging), and moving files to the `dataset` folder.

2.  **Log Analysis:**
    *   Once logs are ingested, the `LogAnalysisService` triggers the `powerchunk` module to generate structured JSON chunks from the raw power log data.
    *   The `PowerLogAnalyzer` then processes these chunks, analyzing numeric parameters against defined ranges and decoding bitfield statuses using `batteryStatusDecoder`.
    *   Analysis summaries are generated and saved.

3.  **Chat Interaction (RAG System):**  
# Current Version uses Model available with my Prompting, upcoming version focusses on finetuned model.
    *   Users interact with the system via a chat interface.
    *   The `ChatService` routes user queries to the `QueryHandler`.
    *   If a query is identified as a "requirement query," the system prompts for confirmation to search the requirement database.
    *   The `RequirementDatabase` (LanceDB) stores embeddings of extracted text from PDF requirements.
    *   For requirement queries, the `QueryHandler` generates an embedding of the user's query, performs a similarity search in LanceDB, and retrieves relevant requirement snippets.
    *   These snippets, along with the user's query, are sent to an LLM (via OpenAI client) to generate a concise and relevant answer.
    *   For general power log related questions, the `QueryHandler` directly sends the query to the LLM, potentially augmented with general power log information.

4.  **Live Log Streaming:**
    *   Users can request live power log streams from a specified address of the device using the `/livepower` chat command.
    *   The `LiveLogService` establishes an SSH connection to the target device and streams the `PowerlogFile.txt` content back to the frontend as server-sent events.

## Databases

*   **LanceDB:** Used as the vector database for the RAG system. It stores embeddings of requirement documents, enabling efficient semantic search for relevant information based on user queries.

## Key Methods/Modules

*   **`backend/app.py`:** Main Flask application, defines API routes and orchestrates service calls.
*   **`backend/services/log_analysis_service.py` (`LogAnalysisService`):**
    *   `analyze_uploaded_logs()`: Handles file uploads, saving, chunking, and analysis.
    *   `initiate_path_analysis()`: Processes logs from a local directory path.
    *   `finalize_analysis()`: Completes analysis after issue name confirmation.
*   **`backend/services/chat_service.py` (`ChatService`):**
    *   `handle_chat_query()`: Main entry point for chat interactions, delegates to `QueryHandler`.
*   **`backend/services/live_log_service.py` (`LiveLogService`):**
    *   `stream_log_for_ip()`: Streams live log data over SSH.
*   **`backend/PowerLogAnalyser/powerLogAnalysis.py` (`PowerLogAnalyzer`):**
    *   `analyze_numeric_param()`: Analyzes numeric log parameters against defined ranges.
    *   `analyze_bitfield_param()`: Decodes and analyzes bitfield status parameters.
    *   `analyze_chunk()`: Orchestrates analysis for individual log chunks.
    *   `get_parameter_definitions()`: Provides definitions for log parameters.
    *   `analyze_power_log()`: Main function to analyze a full power log file.
*   **`backend/PowerLogAnalyser/batteryStatusDecoder.py` (`BatteryStatusSummarizer`):**
    *   `decode_hex_status()`: Decodes hexadecimal status values into human-readable meanings.
    *   `_explain_status_with_llm()`: Uses LLM to explain decoded statuses.
*   **`backend/chunker/powerchunk.py`:** Contains logic for splitting raw log files into manageable chunks.
*   **`backend/log_processor.py`:** Utility functions for sorting, decompressing, and merging log files.
*   **`backend/chatbot/query_handler.py` (`QueryHandler`):**
    *   `handle_query()`: Processes incoming chat queries, determines intent (requirement vs. general), and dispatches to appropriate handlers.
    *   `_handle_requirement_query()`: Manages RAG-based querying of requirements.
    *   `_sync_requirements()`: Extracts text from new PDFs and updates the LanceDB.
*   **`db/lancedb_manager.py` (`RequirementDatabase`):**
    *   `upsert_requirement()`: Inserts or updates requirement data (text and embeddings) into LanceDB.
    *   `query_similar()`: Performs similarity search on requirement embeddings.
*   **`backend/requirement_embedder/embedder.py`:** Handles text embedding generation.
*   **`backend/requirement_embedder/pdf_extractor.py`:** Extracts text content from PDF documents.
