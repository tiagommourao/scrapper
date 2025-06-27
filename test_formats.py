#!/usr/bin/env python3
import requests
import json

def test_all_formats():
    """Teste de todos os formatos de manual"""
    
    result_id = "d24943364e80592427936916022279286ce87234"
    formats = ['html', 'markdown', 'pdf', 'docx']
    
    for format_type in formats:
        print(f"\n🧪 Testando formato: {format_type.upper()}")
        
        payload = {
            "result_id": result_id,
            "format_type": format_type,
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
        
        try:
            response = requests.post(
                "http://localhost:3000/api/deep-scrape/manual",
                json=payload,
                timeout=60  # Aumentando timeout para PDF/DOCX
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {format_type.upper()} gerado com sucesso!")
                print(f"Formato retornado: {result.get('format', 'N/A')}")
                print(f"Tamanho do conteúdo: {len(str(result.get('content', '')))}")
                print(f"Download URL: {result.get('download_url', 'N/A')}")
                
                # Para formatos binários, verificar se content é bytes
                if format_type in ['pdf', 'docx']:
                    content = result.get('content', '')
                    if isinstance(content, str) and content.startswith('<!DOCTYPE'):
                        print(f"⚠️  ATENÇÃO: {format_type.upper()} retornou HTML em vez do formato correto!")
                    else:
                        print(f"✅ {format_type.upper()} parece estar no formato correto")
                
            else:
                print(f"❌ Erro {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Erro: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Resposta raw: {response.text[:500]}...")
            
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")

if __name__ == "__main__":
    test_all_formats() 