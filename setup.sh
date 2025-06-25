#!/bin/bash

# Script de configuração para o Scrapper Deep Scrape
echo "🧹 Configurando o Scrapper com Deep Scraping..."

# Criar diretorios necessários
echo "📁 Criando diretórios..."
mkdir -p user_data user_scripts

# Verificar se estamos no Linux/Mac para definir permissões
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "🔒 Definindo permissões (Linux)..."
    sudo chown 1001:1001 user_data/ user_scripts/
else
    echo "🍎 macOS detectado - permissões automáticas"
fi

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Instale o Docker Compose primeiro."
    exit 1
fi

echo "✅ Setup concluído!"
echo ""
echo "🚀 Para iniciar o Scrapper, execute:"
echo "   docker-compose up --build"
echo ""
echo "🌐 O Scrapper estará disponível em:"
echo "   • Interface Web: http://localhost:3000"
echo "   • API Article: http://localhost:3000/api/article"
echo "   • API Links: http://localhost:3000/api/links"
echo "   • API Deep Scrape: http://localhost:3000/api/deep-scrape"
echo "   • Swagger Docs: http://localhost:3000/docs"
echo ""
echo "🎯 Para testar o Deep Scraping, acesse:"
echo "   http://localhost:3000/deep-scrape"
echo "" 