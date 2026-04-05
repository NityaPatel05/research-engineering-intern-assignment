## PROMPT 001 — Initial System Understanding

Component: System Design / Thinking Phase

Prompt:
"I have a JSONL dataset from Reddit with fields like title, selftext, author, created_utc, subreddit, score, num_comments, url, id, permalink. I need to build an interactive dashboard for social media analysis for a research internship. What are all the functionalities from basic to medium to advanced that would make me unique and best for this type of task using the latest most widely used tech?"

What was wrong with output:
The initial output was too generic and listed too many features without considering what the dataset actually supported. It suggested hashtag analysis which Reddit data does not have natively.

How it was fixed:
I shared the dataset summary explicitly and asked to revise based on actual available fields. Dropped hashtag graph, adjusted all features to use title+selftext as full_text, subreddit as community label, url for link analysis, and created_utc for time analysis.

---

## PROMPT 002 — Unique Functionalities Research

Component: System Design / Unique Features

Prompt:
"Give me 2-3 unique functionalities that are actually used in real world and I can apply on this dataset."

What was wrong with output:
All three were listed as equally viable. I needed to pick one and commit rather than try to implement all three.

How it was fixed:
After reviewing all three (CIB Detection, Narrative Lifecycle Tracking, Cross-Platform Fingerprinting), I chose Narrative Lifecycle Tracking because it matched the dataset better — Reddit has no retweets so CIB coordination signals are weaker, and cross-platform requires additional data sources. Narrative Lifecycle works purely from text and timestamps which the dataset has fully.

---

## PROMPT 003 — Spam Detection Options

Component: Spam Detection Module

Prompt:
"I also have to detect spam as they have mentioned. What can I use for that and what is most widely used?"

What was wrong with output:
The first response gave five layers of spam detection which was overengineered for a research prototype. Layers 3 through 5 required labeled data, GPU inference, or additional dependencies that added complexity without proportional value.

How it was fixed:
Trimmed to two layers: rule-based behavioral signals and Isolation Forest. Explicitly noted the architecture supports adding more layers later. This became the final implementation — two layers, seven signals, honest and explainable in an interview.

---

## PROMPT 004 — Chatbot Context Sources

Component: Chatbot / RAG Design

Prompt:
"For the chatbot based on my project, should I use not just posts but also info from the graphs and other sources? And is one graph enough or do I need multiple?"

What was wrong with output:
The initial response listed six knowledge sources which was too many to implement well. Also the graph section recommended four graphs which was more than the dataset could support without missing fields.

How it was fixed:
Reduced to three ChromaDB knowledge sources: post embeddings, graph-derived account facts, and topic cluster summaries. Reduced graphs to two: User-URL Bipartite and Author Co-Activity. Both reductions were driven by the actual available fields in the dataset — no retweets, no reply chains, no direct interactions.

---

## PROMPT 005 — Dataset Field Reality Check

Component: All Modules / Dataset Alignment

Prompt:
"The dataset is Reddit-like JSONL. Fields available: title, selftext, author, created_utc, subreddit, score, num_comments, url, id, permalink. Missing: hashtags (not on Reddit), direct interactions like retweets or replies, thread structure. Is 4 graphs needed now? Can spam be made simpler? Which RAG sources are most important?"

What was wrong with output:
Nothing major — this was a clarification prompt that confirmed the right direction. The output correctly identified that Graph 1 (User-Hashtag) should be dropped and Graph 3 (Temporal Interaction) cannot be built without reply/retweet data.

How it was fixed:
Finalized the two-graph decision. Graph 1 became User-URL Bipartite. Graph 2 became Author Co-Activity. This is what was implemented.

---

## PROMPT 006 — Switching from CIB to Narrative Lifecycle

Component: Unique Feature Selection

Prompt:
"I want to add Narrative Lifecycle Tracking instead of CIB as it matches our dataset more. Also add growth rate metric as (posts_today - posts_yesterday) / posts_yesterday and visual badges Emerging, Peaking, Declining, Dead. Give me the whole final system with all changes."

What was wrong with output:
The badge logic was initially too simple — just using growth rate alone to assign stages. That produces wrong labels for topics that are stable at high volume (they get labeled Declining because growth rate is near zero).

How it was fixed:
Added volume position to the classification logic. Peaking requires both near-zero growth rate AND current volume above 70% of peak. Emerging requires positive growth rate AND volume below 70% of peak. This produces correct labels for plateau-shaped narratives.

---

## PROMPT 007 — Full System Final Design

Component: All Modules

Prompt:
"Now everything is decided. Give me the proper flow and all the functionalities we decided to implement, what to use in each, unique feature, anomaly detection, and chatbot design."

What was wrong with output:
The backend architecture section listed Redis as a hard dependency. Redis adds operational complexity for a research prototype.

How it was fixed:
Kept Redis in the architecture for caching centrality scores and embeddings but made it optional — the system falls back to in-memory caching if Redis is unavailable. This is reflected in config.py where REDIS_URL has a fallback.

---

## PROMPT 008 — Modular Build Order

Component: Project Structure / Commit Strategy

Prompt:
"I have to show all commits made so I have to build in modular format. Give me that format and the flow of what to make first and what last."

What was wrong with output:
The initial module order had the chatbot at Module 4, before topics and network were built. But the chatbot depends on embeddings from topics and graph facts from network.

How it was fixed:
Reordered so chatbot is always the last backend module (Module 7), built after topics (Module 5), lifecycle (Module 6), and network (Module 4) are all complete. This is the correct dependency order.

---

## PROMPT 009 — Exact File Creation Sequence

Component: Project Structure

Prompt:
"I am asking which files to make first and in which sequence, one file at a time."

What was wrong with output:
The initial sequence had frontend api files being created before their backend endpoints were tested. This means you are writing code against an API that may not work yet.

How it was fixed:
Added explicit test checkpoint between each backend file completion and frontend file creation. Rule established: backend endpoint tested and returning real data before any frontend file for that module is started.

---

## PROMPT 010 — Cluster Caching Strategy

Component: Topic Clustering / Cache Module

Prompt:
"I have to form clusters every time so if I can store a map of clusters from 1 to 20 that are more frequent and if cluster in UI makes changes then render the stored one, or if a new post enters I can find where to insert it. I don't know if this can be done or not."

What was wrong with output:
The first response described storing 20 full BERTopic model objects in memory which would be 2-4GB. That is not practical.

How it was fixed:
Changed to two-level caching: embeddings cached to disk as numpy file (computed once, never again), and cluster assignment outputs cached in a lightweight Python dict keyed by nr_topics (not the full model objects). New post insertion uses BERTopic's built-in transform() method on whichever model is currently active in memory. Pre-warm only the 5 most common nr_topics values on startup.

---

## PROMPT 011 — Network Graph Visual Quality

Component: Network Module / Frontend

Prompt:
"In network as you suggested I am using PyVis but it does not feel good. Any other options which shows a clear interactive graph?"

What was wrong with output:
The first response recommended D3.js as the top option. D3 requires 200+ lines of custom rendering code for the interactivity level needed (click events, centrality toggle, node removal). That time was better spent on other modules.

How it was fixed:
Chose Cytoscape.js with cose-bilkent layout instead. cose-bilkent is specifically designed for clustered networks and naturally separates Leiden communities spatially. Built-in tap events handle node clicks. mapData() handles centrality-to-size encoding. All of this comes for free vs custom D3 code. PyVis was completely removed from the project.

---

## PROMPT 012 — HuggingFace API Error

Component: Chatbot / LLM Integration

Prompt:
"Error: 403, message='Forbidden', url='https://router.huggingface.co/novita/v3/openai/chat/completions' — model mistralai/Mistral-7B-Instruct-v0.3 for provider novita."

What was wrong with output:
First suggestion was to switch to Gemini API. I wanted to stay on HuggingFace.

How it was fixed:
Tried removing the provider parameter entirely to use HuggingFace serverless inference directly. All models returned 404. This confirmed HuggingFace free serverless inference was not available on my account tier. Moved to OpenRouter instead of Gemini because OpenRouter gives access to free models including Qwen without requiring a credit card.

---

## PROMPT 013 — HuggingFace Model Testing

Component: Chatbot / LLM Integration

Prompt:
"Show me demo code to test if microsoft/Phi-3-mini-4k-instruct is working without error."

What was wrong with output:
First test used text_generation method. Got StopIteration error.

How it was fixed:
Switched to chat.completions.create with stream=False explicitly. Still got StopIteration. Tried streaming fallback. Still failed. Root cause: Phi-3 was returning a generator even with stream=False due to HuggingFace SDK behavior at that version. Tried requests library directly — got 404. Confirmed the model is not on free serverless inference. Tried 6 other models including zephyr-7b-beta, Mistral-7B-Instruct-v0.1, falcon-7b-instruct, flan-t5-large, opt-1.3b, bloom-560m — all 404. Concluded HuggingFace free tier was fully unavailable.

---

## PROMPT 014 — Switching to OpenRouter

Component: Chatbot / LLM Integration

Prompt:
"Can I use OpenRouter instead of Groq and then use qwen/qwen3-30b-a3b:free model?"

What was wrong with output:
First test code worked structurally but returned 401 Forbidden.

How it was fixed:
The issue was the API key was not being loaded from environment correctly. After confirming the key was loaded (key found: True, starts with sk-or-v1-6, length 37), the 401 persisted. Root cause was the key had a domain restriction set in the OpenRouter dashboard that blocked localhost requests. Deleted the key, created a new one with no domain restrictions, and the API call succeeded.

---

## PROMPT 015 — LangGraph Decision

Component: Chatbot / Architecture

Prompt:
"Do I need to implement LangGraph for the chatbot or not?"

What was wrong with output:
Nothing wrong — this was a clarification question. The answer was correct immediately.

How it was fixed:
Confirmed LangGraph is not needed. The chatbot flow is a linear pipeline: retrieve, synthesize, suggest. No branching logic, no conditional next steps. LangGraph is for multi-step agent workflows where the next action depends on the previous result. Adding it would have introduced the exact 403 errors that were already causing problems (the original error in the logs was from a LangGraph node). Removed LangGraph entirely and replaced with three plain functions.

---

## PROMPT 016 — Clickable Drilldown Functionality

Component: Frontend / All Pages

Prompt:
"There is no clickable URI and no clickable element that makes it show posts. Where can I add this functionality from all components?"

What was wrong with output:
The initial response listed clickable elements for every component but suggested creating new backend endpoints for cases where existing ones already handled it. Specifically the author drilldown was already handled by GET /accounts/{username} which existed in the spam router.

How it was fixed:
Identified which clickable interactions needed new endpoints vs which just needed frontend wiring to existing endpoints. New endpoints added: GET /topics/{topic_id}/posts, GET /timeseries/posts, GET /accounts/{username}/posts. Existing endpoints reused: GET /accounts/{username} wired to Cytoscape node click event. One shared PostModal component handles all post detail views. The permalink field in the dataset provides the actual Reddit URL so View on Reddit becomes a real link.

---

## PROMPT 017 — Gemini to OpenRouter Conversion

Component: Chatbot / responder.py

Prompt:
"Convert this Gemini streaming responder code to OpenRouter instead of Gemini."

What was wrong with output:
The first conversion attempt kept the async generator pattern from Gemini but used requests library which is synchronous. This creates a blocking call inside an async function which can block the FastAPI event loop.

How it was fixed:
Kept the async generator for the streaming interface (because FastAPI SSE requires it) but moved the actual HTTP call into a synchronous helper function call_openrouter() called normally inside the async generator. For true async HTTP on OpenRouter, httpx could be used instead of requests, but the synchronous approach works correctly for this use case because the LLM call is the only blocking operation and it runs to completion before yielding. Noted in code comments.

---

## PROMPT 018 — Video Demo Script

Component: Documentation / Submission

Prompt:
"I have to make a video demo for it. Generate a speech along with what I will be seeing on the dashboard and where to put cursor when speaking, making sure to cover all the pro tips they mentioned."

What was wrong with output:
The first script was too technical in places — explaining what BERTopic does step by step rather than why design choices were made. The pro tips specifically say: not what the code does line by line, but why you made the choices you did.

How it was fixed:
Rewrote all technical explanation sections to lead with the research motivation, then the algorithm choice, then why that choice over alternatives. For example the network section was rewritten to explain why two graphs not one, why Cytoscape not PyVis, and what each graph answers — not what the algorithms compute internally.

---

## PROMPT 019 — Topic Clustering Video Script

Component: Documentation / Submission

Prompt:
"Give me also info about the topic clustering page in simple English and cover all info."

What was wrong with output:
The first version explained BERTopic's three stages (embedding, UMAP, HDBSCAN) at the beginning before explaining what the page does for a researcher. Evaluators who are not ML experts would lose context.

How it was fixed:
Restructured to lead with what the page answers for a researcher, then the slider explanation, then the algorithm explanation positioned as supporting the design choice, then the visualization, then card walkthrough, then edge cases. Algorithm details come after the value proposition, not before it.

---

## PROMPT 020 — README Generation

Component: Documentation / Submission

Prompt:
"Generate a perfect README file based on the project info and file structure. I have deployed on EC2 so make placeholder for that link. No emojis. Screenshot placeholders for all modules."

What was wrong with output:
First draft included a Lessons Learned section which is not part of the rubric and wastes space. Also the API endpoints section listed endpoints that did not exist in the final implementation.

How it was fixed:
Removed Lessons Learned section. Audited API endpoints against actual routers and removed any that were not implemented. Added the admin index endpoint for ChromaDB setup which was missing from the first draft. Kept eleven screenshot placeholders, one per meaningful view.

---

## SUMMARY OF MAJOR DECISIONS THAT CHANGED DURING DEVELOPMENT

1. CIB Detection was the original unique feature. Changed to Narrative Lifecycle Tracking because the dataset has no retweet or reply fields, making coordination timing signals weak. Lifecycle tracking works purely from text and timestamps.

2. Four graphs were initially planned. Reduced to two because Graph 1 (User-Hashtag Bipartite) requires hashtags which Reddit does not have natively, and Graph 3 (Temporal Interaction) requires reply/retweet edges which are absent from this dataset.

3. Six RAG knowledge sources were initially planned. Reduced to three: post embeddings, graph account facts, topic summaries. GDELT real-world events and time-series narrative pre-storage were deferred as future extensions.

4. Five spam detection layers were initially planned. Reduced to two: rule-based signals and Isolation Forest. The remaining layers require labeled data or GPU inference and were architecturally noted as future additions.

5. LangGraph was initially used for chatbot orchestration. Removed entirely after 403 errors confirmed it was adding complexity and a third-party routing dependency for a linear pipeline that needs no branching logic.

6. PyVis was the initial network visualization choice. Replaced with Cytoscape.js with cose-bilkent layout because PyVis physics produces unstable layouts and has no node click event API.

7. HuggingFace serverless inference was the initial LLM provider. Replaced with OpenRouter after confirming HuggingFace free tier was not accessible on the account used (all models returned 404 on the inference API regardless of model or provider parameter).

8. Gemini API was an intermediate LLM provider choice. Replaced with OpenRouter because OpenRouter provides free access to Qwen3 without requiring a credit card and has a cleaner rate limit policy for research prototypes.
