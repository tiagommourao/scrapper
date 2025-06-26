# Scrapper com Deep Scraping Avançado 🧹🔍

## ⚡ Sistema Completo de Deep Scraping com Geração de Documentos Profissionais

Esta versão avançada do **Scrapper** oferece uma solução completa de **Deep Scraping** com funcionalidades profissionais de extração, processamento e exportação de conteúdo web em múltiplos formatos de alta qualidade.

### 🎯 O que é Deep Scraping Avançado?

Nosso sistema vai muito além do scraping tradicional:

1. **Extração recursiva** de conteúdo com controle preciso de profundidade
2. **Interface moderna** com visualização hierárquica e controles intuitivos
3. **6 formatos de exportação** desde básicos até qualidade profissional
4. **Geração server-side** usando WeasyPrint (PDF) e Pandoc (DOCX)
5. **Sistema de cache inteligente** para performance otimizada
6. **Feedback visual completo** com estados de loading e mensagens
7. **Formatação Markdown** para melhor legibilidade do conteúdo

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
- **Deep Scraping UI**: http://localhost:3000/
- **API REST**: http://localhost:3000/api/deep-scrape
- **Documentação API**: http://localhost:3000/docs

## 🎛️ Funcionalidades Avançadas do Deep Scraping

### Parâmetros de Controle Precisos
| Parâmetro | Descrição | Padrão | Limites | Exemplo |
|-----------|-----------|---------|---------|---------|
| **depth** | Profundidade de recursão | 3 | 1-10 | `depth=4` para 4 níveis |
| **max-urls-per-level** | URLs máximas por nível | 10 | 1-50 | `max-urls-per-level=20` |
| **same-domain-only** | Restringir ao mesmo domínio | true | boolean | `same-domain-only=false` |
| **delay-between-requests** | Delay entre requisições (seg) | 1.0 | 0.1-10.0 | `delay-between-requests=2.0` |
| **exclude-patterns** | Padrões de URL para excluir | null | string | `exclude-patterns=/admin,/login` |

### Interface Web Revolucionária

#### 🖥️ Layout Otimizado
- **Container de 90% da tela** para máxima legibilidade
- **Níveis colapsáveis** com ícones animados (▼/►)
- **Alternância HTML/Markdown** para visualização flexível
- **Botões de ação intuitivos** com feedback visual

#### 📱 Responsividade Total
- **Design adaptativo** para desktop, tablet e mobile
- **Controles touch-friendly** para dispositivos móveis
- **Tipografia otimizada** com Pico CSS framework

#### 🎨 Experiência do Usuário
- **Estados de loading** com spinners animados
- **Mensagens de sucesso/erro** com auto-hide
- **Modais interativos** para seleção de formatos
- **Indicadores de progresso** visuais

## 📦 Sistema de Download Avançado (6 Formatos)

### 🔄 Downloads Client-Side (JavaScript)
| Formato | Tecnologia | Descrição | Uso Recomendado |
|---------|------------|-----------|-----------------|
| **ZIP MD** | JSZip | Arquivos Markdown individuais + índice | Organização por páginas |
| **Single MD** | Blob API | Markdown consolidado em arquivo único | Leitura contínua |
| **PDF Client** | jsPDF | PDF básico gerado no navegador | Preview rápido |
| **DOCX Client** | RTF Format | Documento compatível com Word | Edição simples |

### 🏗️ Downloads Server-Side (Python - Alta Qualidade)
| Formato | Tecnologia | Descrição | Vantagens |
|---------|------------|-----------|-----------|
| **PDF Server** | WeasyPrint | PDF profissional com CSS completo | Qualidade tipográfica superior |
| **DOCX Server** | Pandoc | DOCX nativo com formatação avançada | Compatibilidade total com Office |

### 🎯 Modais de Download Inteligentes

#### Modal "Download All MD" (Conteúdo Markdown)
```
┌─────────────────────────────────┐
│  📁 ZIP with Individual Files   │  ← Arquivos separados
│  📄 Single Markdown File        │  ← Arquivo consolidado  
│  📊 PDF from Markdown (Client)  │  ← Preview rápido
│  📝 Word from Markdown (Client) │  ← Edição básica
│  🎨 PDF High Quality (Server)   │  ← Qualidade profissional
│  📋 Word High Quality (Server)  │  ← Office nativo
└─────────────────────────────────┘
```

#### Modal "Download All HTML" (Conteúdo Visual)
```
┌─────────────────────────────────┐
│  📊 PDF from HTML (Client)      │  ← Formatação visual
│  📝 Word from HTML (Client)     │  ← Texto limpo
└─────────────────────────────────┘
```

## 🛠️ Tecnologias e Arquitetura Avançada

### Backend Robusto
```python
# Principais tecnologias
- Python 3.11+ + FastAPI (performance)
- Playwright (browser automation)
- Readability.js (extração de conteúdo)
- WeasyPrint (PDF de alta qualidade)
- Pandoc (DOCX profissional)
- Cache inteligente com TTL
```

### Frontend Moderno
```javascript
// Bibliotecas client-side
- Pico CSS (framework moderno)
- JSZip (compressão de arquivos)
- jsPDF (geração de PDF)
- HTML-to-RTF (conversão para Word)
- Vanilla JS otimizado
```

### Infraestrutura Docker
```dockerfile
# Container otimizado
- Base: playwright/python:v1.51.0-noble
- Pandoc instalado via apt
- WeasyPrint com dependências completas
- Volume persistente para outputs
- Health checks automáticos
```

## 📊 Estrutura de Resposta Completa

### Resposta da API Deep Scrape
```json
{
  "id": "deep_scrape_abc123",
  "base_url": "https://example.com",
  "domain": "example.com", 
  "date": "2024-01-15T10:30:00Z",
  "total_pages": 25,
  "query": {
    "url": "https://example.com",
    "depth": 3,
    "max_urls_per_level": 10
  },
  "levels": [
    {
      "level": 0,
      "pages": [
        {
          "url": "https://example.com",
          "title": "Home Page",
          "content": "<article>Conteúdo HTML extraído...</article>",
          "contentMarkdown": "# Home Page\n\nConteúdo em Markdown...",
          "textContent": "Texto limpo sem tags...",
          "meta": {
            "description": "Meta description",
            "keywords": "palavra, chave",
            "author": "Autor"
          },
          "links_found": 15,
          "processing_time": 2.3
        }
      ]
    }
  ],
  "resultUri": "/view?id=deep_scrape_abc123",
  "screenshotUri": "/static/screenshots/abc123.png"
}
```

### Resposta dos Endpoints de Alta Qualidade
```json
{
  "success": true,
  "download_url": "http://localhost:3000/static/output/deep_scrape_example_20241215_143022.pdf",
  "filename": "deep_scrape_example_20241215_143022.pdf",
  "message": "PDF gerado com sucesso usando WeasyPrint"
}
```

## 🔒 Segurança e Filtros Inteligentes

### Filtros Automáticos Avançados
```python
# URLs problemáticas filtradas
BLOCKED_PATTERNS = [
    '/login', '/admin', '/logout', '/register',
    '/api/', '/rss/', '/feed/', '/sitemap',
    '.pdf', '.zip', '.exe', '.dmg', '.pkg'
]

# Protocolos seguros apenas
ALLOWED_SCHEMES = ['http', 'https']

# Rate limiting inteligente
DEFAULT_DELAY = 1.0  # segundos entre requests
MAX_CONCURRENT = 3   # requests simultâneos
```

### Validação de URLs
- **Domínio permitido** quando `same-domain-only=true`
- **Exclusão de padrões** customizáveis
- **Detecção de loops** infinitos
- **Timeout configurável** por requisição

## 🎯 Casos de Uso Detalhados

### 1. Documentação Técnica Completa
```bash
# Extrair docs Python completas com alta qualidade
curl -X GET "http://localhost:3000/api/deep-scrape" \
  -H "Authorization: Bearer test" \
  -G \
  -d "url=https://docs.python.org/3/tutorial/" \
  -d "depth=4" \
  -d "max-urls-per-level=20" \
  -d "same-domain-only=true"

# Depois gerar PDF profissional
curl -X GET "http://localhost:3000/api/deep-scrape/pdf" \
  -H "Authorization: Bearer test" \
  -G \
  -d "result_id=deep_scrape_docs_python_abc123"
```

### 2. Portal de Notícias com Formatação
```bash
# Scraping de artigos recentes
curl -X GET "http://localhost:3000/api/deep-scrape" \
  -H "Authorization: Bearer test" \
  -G \
  -d "url=https://techcrunch.com" \
  -d "depth=2" \
  -d "max-urls-per-level=25" \
  -d "exclude-patterns=/author,/tag,/category"
```

### 3. Site Corporativo para Análise
```bash
# Análise completa de conteúdo
curl -X GET "http://localhost:3000/api/deep-scrape" \
  -H "Authorization: Bearer test" \
  -G \
  -d "url=https://company.com" \
  -d "depth=3" \
  -d "delay-between-requests=2.0" \
  -d "exclude-patterns=/careers,/contact,/legal"
```

## ⚡ Performance e Otimizações

### Cache Inteligente Multinível
```python
# Sistema de cache otimizado
- Cache de resultados completos (TTL: 1 hora)
- Cache de páginas individuais (TTL: 30 min)  
- Cache de screenshots (TTL: 24 horas)
- Limpeza automática de arquivos antigos
- Compressão automática de dados grandes
```

### Controle de Recursos
- **Semáforos** para concorrência controlada
- **Pool de browsers** reutilizáveis
- **Timeouts escalonados** por profundidade
- **Cleanup automático** de contextos
- **Monitoramento de memória**

### Otimizações de Rede
- **Keep-alive** de conexões HTTP
- **Retry automático** com backoff exponencial
- **Detecção de rate limiting** do servidor
- **Headers otimizados** para performance

## 📈 Monitoramento e Debugging

### Logs Estruturados
```bash
# Acompanhar deep scraping em tempo real
docker-compose logs -f scrapper | grep "deep-scrape"

# Logs específicos de geração de documentos
docker-compose logs -f scrapper | grep -E "(WeasyPrint|Pandoc)"

# Monitorar performance
docker-compose logs -f scrapper | grep "processing_time"
```

### Métricas Detalhadas
- **Total de páginas** processadas por nível
- **Tempo de execução** médio por página
- **URLs filtradas** e motivos
- **Erros por profundidade** com stack traces
- **Taxa de sucesso** por domínio
- **Uso de recursos** (CPU, memória, disco)

### Health Checks
```bash
# Verificar status do sistema
curl http://localhost:3000/health

# Verificar dependências
curl http://localhost:3000/api/deep-scrape/health
```

## 🔄 Comparativo de Funcionalidades

| Funcionalidade | Article | Links | **Deep Scrape v1** | **Deep Scrape v2** |
|----------------|---------|-------|---------------------|---------------------|
| Páginas processadas | 1 | 1 | 1-500+ | 1-500+ |
| Formatos de export | 0 | 0 | 2 básicos | **6 formatos** |
| Qualidade de documentos | ❌ | ❌ | Básica | **Profissional** |
| Interface de download | ❌ | ❌ | Simples | **Modais avançados** |
| Geração server-side | ❌ | ❌ | ❌ | **✅ WeasyPrint + Pandoc** |
| Formatação Markdown | ❌ | ❌ | ❌ | **✅ Conversão HTML→MD** |
| Feedback visual | ❌ | ❌ | Básico | **✅ Loading + Mensagens** |
| Controle de profundidade | ❌ | ❌ | ⚠️ Bugs | **✅ Corrigido** |
| Sistema de cache | ❌ | ❌ | Básico | **✅ Multinível** |
| Nomenclatura de arquivos | ❌ | ❌ | Simples | **✅ Timestamps** |

## 🛠️ Instalação e Configuração Avançada

### Dependências do Sistema
```bash
# Dependências Python
weasyprint~=63.1     # PDF de alta qualidade
playwright>=1.40.0   # Browser automation
fastapi>=0.104.0     # API framework
beautifulsoup4       # HTML parsing

# Dependências do Sistema (Docker)
pandoc               # Conversão para DOCX
fonts-liberation     # Fontes para PDF
libpango-1.0-0      # Renderização de texto
```

### Variáveis de Ambiente
```bash
# .env (opcional)
SCRAPPER_DEBUG=true
SCRAPPER_CACHE_TTL=3600
SCRAPPER_MAX_DEPTH=10
SCRAPPER_OUTPUT_DIR=/app/static/output
WEASYPRINT_DPI=96
PANDOC_DATA_DIR=/usr/share/pandoc
```

### Configuração de Produção
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  scrapper:
    build: .
    environment:
      - SCRAPPER_DEBUG=false
      - SCRAPPER_CACHE_TTL=7200
    volumes:
      - ./data:/app/static/output
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 🐛 Troubleshooting

### Problemas Comuns e Soluções

#### 1. Erro 422 nos Endpoints de Alta Qualidade
```bash
# Problema: result_id não encontrado
# Solução: Verificar se o deep scraping foi executado primeiro
curl -X GET "http://localhost:3000/api/deep-scrape/pdf?result_id=VALID_ID"
```

#### 2. WeasyPrint/Pandoc não Disponível
```bash
# Problema: Dependências não instaladas
# Solução: Reconstruir container
docker-compose down
docker-compose up --build
```

#### 3. Profundidade não Respeitada
```bash
# Problema: Depth sempre = 4 (bug corrigido)
# Solução: Usar versão mais recente
git pull origin master
docker-compose up --build
```

#### 4. Downloads não Funcionam
```bash
# Problema: data-result-id não encontrado
# Solução: Verificar se o template tem o atributo
grep -n "data-result-id" app/templates/view.html
```

### Logs de Debug
```bash
# Ativar logs detalhados
export SCRAPPER_DEBUG=true

# Verificar logs específicos
docker-compose logs scrapper | grep -E "(ERROR|WARNING)"

# Monitorar geração de arquivos
ls -la app/static/output/
```

## 🔮 Roadmap e Melhorias Futuras

### Versão 2.1 (Próxima - Redis Integration) 🚀
**Migração Inteligente para Redis Cache**
- [ ] **Cache Redis Multinível** substituindo sistema de arquivos
  ```python
  # Estruturas Redis planejadas
  scrape_results:{id}     # Hash com metadados do scraping
  scrape_pages:{id}       # List com páginas processadas
  scrape_progress:{id}    # Hash com progresso em tempo real
  scrape_queue           # List para processamento em background
  ```
- [ ] **Sistema de TTL Automático** para limpeza inteligente
- [ ] **Processamento em Background** com Redis Queues
- [ ] **API de Progresso em Tempo Real** via Redis Pub/Sub
- [ ] **Cache de Screenshots** otimizado
- [ ] **Rate Limiting Distribuído** por domínio
- [ ] **Métricas Live** de performance

### Versão 2.2 (Redis Avançado) ⚡
**Funcionalidades Avançadas com Redis**
- [ ] **WebSocket API** para progresso em tempo real
- [ ] **Sessões de Usuário** para múltiplos scrapings simultâneos
- [ ] **Cache Inteligente** por similaridade de URLs
- [ ] **Queue System** para processamento assíncrono
- [ ] **Distributed Locking** para concorrência
- [ ] **Analytics em Tempo Real** de uso
- [ ] **Auto-scaling** baseado em carga

### Versão 3.0 (PostgreSQL + Analytics) 📊
**Persistência e Análise Avançada** (Futuro)
- [ ] **PostgreSQL** para persistência permanente de resultados importantes
- [ ] **Data Pipeline** Redis → PostgreSQL para analytics
- [ ] **Full-Text Search** com índices otimizados
- [ ] **Dashboard Analytics** com métricas históricas
- [ ] **ML para Relevância** de conteúdo automática
- [ ] **API GraphQL** para queries complexas
- [ ] **Data Export** para ferramentas BI

### Arquitetura Evolutiva Planejada

#### 🏗️ Fase Atual (v2.0)
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Browser   │───▶│   FastAPI    │───▶│ File Cache  │
│ (Playwright)│    │   (Python)   │    │   (JSON)    │
└─────────────┘    └──────────────┘    └─────────────┘
```

#### 🚀 Próxima Fase (v2.1 - Redis)
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Browser   │───▶│   FastAPI    │───▶│    Redis    │
│ (Playwright)│    │   (Python)   │    │  (Cache +   │
└─────────────┘    └──────────────┘    │   Queue)    │
                           │            └─────────────┘
                           ▼                   │
                   ┌──────────────┐           │
                   │   WebSocket  │◀──────────┘
                   │  (Progress)  │
                   └──────────────┘
```

#### 🎯 Fase Futura (v3.0 - Full Stack)
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Browser   │───▶│   FastAPI    │───▶│    Redis    │
│ (Playwright)│    │   (Python)   │    │  (Cache)    │
└─────────────┘    └──────────────┘    └─────────────┘
                           │                   │
                           ▼                   ▼
                   ┌──────────────┐    ┌─────────────┐
                   │ PostgreSQL   │◀───│  Pipeline   │
                   │ (Analytics)  │    │  (ETL)      │
                   └──────────────┘    └─────────────┘
```

### 🎯 Por que Redis Primeiro?

#### Vantagens Imediatas
```python
# Performance Superior
- 10-100x mais rápido que arquivo para cache
- Operações atômicas nativas
- TTL automático sem código adicional

# Estruturas de Dados Ricas
redis_client.hset(f"scrape:{id}", mapping={
    "status": "processing",
    "progress": "45%",
    "pages_found": 23,
    "current_level": 2
})

# Pub/Sub para Tempo Real
redis_client.publish(f"progress:{id}", json.dumps({
    "level": 2,
    "pages_processed": 15,
    "eta_seconds": 120
}))
```

#### Casos de Uso Ideais
- **Cache Temporário**: Resultados com TTL configurável
- **Processamento Assíncrono**: Queues para deep scraping
- **Progresso em Tempo Real**: Pub/Sub para WebSocket
- **Rate Limiting**: Contadores distribuídos
- **Sessões**: Estado de usuário temporário

### 🛠️ Plano de Implementação Redis

#### Fase 1: Migração do Cache (1-2 semanas)
```python
# Substituir cache de arquivo por Redis
class RedisCache:
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379, db=0)
    
    def store_result(self, key: str, data: dict, ttl: int = 3600):
        """Armazenar resultado com TTL automático"""
        self.redis.hset(f"scrape:{key}", mapping=data)
        self.redis.expire(f"scrape:{key}", ttl)
    
    def get_result(self, key: str) -> dict:
        """Recuperar resultado do cache"""
        return self.redis.hgetall(f"scrape:{key}")
```

#### Fase 2: Processamento Assíncrono (2-3 semanas)
```python
# Background processing com Redis Queue
import rq
from rq import Worker

def deep_scrape_async(url: str, params: dict):
    """Processar scraping em background"""
    job = redis_queue.enqueue(
        'scrape_worker.deep_scrape_job',
        url, params,
        job_timeout='30m'
    )
    return job.id

# Worker dedicado
worker = Worker(['scrape_queue'], connection=redis_client)
worker.work()
```

#### Fase 3: Progresso em Tempo Real (1-2 semanas)
```python
# WebSocket + Redis Pub/Sub
@app.websocket("/ws/progress/{scrape_id}")
async def websocket_progress(websocket: WebSocket, scrape_id: str):
    await websocket.accept()
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"progress:{scrape_id}")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            await websocket.send_text(message['data'])
```

### Integrações Futuras (v2.x)
- [ ] **Slack/Discord** bots para scraping
- [ ] **GitHub Actions** para scraping automatizado  
- [ ] **S3/Cloud Storage** para arquivos grandes
- [ ] **Elasticsearch** para busca full-text
- [ ] **Grafana** dashboards para métricas

### 🚀 Migração Redis: Benefícios Técnicos

#### Performance Comparativa
```python
# Operações por segundo (estimativa)
File Cache:     ~100 ops/sec    (I/O bound)
Redis Cache:    ~10,000 ops/sec (Memory bound)
PostgreSQL:     ~1,000 ops/sec  (Network + Disk)

# Latência típica
File Cache:     10-50ms   (disk read/write)
Redis Cache:    0.1-1ms   (memory access)
PostgreSQL:     1-10ms    (network + query)
```

#### Estrutura de Dados Redis
```python
# Schema Redis planejado
{
    # Metadados do scraping
    "scrape:{id}": {
        "status": "completed|processing|failed",
        "base_url": "https://example.com",
        "domain": "example.com", 
        "total_pages": 25,
        "current_level": 3,
        "progress_percent": 85,
        "started_at": "2024-01-15T10:30:00Z",
        "estimated_completion": "2024-01-15T10:45:00Z"
    },
    
    # Páginas processadas (List)
    "scrape_pages:{id}": [
        {"url": "...", "title": "...", "level": 0},
        {"url": "...", "title": "...", "level": 1}
    ],
    
    # Queue de processamento
    "scrape_queue": ["job_id_1", "job_id_2", "job_id_3"],
    
    # Rate limiting por domínio
    "rate_limit:example.com": 5,  # requests nos últimos 5 segundos
    
    # Cache de screenshots
    "screenshot:{url_hash}": "base64_image_data"
}
```

#### Docker Compose Atualizado
```yaml
# docker-compose.redis.yml (próxima versão)
version: '3.8'
services:
  scrapper:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "3000:3000"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
  
  redis-worker:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    command: python -m app.workers.scrape_worker

volumes:
  redis_data:
```

### 📋 Checklist de Migração

#### Preparação (Antes da Implementação)
- [ ] **Análise de Dados**: Mapear estruturas atuais para Redis
- [ ] **Benchmarks**: Testar performance Redis vs arquivo
- [ ] **Backup Strategy**: Plano para migração de dados existentes
- [ ] **Monitoring**: Configurar Redis monitoring

#### Implementação Incremental
- [ ] **Fase 1**: Redis como cache secundário (fallback para arquivo)
- [ ] **Fase 2**: Redis como cache primário (arquivo como backup)
- [ ] **Fase 3**: Apenas Redis (remover sistema de arquivo)
- [ ] **Fase 4**: Adicionar funcionalidades avançadas (pub/sub, queues)

#### Validação e Rollback
- [ ] **Testes de Carga**: Comparar performance antes/depois
- [ ] **Testes de Funcionalidade**: Validar todos os endpoints
- [ ] **Plano de Rollback**: Reverter para arquivo se necessário
- [ ] **Monitoring**: Alertas para problemas de Redis

### 🎯 Próximos Passos Sugeridos

1. **Semana 1-2**: Setup Redis básico + migração de cache simples
2. **Semana 3-4**: Implementar background processing
3. **Semana 5-6**: WebSocket + progresso em tempo real
4. **Semana 7-8**: Otimizações e refinamentos

**Quer começar com a implementação Redis? Posso ajudar com:**
- Setup inicial do Redis no Docker Compose
- Migração incremental do sistema de cache
- Implementação de background jobs
- WebSocket para progresso em tempo real

## 🤝 Contribuindo

### Como Contribuir
1. **Fork** o repositório
2. **Clone** localmente: `git clone your-fork-url`
3. **Crie uma branch**: `git checkout -b feature/nova-funcionalidade`
4. **Implemente** com testes: `pytest app/`
5. **Commit** seguindo convenções: `git commit -m "feat: adiciona funcionalidade X"`
6. **Push**: `git push origin feature/nova-funcionalidade`
7. **Pull Request** com descrição detalhada

### Padrões de Código
```python
# Seguir PEP 8
black app/                    # Formatação
ruff app/                     # Linting
pytest app/ --cov=app/       # Testes com cobertura
mypy app/                     # Type checking
```

### Testes
```bash
# Executar todos os testes
pytest app/ -v

# Testes específicos do deep scraping
pytest app/router/tests/test_deep_scrape.py -v

# Testes de integração
pytest app/test_main.py::test_deep_scrape_integration -v
```

## 📞 Suporte e Comunidade

### Links Úteis
- **📋 Issues**: [GitHub Issues](https://github.com/tiagommourao/scrapper/issues)
- **📖 Documentação**: [/docs/DEEP_SCRAPING.md](./docs/DEEP_SCRAPING.md)
- **🔧 API Docs**: http://localhost:3000/docs
- **💬 Discussões**: [GitHub Discussions](https://github.com/tiagommourao/scrapper/discussions)

### Exemplos Avançados
```bash
# Repositório de exemplos
git clone https://github.com/tiagommourao/scrapper-examples
cd scrapper-examples/deep-scraping/

# Executar exemplos
python examples/documentation_scraper.py
python examples/news_aggregator.py
python examples/ecommerce_analyzer.py
```

## 📊 Estatísticas do Projeto

### Funcionalidades Implementadas
- ✅ **Deep Scraping Recursivo** (100%)
- ✅ **6 Formatos de Download** (100%)
- ✅ **Interface Moderna** (100%)
- ✅ **Geração de Alta Qualidade** (100%)
- ✅ **Sistema de Cache** (100%)
- ✅ **Feedback Visual** (100%)
- ✅ **Controle de Bugs** (100%)

### Commits Principais
1. `feat: implementa formatação Markdown para Deep Scraping`
2. `feat: melhora interface com container 90% e download avançado`
3. `fix: corrige controle de depth e sistema dual de download`
4. `fix: corrige exportação DOCX/PDF para usar texto limpo`
5. `feat: implementa geração de alta qualidade com WeasyPrint/Pandoc`
6. `fix: corrige endpoints PDF/DOCX com result_id`

---

## 🎉 Conclusão

**O Scrapper com Deep Scraping Avançado** representa uma solução completa e profissional para extração de conteúdo web. Com **6 formatos de exportação**, **interface moderna**, **geração de documentos de alta qualidade** e **sistema robusto de cache**, oferece tudo que você precisa para projetos desde simples até enterprise.

### 🚀 **Próximos Passos**
1. **Execute** um deep scraping de teste
2. **Experimente** todos os 6 formatos de download
3. **Compare** a qualidade entre client-side e server-side
4. **Explore** as possibilidades para seu projeto

**Transforme qualquer site em documentação profissional com apenas alguns cliques!** 📚✨ 