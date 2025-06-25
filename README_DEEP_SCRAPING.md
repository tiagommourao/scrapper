# Scrapper com Deep Scraping 🧹🔍

## ⚡ Nova Funcionalidade: Deep Scraping Recursivo

Esta versão estendida do **Scrapper** inclui uma poderosa funcionalidade de **Deep Scraping** que permite extrair conteúdo de forma recursiva de sites inteiros, controlando a profundidade de navegação.

### 🎯 O que é Deep Scraping?

Diferentemente do scraping tradicional que analisa apenas uma página, o Deep Scraping:

1. **Extrai conteúdo da URL base**
2. **Encontra todos os links na página**
3. **Segue os links encontrados recursivamente**
4. **Organiza resultados hierarquicamente por nível**
5. **Aplica filtros inteligentes** para evitar URLs problemáticas

## 🚀 Quick Start

### 1. Setup Rápido
```bash
# Windows
./setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### 2. Iniciar o Container
```bash
docker-compose up --build
```

### 3. Acessar a Interface
- **Deep Scraping UI**: http://localhost:3000/deep-scrape
- **API REST**: http://localhost:3000/api/deep-scrape
- **Docs**: http://localhost:3000/docs

## 🎛️ Funcionalidades do Deep Scraping

### Parâmetros de Controle
| Parâmetro | Descrição | Padrão | Limites |
|-----------|-----------|---------|---------|
| **depth** | Profundidade de recursão | 3 | 1-10 |
| **max-urls-per-level** | URLs máximas por nível | 10 | 1-50 |
| **same-domain-only** | Restringir ao mesmo domínio | true | boolean |
| **delay-between-requests** | Delay entre requisições (seg) | 1.0 | 0.1-10.0 |
| **exclude-patterns** | Padrões de URL para excluir | null | string |

### Interface Web Intuitiva
- ✅ **Formulário dedicado** com controles específicos
- ✅ **Configuração visual** de parâmetros
- ✅ **Visualização hierárquica** dos resultados
- ✅ **Resumo estatístico** de páginas processadas

### API REST Completa
```bash
# Exemplo básico
curl "http://localhost:3000/api/deep-scrape?url=https://example.com&depth=3"

# Exemplo avançado
curl "http://localhost:3000/api/deep-scrape?url=https://docs.example.com&depth=4&max-urls-per-level=15&same-domain-only=true&exclude-patterns=/admin,/login"
```

## 📊 Estrutura de Resposta

```json
{
  "id": "abc123",
  "base_url": "https://example.com",
  "domain": "example.com",
  "total_pages": 25,
  "levels": [
    {
      "level": 0,
      "pages": [
        {
          "url": "https://example.com",
          "title": "Home Page",
          "content": "<p>Conteúdo extraído...</p>",
          "textContent": "Texto limpo...",
          "meta": {...}
        }
      ]
    },
    {
      "level": 1,
      "pages": [...]
    }
  ]
}
```

## 🔒 Segurança e Filtros

### Filtros Automáticos
- **URLs problemáticas**: `/login`, `/admin`, `/logout`
- **Arquivos binários**: `.pdf`, `.zip`, `.exe`
- **Protocolos especiais**: `mailto:`, `tel:`, `javascript:`
- **APIs e feeds**: `/api/`, `/rss/`, `/feed/`

### Rate Limiting Inteligente
- **Delay configurável** entre requisições
- **Respeito aos servidores** com limites sensatos
- **Controle de concorrência** otimizado

## 🎯 Casos de Uso

### 1. Documentação Técnica
```bash
# Extrair documentação completa
curl "localhost:3000/api/deep-scrape?url=https://docs.python.org&depth=4&same-domain-only=true"
```

### 2. Portal de Notícias
```bash
# Scraping de artigos recentes
curl "localhost:3000/api/deep-scrape?url=https://techcrunch.com&depth=2&max-urls-per-level=20"
```

### 3. Site Corporativo
```bash
# Análise completa de conteúdo
curl "localhost:3000/api/deep-scrape?url=https://company.com&depth=3&exclude-patterns=/careers,/contact"
```

## 🛠️ Tecnologias e Arquitetura

### Backend Robusto
- **Python + FastAPI** para performance
- **Playwright** para browser automation
- **Readability.js** para extração de conteúdo
- **Algoritmo BFS** para navegação eficiente

### Frontend Moderno
- **Interface responsiva** com Pico CSS
- **Controles dinâmicos** para configuração
- **Visualização hierárquica** dos resultados
- **JavaScript otimizado** para UX fluída

### Infraestrutura
- **Docker + Docker Compose** para deploy
- **Cache inteligente** para otimização
- **Logs detalhados** para monitoramento
- **Health checks** para confiabilidade

## ⚡ Performance e Otimizações

### Cache Avançado
- **Evita URLs duplicadas** automaticamente
- **Cache de resultados** para consultas repetidas
- **Limpeza automática** de arquivos antigos

### Controle de Recursos
- **Semáforos** para concorrência controlada
- **Timeouts configuráveis** para stability
- **Cleanup automático** de contextos de browser

## 📈 Monitoramento

### Logs Estruturados
```bash
# Acompanhar deep scraping em tempo real
docker-compose logs -f scrapper | grep "deep-scrape"
```

### Métricas Disponíveis
- Total de páginas processadas
- Tempo de execução por nível
- URLs filtradas e ignoradas
- Erros por profundidade

## 🔄 Comparativo de Funcionalidades

| Funcionalidade | Article | Links | **Deep Scrape** |
|----------------|---------|-------|-----------------|
| Páginas processadas | 1 | 1 | 1-500+ |
| Estrutura de dados | Simples | Lista | **Hierárquica** |
| Controle de profundidade | ❌ | ❌ | **✅** |
| Navegação recursiva | ❌ | ❌ | **✅** |
| Filtros inteligentes | ❌ | Básico | **Avançados** |
| Rate limiting | ❌ | ❌ | **✅** |

## 🤝 Contribuindo

### Melhorias Futuras
- [ ] **Processamento paralelo** por nível
- [ ] **Base de dados** para resultados grandes
- [ ] **API de progresso** em tempo real
- [ ] **Webhooks** para notificações
- [ ] **ML para relevância** de conteúdo

### Como Contribuir
1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente os testes
4. Submeta um Pull Request

## 📞 Suporte

- **Issues**: [GitHub Issues](https://github.com/amerkurev/scrapper/issues)
- **Documentação**: `/docs/DEEP_SCRAPING.md`
- **API Docs**: http://localhost:3000/docs

---

**🎉 Agora você tem o poder do Deep Scraping em suas mãos!**

Extraia conteúdo de sites inteiros de forma inteligente, respeitosa e eficiente. 🚀 