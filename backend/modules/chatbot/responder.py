import logging
import os
import json
import time
import google.generativeai as genai

logger = logging.getLogger(__name__)

async def stream_response(query: str, context_results: list):
    """
    Stream SSE standard response yielding JSON chunks.
    Builds the system prompt, streams tokens, then invokes follow-up generator.
    """
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        system = """You are a social media research analyst. Answer questions about Reddit data using ONLY the provided context. Be precise and cite specific authors, subreddits, or topics from the context when relevant."""
        
        context_str = "\\n---CONTEXT---\\n"
        for idx, r in enumerate(context_results):
            context_str += f"[{idx+1}] Source: {r['source_type']}\\nMetadata: {json.dumps(r['metadata'])}\\n{r['text']}\\n\\n"
            
        full_prompt = f"{system}\\n{context_str}\\n---USER QUERY---\\n{query}"
        
        t0 = time.time()
        
        response = model.generate_content(
            full_prompt, 
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        full_answer = ""
        for chunk in response:
            if chunk.text:
                full_answer += chunk.text
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\\n\\n"
        
        latency = time.time() - t0
        logger.info(f"Chat stream finished. Latency: {latency:.2f}s")
        
        # Second call to get 3 follow-up suggestions
        sug_prompt = f"Based on the query '{query}' and the analysis just performed:\\n{full_answer}\\nSuggest exactly 3 related research questions as a JSON array of strings. Do not return markdown blocks, just the raw JSON list format [\"Question 1\", \"Question 2\", \"Question 3\"]."
        
        try:
            sug_res = model.generate_content(sug_prompt, generation_config=genai.types.GenerationConfig(temperature=0.5))
            # Clean up response to ensure valid json
            txt = sug_res.text.strip()
            if txt.startswith("```json"): txt = txt[7:]
            if txt.startswith("```"): txt = txt[3:]
            if txt.endswith("```"): txt = txt[:-3]
            txt = txt.strip()
            
            suggestions = json.loads(txt)
            if not isinstance(suggestions, list): suggestions = []
        except Exception as se:
            logger.error(f"Failed to generate suggestions: {se}")
            suggestions = []
            
        yield f"data: {json.dumps({'type': 'suggestions', 'content': suggestions})}\\n\\n"
        yield f"data: [DONE]\\n\\n"
        
    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred during response generation.'})}\\n\\n"
