import logging
import os
import json
import time
from xmlrpc import client
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

async def stream_response(query: str, context_results: list):
    """
    Stream SSE standard response yielding JSON chunks.
    Builds the system prompt, streams tokens, then invokes follow-up generator.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            yield f"data: {json.dumps({'type': 'error', 'content': 'OPENROUTER_API_KEY not set in .env'})}\n\n"
            return
            
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SimPPL Dashboard",
            }
        )
        
        system = """You are a social media research analyst. Answer questions about Reddit data using ONLY the provided context. Be precise and cite specific authors, subreddits, or topics from the context when relevant."""
        
        context_str = "\n---CONTEXT---\n"
        for idx, r in enumerate(context_results):
            context_str += f"[{idx+1}] Source: {r['source_type']}\nMetadata: {json.dumps(r['metadata'])}\n{r['text']}\n\n"
            
        full_prompt = f"{system}\n{context_str}\n---USER QUERY---\n{query}"
        
        t0 = time.time()
        
        response = await client.chat.completions.create(
            model="google/gemma-4-26b-a4b-it",
            messages=[{"role": "user", "content": full_prompt}],
            stream=True,
            temperature=0.3
        )
        full_answer = ""
        async for chunk in response:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}" + "\n\n"
        
        latency = time.time() - t0
        logger.info(f"Chat stream finished. Latency: {latency:.2f}s")
        
        # Second call to get 3 follow-up suggestions
        sug_prompt = (
            f"Based on the query '{query}' and the analysis just performed:\n"
            f"{full_answer}\n"
            f"Suggest exactly 3 related research questions as a JSON array of strings. "
            f"Do not return markdown blocks, just the raw JSON list format [\"Question 1\", \"Question 2\", \"Question 3\"]."
        )        
        try:
            sug_res = await client.chat.completions.create(
                model="google/gemma-4-26b-a4b-it",
                messages=[{"role": "user", "content": sug_prompt}],
                temperature=0.5
            )            # Clean up response to ensure valid json
            txt = sug_res.choices[0].message.content.strip()
            if txt.startswith("```json"): txt = txt[7:]
            if txt.startswith("```"): txt = txt[3:]
            if txt.endswith("```"): txt = txt[:-3]
            txt = txt.strip()
            start = txt.find("[")
            end   = txt.rfind("]") + 1
            if start != -1 and end > start:
                txt = txt[start:end]
            
            
            suggestions = json.loads(txt)
            if not isinstance(suggestions, list): suggestions = []
        except Exception as se:
            logger.error(f"Failed to generate suggestions: {se}")
            suggestions = []
            
        yield f"data: {json.dumps({'type': 'suggestions', 'content': suggestions})}" + "\n\n"
        yield "data: [DONE]" + "\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred during response generation.'})}" + "\n\n"
