#!/usr/bin/env python3
import requests
import json

def test_markdown():
    """Teste específico para Markdown"""
    
    result_id = "d24943364e80592427936916022279286ce87234"
    
    payload = {
        "result_id": result_id,
        "format_type": "markdown",
        "style": "professional",
        "translate": False,
        "source_language": "auto",
        "target_language": "pt",
        "translation_provider": "libre",
        "translation_api_key": None,
        "manual_type": "general",
        "include_toc": True,
        "include_metadata": True
    }
    
    print(f"🧪 Testando formato Markdown...")
    
    try:
        response = requests.post(
            "http://localhost:3000/api/deep-scrape/manual",
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Chaves da resposta: {list(result.keys())}")
            
            if 'error' in result:
                print(f"❌ Erro na resposta: {result['error']}")
            else:
                print(f"✅ Markdown gerado!")
                print(f"Formato: {result.get('format', 'N/A')}")
                print(f"Título: {result.get('title', 'N/A')}")
                print(f"Download URL: {result.get('download_url', 'N/A')}")
                
                if 'content' in result:
                    content = result['content']
                    print(f"Conteúdo presente: {len(content) > 0}")
                    if len(content) > 0:
                        print(f"Primeiros 200 chars: {content[:200]}...")
                    else:
                        print("⚠️  Conteúdo vazio!")
                else:
                    print("⚠️  Chave 'content' não encontrada na resposta!")
                
        else:
            print(f"❌ Erro {response.status_code}")
            try:
                error_data = response.json()
                print(f"Erro: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Resposta raw: {response.text}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_markdown() 