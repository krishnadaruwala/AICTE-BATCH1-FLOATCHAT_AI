🌊 FloatChat AI
AI-Powered Ocean Intelligence Assistant using Argo Float Data and Retrieval-Augmented Generation (RAG)

📌 Project Overview

FloatChat AI is an intelligent oceanographic assistant that combines:

🌊 Real-time Argo Float Ocean Data
🤖 Google Gemini AI
📚 Retrieval-Augmented Generation (RAG)
🔍 Scientific Ocean Research Papers
📈 Interactive Ocean Visualizations

The system allows users to query ocean temperature, salinity, thermocline depth, float trajectories, and oceanographic concepts using natural language.

🎯 Problem Statement

Oceanographic datasets are large, complex, and difficult for researchers, students, and decision-makers to interpret quickly.

Traditional systems:

Require domain expertise
Lack conversational interaction
Cannot combine live ocean data with scientific literature
Provide limited contextual explanations

There is a need for an AI-powered assistant that can analyze ocean observations and answer scientific questions using both data and research knowledge.

💡 Proposed Solution

FloatChat AI integrates:

Argo Float observational data
Google Gemini Large Language Model
Ocean research papers converted into a searchable knowledge base
Vector Search using FAISS
Interactive Streamlit interface

The system automatically decides whether a query should:

Retrieve live ocean data
Search scientific literature
Combine both sources

to generate contextual and scientifically grounded answers.

🏗 System Architecture
                    ┌──────────────────────┐
                    │      User Query      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Streamlit Frontend │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┴──────────────────┐
          │                                       │
          ▼                                       ▼

 ┌─────────────────┐                  ┌─────────────────┐
 │  FloatChat Core │                  │ FloatChat RAG   │
 │ (Ocean Data AI) │                  │ Knowledge Base  │
 └────────┬────────┘                  └────────┬────────┘
          │                                    │
          ▼                                    ▼

 ┌─────────────────┐                 ┌──────────────────┐
 │ Argo Float Data │                 │ Research Papers  │
 │    (ERDDAP)     │                 │     (.txt)       │
 └────────┬────────┘                 └────────┬─────────┘
          │                                    │
          ▼                                    ▼

 ┌─────────────────┐                 ┌──────────────────┐
 │ Gemini Analysis │                 │ Embeddings Model │
 └────────┬────────┘                 └────────┬─────────┘
          │                                    │
          └──────────────┬─────────────────────┘
                         ▼

               ┌─────────────────┐
               │ Final Response  │
               └─────────────────┘
⚙️ Technologies Used
Component	Technology
Programming Language	Python 3.11
Frontend	Streamlit
LLM	Google Gemini
Vector Database	FAISS
Embeddings	Sentence Transformers
Data Source	Argo Float ERDDAP
Visualization	Plotly
Environment	Virtual Environment
Version Control	Git & GitHub
📂 Project Structure
FLOATCHAT_AI/
│
├── docs/
│   ├── argo_ocean_paper.md
│   ├── salinity_research.md
│   ├── indian_ocean_study.md
│
├── notebooks/
│   └── FloatChat_Development.ipynb
│
├── src/
│   ├── floatchat_app.py
│   ├── floatchat_core.py
│   ├── floatchat_rag.py
│   ├── floatchat_viz.py
│   └── build_vectorstore.py
│
├── vectorstore/
│   ├── index.faiss
│   └── index.pkl
│
├── requirements.txt
├── README.md
└── .env
🚀 Features
Ocean Data Analytics
Temperature profiles
Salinity analysis
Thermocline depth estimation
Mixed layer depth analysis
Regional ocean comparisons
AI Assistant
Natural language querying
Context-aware responses
Scientific explanations
RAG Knowledge Base
Oceanography papers
Indian Ocean studies
Salinity research
Scientific citations
Interactive Visualization
Float locations
T-S diagrams
Time-series plots
Comparative analysis charts
📷 Screenshots
Main Dashboard

Add screenshot here

screenshots/dashboard.png
Temperature Profile Analysis

Add screenshot here

screenshots/temp_profile.png
Salinity Comparison

Add screenshot here

screenshots/salinity_comparison.png
RAG-Based Scientific Query

Add screenshot here

screenshots/rag_query.png
🧠 RAG Workflow
User Question
      │
      ▼
Scientific Query Detection
      │
      ▼
Vector Search (FAISS)
      │
      ▼
Retrieve Relevant Chunks
      │
      ▼
Gemini AI
      │
      ▼
Context-Aware Answer
📥 Installation
Clone Repository
git clone https://github.com/krishnadaruwala/AICTE-BATCH1-FLOATCHAT_AI.git

cd AICTE-BATCH1-FLOATCHAT_AI
Create Virtual Environment
python -m venv .venv

Activate:

Windows

.venv\Scripts\activate

Linux/Mac

source .venv/bin/activate
Install Dependencies
pip install -r requirements.txt
Configure API Key

Create .env

GEMINI_API_KEY=YOUR_API_KEY_HERE
🔨 Build Vector Database
python src/build_vectorstore.py

Expected Output:

Vector database created successfully.
▶️ Run Application
streamlit run src/floatchat_app.py

Open:

http://localhost:8501
☁️ Deployment
Streamlit Cloud
Push project to GitHub
Login to Streamlit Cloud
Create New App
Select repository
Main file:
src/floatchat_app.py
Add Secret:
GEMINI_API_KEY=YOUR_KEY

Deploy

Alternative Deployment
Hugging Face Spaces
Render
Railway
Azure App Service
📊 Example Queries
Ocean Data
Show temperature profile in Arabian Sea
Compare Bay of Bengal and Arabian Sea salinity
Generate T-S diagram for Arabian Sea
RAG Queries
What causes salinity variation?
Explain thermocline
What is Ekman transport?
Explain Indian Ocean circulation
📈 Project Outcomes
Successfully integrated Gemini AI with Ocean Data Analytics.
Built domain-specific RAG knowledge base.
Enabled contextual scientific question answering.
Developed interactive visualization dashboard.
Improved accessibility of oceanographic information.
🔮 Future Scope
Technical Enhancements
Multi-document retrieval
Hybrid Search (BM25 + Vector Search)
Query Routing using LLM
Citation-based responses
Source ranking
Oceanographic Extensions
Satellite Data Integration
ENSO Monitoring
Marine Heatwave Detection
Ocean Anomaly Detection
Climate Change Analysis
Deployment Enhancements
User Authentication
Research Report Generation
PDF Export
Mobile Application
👨‍🎓 Capstone Project Information

Student Name: Krishna Daruwala

College: Sarvajanik College of Commerce and Computer Application

University: Sarvajanik University

Department: Faculty of Commerce

Program: Bachelor of Computer Applications (BCA)

Project Title: FloatChat AI – AI-Powered Ocean Intelligence Assistant using Argo Float Data and RAG

📚 References
Python Documentation
Streamlit Documentation
Google Gemini API Docs
FAISS Documentation
Hugging Face Transformers
Argo Program Official Website
Scikit-Learn Documentation
⭐ Acknowledgements

This project was developed as part of the AICTE Capstone Project Program, combining Artificial Intelligence, Ocean Data Analytics, and Retrieval-Augmented Generation (RAG) to create an intelligent oceanographic assistant. 🌊🤖
