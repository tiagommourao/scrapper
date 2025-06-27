from fastapi import APIRouter, HTTPException, Request
from internal import redis_cache
import os
import openai
from typing import List, Dict, Any

router = APIRouter(prefix='/api/manual', tags=['manual'])

@router.post('/generate')
async def generate_manual(payload: dict, request: Request):
    result_id = payload['result_id']
    target_language = payload.get('target_language', 'pt-BR')
    formatting = payload.get('formatting', 'chapters')
    use_ai_translation = payload.get('use_ai_translation', False)
    use_ai_summarization = payload.get('use_ai_summarization', False)
    custom_prompt = payload.get('custom_prompt')

    # 1. Carregar resultado do scraping
    scraping = redis_cache.load_result(result_id)
    if not scraping:
        raise HTTPException(404, detail="Scraping result not found")

    # 2. Estruturar conteúdo
    sections = extract_sections(scraping, formatting)

    # 3. Pipeline IA
    processed_sections = []
    for section in sections:
        text = section['content']
        if use_ai_translation:
            text = await translate_with_openai(text, target_language, custom_prompt)
        if use_ai_summarization:
            text = await summarize_with_openai(text, custom_prompt)
        processed_sections.append({**section, 'content': text})

    # 4. Montar manual
    manual_md = build_markdown_manual(processed_sections)
    manual_id = save_manual(manual_md, result_id, target_language)

    host_url = str(request.base_url).rstrip('/')
    return {
        "success": True,
        "manual_id": manual_id,
        "download_url": f"{host_url}/manual/download/{manual_id}?format=pdf",
        "preview_url": f"{host_url}/manual/preview/{manual_id}"
    }

# Exemplos de helpers (simplificados)
async def translate_with_openai(text: str, target_language: str, prompt: str = None) -> str:
    openai.api_key = os.getenv('OPENAI_API_KEY')
    system_prompt = f"Traduza o texto para {target_language}."
    if prompt:
        system_prompt += " " + prompt
    response = openai.ChatCompletion.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-4'),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    return response['choices'][0]['message']['content']

async def summarize_with_openai(text: str, prompt: str = None) -> str:
    openai.api_key = os.getenv('OPENAI_API_KEY')
    system_prompt = "Resuma e reestruture o texto para maior clareza e concisão."
    if prompt:
        system_prompt += " " + prompt
    response = openai.ChatCompletion.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-4'),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    return response['choices'][0]['message']['content']

def extract_sections(scraping: dict, formatting: str) -> List[Dict[str, Any]]:
    # Exemplo: extrair páginas como seções
    sections = []
    for level in scraping.get('levels', []):
        for page in level.get('pages', []):
            sections.append({
                'title': page.get('title', 'Sem título'),
                'content': page.get('textContent', '') or page.get('content', '')
            })
    return sections

def build_markdown_manual(sections: List[Dict[str, Any]]) -> str:
    md = ""
    for i, section in enumerate(sections, 1):
        md += f"# {i}. {section['title']}\n\n{section['content']}\n\n"
    return md

def save_manual(manual_md: str, result_id: str, lang: str) -> str:
    # Salva o manual em cache ou disco e retorna um manual_id
    import hashlib, time
    manual_id = hashlib.sha1(f"{result_id}-{lang}-{time.time()}".encode()).hexdigest()
    # Aqui você pode salvar no Redis, arquivo, etc.
    # Exemplo: redis_cache.store_result(manual_id, {'manual_md': manual_md, 'lang': lang, 'source': result_id})
    return manual_id 