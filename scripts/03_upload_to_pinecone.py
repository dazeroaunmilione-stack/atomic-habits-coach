import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv('../.env')

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index('atomic-habits-knowledge')

with open('../output/modules_enriched.json', 'r', encoding='utf-8') as f:
    modules = json.load(f)

def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding

def make_chunk_text(mod):
    parts = [
        f"Titolo: {mod.get('module_title', '')}",
        f"Dominio: {mod.get('primary_domain', '')}",
        f"Fase cambiamento: {mod.get('behavior_change_stage', '')}",
        f"Ruolo funzionale: {mod.get('functional_role', '')}",
        f"Keywords: {mod.get('retrieval_keywords', '')}",
        f"Contenuto: {mod.get('text', '')[:3000]}"
    ]
    return '\n'.join(p for p in parts if p.split(': ')[1])

vectors = []
for mod in modules:
    chunk_text = make_chunk_text(mod)
    embedding = get_embedding(chunk_text)
    vector = {
        'id': f"module_{mod['module_id']}",
        'values': embedding,
        'metadata': {
            'module_id': str(mod['module_id']),
            'module_title': mod.get('module_title', ''),
            'primary_domain': mod.get('primary_domain', ''),
            'behavior_change_stage': mod.get('behavior_change_stage', ''),
            'coaching_relevance': str(mod.get('coaching_relevance', '')),
            'functional_role': mod.get('functional_role', ''),
            'text_preview': mod.get('text', '')[:500]
        }
    }
    vectors.append(vector)
    print(f"✓ {mod.get('module_title', '')[:50]}")

batch_size = 100
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i+batch_size]
    index.upsert(vectors=batch)
    print(f"Caricati {min(i+batch_size, len(vectors))}/{len(vectors)} vettori")

print(f"\n✅ COMPLETATO: {len(vectors)} moduli caricati su Pinecone")
print("Stats:", index.describe_index_stats())