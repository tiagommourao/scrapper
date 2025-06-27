#!/usr/bin/env python3
"""
Teste do Cache Inteligente para Deep Scraping

Este script testa:
1. Cache com diferentes parâmetros de depth
2. Cache incremental por URL
3. Botão "Ignore Cache"
"""

import requests
import json
import time

BASE_URL = "http://localhost:3000"
TEST_URL = "https://example.com"

def test_cache_with_different_depths():
    """Testa se cache diferencia entre depths diferentes"""
    print("🧪 Testando cache com depths diferentes...")
    
    # Teste 1: Depth 2
    print("📊 Fazendo scraping com depth=2...")
    response1 = requests.get(f"{BASE_URL}/api/deep-scrape", params={
        'url': TEST_URL,
        'depth': 2,
        'cache': 'true'
    })
    
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"✅ Depth 2 - Result ID: {result1.get('id', 'N/A')}")
    else:
        print(f"❌ Erro no depth 2: {response1.status_code}")
        return False
    
    time.sleep(1)
    
    # Teste 2: Depth 3 (deve ser diferente do depth 2)
    print("📊 Fazendo scraping com depth=3...")
    response2 = requests.get(f"{BASE_URL}/api/deep-scrape", params={
        'url': TEST_URL,
        'depth': 3,
        'cache': 'true'
    })
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✅ Depth 3 - Result ID: {result2.get('id', 'N/A')}")
        
        # Verificar se são IDs diferentes (cache inteligente funcionando)
        if result1.get('id') != result2.get('id'):
            print("🎉 Cache inteligente funcionando! IDs diferentes para depths diferentes.")
            return True
        else:
            print("⚠️  Cache não diferenciou entre depths - IDs iguais.")
            return False
    else:
        print(f"❌ Erro no depth 3: {response2.status_code}")
        return False

def test_ignore_cache():
    """Testa se o botão ignore cache funciona"""
    print("\n🧪 Testando botão 'Ignore Cache'...")
    
    # Primeiro request com cache
    print("📊 Primeiro request com cache...")
    response1 = requests.get(f"{BASE_URL}/api/deep-scrape", params={
        'url': TEST_URL,
        'depth': 2,
        'cache': 'true'
    })
    
    if response1.status_code != 200:
        print(f"❌ Erro no primeiro request: {response1.status_code}")
        return False
    
    result1 = response1.json()
    print(f"✅ Primeiro request - Result ID: {result1.get('id', 'N/A')}")
    
    time.sleep(1)
    
    # Segundo request ignorando cache
    print("📊 Segundo request ignorando cache...")
    response2 = requests.get(f"{BASE_URL}/api/deep-scrape", params={
        'url': TEST_URL,
        'depth': 2,
        'cache': 'false'  # Ignore cache
    })
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✅ Segundo request - Result ID: {result2.get('id', 'N/A')}")
        
        # Verificar se são IDs diferentes (ignore cache funcionando)
        if result1.get('id') != result2.get('id'):
            print("🎉 Ignore cache funcionando! IDs diferentes mesmo com mesmos parâmetros.")
            return True
        else:
            print("⚠️  Ignore cache não funcionou - IDs iguais.")
            return False
    else:
        print(f"❌ Erro no segundo request: {response2.status_code}")
        return False

def test_async_intelligent_cache():
    """Testa cache inteligente no endpoint assíncrono"""
    print("\n🧪 Testando cache inteligente no endpoint assíncrono...")
    
    # Teste com depth 2
    payload1 = {
        "url": TEST_URL,
        "depth": 2,
        "cache": True
    }
    
    print("📊 Enviando job assíncrono com depth=2...")
    response1 = requests.post(f"{BASE_URL}/api/deep-scrape/async", json=payload1)
    
    if response1.status_code != 200:
        print(f"❌ Erro no job assíncrono depth 2: {response1.status_code}")
        return False
    
    result1 = response1.json()
    print(f"✅ Job depth 2 - {'Cache HIT' if result1.get('from_cache') else 'Cache MISS'}")
    
    # Teste com depth 3
    payload2 = {
        "url": TEST_URL,
        "depth": 3,
        "cache": True
    }
    
    print("📊 Enviando job assíncrono com depth=3...")
    response2 = requests.post(f"{BASE_URL}/api/deep-scrape/async", json=payload2)
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✅ Job depth 3 - {'Cache HIT' if result2.get('from_cache') else 'Cache MISS'}")
        
        # Se depth 3 for cache MISS, significa que o cache inteligente está funcionando
        if not result2.get('from_cache'):
            print("🎉 Cache inteligente assíncrono funcionando! Depth 3 não usou cache do depth 2.")
            return True
        else:
            print("⚠️  Cache assíncrono pode não estar diferenciando depths.")
            return False
    else:
        print(f"❌ Erro no job assíncrono depth 3: {response2.status_code}")
        return False

def main():
    """Executa todos os testes"""
    print("🚀 Iniciando testes do Cache Inteligente para Deep Scraping\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Teste 1: Cache com diferentes depths
    if test_cache_with_different_depths():
        tests_passed += 1
    
    # Teste 2: Botão ignore cache
    if test_ignore_cache():
        tests_passed += 1
    
    # Teste 3: Cache inteligente assíncrono
    if test_async_intelligent_cache():
        tests_passed += 1
    
    print(f"\n📊 Resultados dos testes: {tests_passed}/{total_tests} passaram")
    
    if tests_passed == total_tests:
        print("🎉 Todos os testes passaram! Cache inteligente funcionando perfeitamente.")
    else:
        print("⚠️  Alguns testes falharam. Verificar implementação.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    main() 