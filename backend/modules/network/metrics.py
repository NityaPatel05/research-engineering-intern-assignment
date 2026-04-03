import logging
import math
import networkx as nx
import igraph as ig
import leidenalg
import os
import time
import google.generativeai as genai

logger = logging.getLogger(__name__)

COLOR_PALETTE = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

# Module-level flag: set to True once daily quota is exhausted to skip further calls
_gemini_quota_exceeded = False
_gemini_quota_reset_time = 0.0  # epoch seconds when we can retry


def _safe_float(v: float) -> float:
    """Replace NaN/Inf with 0.0 so JSON serialisation never fails."""
    if not isinstance(v, (int, float)):
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return float(v)

def get_community_label(top_nodes: list) -> str:
    """Use Gemini to label a community from top node names."""
    global _gemini_quota_exceeded, _gemini_quota_reset_time

    # Skip if daily quota was exhausted and not yet reset
    if _gemini_quota_exceeded:
        if time.time() < _gemini_quota_reset_time:
            logger.info("Gemini daily quota exceeded — skipping label call.")
            return "Unknown Cluster"
        else:
            # Reset for a new day
            _gemini_quota_exceeded = False

    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        You are a social media analyst. Here are the top 5 most influential users or domains
        in a networked cluster: {', '.join(top_nodes)}.
        Please provide a concise 3-word label summarizing the nature of this community.
        Return ONLY the 3 words.
        """
        # Throttle: 5 req/min per-minute limit → 1 req/13s
        time.sleep(13)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=20, temperature=0.3)
        )
        # Guard safety-filter blocks
        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning("Gemini returned no content parts (safety filter). Using default label.")
            return "Unknown Cluster"
        return response.text.replace('"', '').strip()
    except Exception as e:
        err_str = str(e)
        logger.error(f"Gemini API call failed for label: {e}")
        # Detect daily quota exhaustion and back off for 24 hours
        if "GenerateRequestsPerDay" in err_str or ("429" in err_str and "limit: 20" in err_str):
            _gemini_quota_exceeded = True
            _gemini_quota_reset_time = time.time() + 86400  # retry after 24h
            logger.warning("Gemini daily quota exhausted — community labelling disabled for 24h.")
        return "Unknown Cluster"

def convert_nx_to_ig(G_nx: nx.Graph) -> ig.Graph:
    """Convert NetworkX graph to iGraph with weights."""
    g = ig.Graph()
    if G_nx.number_of_nodes() == 0:
        return g
        
    g.add_vertices(list(G_nx.nodes()))
    
    # Store standard nx attributes on igraph equivalent
    for node, data in G_nx.nodes(data=True):
        g.vs.find(name=node)["type"] = data.get("type", "user")
        g.vs.find(name=node)["label"] = data.get("label", str(node))
        
    edges = list(G_nx.edges(data=True))
    ig_edges = [(e[0], e[1]) for e in edges]
    g.add_edges(ig_edges)
    
    weights = [e[2].get('weight', 1.0) for e in edges]
    g.es["weight"] = weights
    return g

def compute_metrics(G_nx: nx.Graph) -> dict:
    """
    Convert to iGraph, compute PageRank (0.85), Betweenness, Degree.
    Run Leiden, Get LLM labels. Handle disconnected components.
    """
    try:
        if G_nx.number_of_nodes() == 0:
            return {"metrics": {}, "assignments": {}, "labels": {}}
            
        g = convert_nx_to_ig(G_nx)
        
        metrics = {}
        # We must process connected components safely
        components = g.components()
        
        for comp in components:
            subgraph = g.induced_subgraph(comp)
            
            # Degree is safe globally as well, but do it here safely
            degrees = subgraph.degree()
            
            # Betweenness
            # Handle weights: weights should be costs for path tracing or standard.
            # default betweenness ignores weights if not directed properly but we'll use base.
            betweenness = subgraph.betweenness(directed=False)
            
            # PageRank
            pageranks = subgraph.pagerank(damping=0.85)

            for idx, vertex in enumerate(subgraph.vs):
                metrics[vertex["name"]] = {
                    "degree": _safe_float(degrees[idx]),
                    "betweenness": _safe_float(betweenness[idx]),
                    "pagerank": _safe_float(pageranks[idx])
                }
                
        # Community Detection
        # Weighted Leiden
        partition = leidenalg.find_partition(
            g, leidenalg.ModularityVertexPartition, weights=g.es["weight"]
        )
        
        assignments = {}
        labels = {}
        
        names = g.vs["name"]
        for comm_id, node_indices in enumerate(partition):
            color = COLOR_PALETTE[comm_id % len(COLOR_PALETTE)]
            
            # Sort node indices by pagerank to find top 5
            comm_nodes_pr = [(names[idx], metrics[names[idx]]["pagerank"]) for idx in node_indices]
            comm_nodes_pr.sort(key=lambda x: x[1], reverse=True)
            top_5 = [item[0] for item in comm_nodes_pr[:5]]
            
            for idx in node_indices:
                assignments[names[idx]] = {"group": comm_id, "color": color}
                
            label = get_community_label(top_5)
            labels[str(comm_id)] = {"label": label, "color": color}
            
        return {
            "metrics": metrics,
            "assignments": assignments,
            "labels": labels
        }
    except Exception as e:
        logger.error(f"Error computing metrics: {e}")
        return {"metrics": {}, "assignments": {}, "labels": {}}
