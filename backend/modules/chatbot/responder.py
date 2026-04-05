import logging
import json
import time
import google.generativeai as genai
from config import get_gemini_api_key, mark_gemini_key_exhausted, increment_gemini_key_usage

logger = logging.getLogger(__name__)

async def stream_response(query: str, context_results: list):
    """
    Stream SSE standard response yielding JSON chunks.
    Builds the system prompt, streams tokens, then invokes follow-up generator.
    """
    api_key = get_gemini_api_key()
    try:
        if not api_key:
            yield f"data: {json.dumps({'type': 'error', 'content': 'GEMINI_API_KEY not set or all keys exhausted'})}\n\n"
            return
            
        genai.configure(api_key=api_key)
        
        system = "You are a social media research analyst. Answer questions about Reddit data using ONLY the provided context. Be precise and cite specific authors, subreddits, or topics from the context when relevant."
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system
        )
        
        context_str = "\n---CONTEXT---\n"
        for idx, r in enumerate(context_results):
            context_str += f"[{idx+1}] Source: {r['source_type']}\nMetadata: {json.dumps(r['metadata'])}\n{r['text']}\n\n"
            
        full_prompt = f"{context_str}\n---USER QUERY---\n{query}"
        
        t0 = time.time()
        
        increment_gemini_key_usage(api_key)
        response = await model.generate_content_async(
            full_prompt,
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        full_answer = ""
        async for chunk in response:
            token = chunk.text
            if token:
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        
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
            api_key_sug = get_gemini_api_key()
            if api_key_sug:
                genai.configure(api_key=api_key_sug)
                sug_model = genai.GenerativeModel("gemini-2.5-flash")
                increment_gemini_key_usage(api_key_sug)
                sug_res = await sug_model.generate_content_async(
                    sug_prompt,
                    generation_config=genai.types.GenerationConfig(temperature=0.5)
                )
                
                txt = sug_res.text.strip()
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
            else:
                suggestions = []
        except Exception as se:
            err_str = str(se)
            if "GenerateRequestsPerDay" in err_str or ("429" in err_str and "limit: 20" in err_str) or "Quota exceeded" in err_str:
                if 'api_key_sug' in locals() and api_key_sug: mark_gemini_key_exhausted(api_key_sug)
            logger.error(f"Failed to generate suggestions: {se}")
            suggestions = []
            
        yield f"data: {json.dumps({'type': 'suggestions', 'content': suggestions})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        err_str = str(e)
        if "GenerateRequestsPerDay" in err_str or ("429" in err_str and "limit: 20" in err_str) or "Quota exceeded" in err_str:
            if api_key: mark_gemini_key_exhausted(api_key)
        logger.error(f"Error in stream_response: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred during response generation.'})}" + "\n\n"

