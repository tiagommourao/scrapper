# Deep Scraping - Scrapping Recursivo

## 🎯 Visão Geral

A funcionalidade **Deep Scraping** do Scrapper permite extrair conteúdo de forma recursiva de um site inteiro, controlando a profundidade de navegação. Diferentemente do scraping tradicional que analisa apenas uma página, o Deep Scraping:

1. **Extrai conteúdo da URL base**
2. **Encontra todos os links na página**
3. **Segue os links encontrados**
4. **Repete o processo recursivamente** até a profundidade especificada

## 🚀 Como Usar

### Inicialização Completa
```bash
# Iniciar todos os serviços (Scrapper + Redis + Worker)
docker-compose up --build -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### Interface Web
Acesse `http://localhost:3000/deep-scrape` e configure:

- **URL Base**: A URL raiz para iniciar o scraping
- **Profundidade**: Níveis de recursão (1-10)
- **URLs por Nível**: Limite de URLs processadas por nível
- **Mesmo Domínio**: Restringir ao domínio original
- **Delay**: Intervalo entre requisições (segundos)
- **Padrões de Exclusão**: URLs a serem ignoradas

### API REST

```bash
curl -X GET "http://localhost:3000/api/deep-scrape?url=https://example.com&depth=3&max-urls-per-level=10"
```

## 📋 Parâmetros

### Parâmetros Específicos do Deep Scraping

| Parâmetro | Descrição | Padrão | Limites |
|-----------|-----------|---------|---------|
| `depth` | Profundidade máxima de recursão | 3 | 1-10 |
| `max-urls-per-level` | Máximo de URLs por nível | 10 | 1-50 |
| `same-domain-only` | Restringir ao mesmo domínio | true | boolean |
| `delay-between-requests` | Delay entre requisições (segundos) | 1.0 | 0.1-10.0 |
| `exclude-patterns` | Padrões de URL para excluir | null | string |

### Parâmetros Herdados
O Deep Scraping também aceita todos os parâmetros do scraping tradicional:
- Configurações de browser (`device`, `timeout`, `user-agent`, etc.)
- Configurações de proxy (`proxy-server`, `proxy-username`, etc.)
- Configurações do Readability (`char-threshold`, `max-elems-to-parse`, etc.)
- Configurações gerais (`cache`, `screenshot`, `full-content`, etc.)

## 📊 Estrutura de Resposta

```json
{
  "id": "abc123",
  "base_url": "https://example.com",
  "domain": "example.com",
  "date": "2024-01-15T10:30:00Z",
  "total_pages": 25,
  "query": {...},
  "resultUri": "http://localhost:3000/result/abc123",
  "screenshotUri": "http://localhost:3000/screenshot/abc123",
  "levels": [
    {
      "level": 0,
      "pages": [
        {
          "url": "https://example.com",
          "title": "Home Page",
          "content": "<p>Conteúdo extraído...</p>",
          "textContent": "Conteúdo em texto...",
          "level": 0,
          "parent_index": -1,
          "meta": {...}
        }
      ]
    },
    {
      "level": 1,
      "pages": [
        {
          "url": "https://example.com/about",
          "title": "Sobre Nós",
          "content": "<p>Mais conteúdo...</p>",
          "level": 1,
          "parent_index": 0,
          "meta": {...}
        }
      ]
    }
  ]
}
```

## 🔒 Filtros de Segurança

O sistema inclui filtros automáticos para evitar URLs problemáticas:

### URLs Excluídas Automaticamente
- `/login`, `/logout`, `/register`, `/signup`, `/admin`
- Arquivos: `.pdf`, `.doc`, `.docx`, `.zip`, `.exe`, `.dmg`
- Protocolos especiais: `mailto:`, `tel:`, `javascript:`
- Feeds: `/feed`, `/rss`, `/api/`, `/ajax/`
- Fragmentos: URLs com `#` apenas

### Padrões Personalizados
Use o parâmetro `exclude-patterns` para adicionar seus próprios filtros:
```
exclude-patterns=/admin,/login,/private,/download
```

## 🏗️ Arquitetura de Serviços

O Deep Scraping utiliza uma arquitetura distribuída com três serviços principais:

### 1. **Scrapper** (Web API)
- Interface web e API REST
- Recebe requisições de deep scraping
- Enfileira jobs no Redis
- Serve resultados processados

### 2. **Redis** (Cache & Queue)
- Cache inteligente de resultados
- Queue de jobs para processamento assíncrono
- Pub/Sub para progresso em tempo real
- Distributed locking para evitar duplicação

### 3. **Worker** (Processamento)
- Processa jobs de deep scraping de forma assíncrona
- Executa scraping recursivo com Playwright
- Publica progresso via Redis Pub/Sub
- Implementa distributed locking

### Fluxo de Processamento
```
[Cliente] → [API] → [Redis Queue] → [Worker] → [Cache] → [Cliente]
```

1. Cliente envia requisição para API
2. API verifica cache e enfileira job se necessário
3. Worker processa job assincronamente
4. Resultado é salvo no cache
5. Cliente recebe resultado via WebSocket ou polling

## ⚡ Otimizações de Performance

### Rate Limiting
- **Delay configurável** entre requisições
- **Limite de URLs por nível** para evitar sobrecarga
- **Limite de profundidade** para controlar recursos

### Cache Inteligente
- **Evita URLs duplicadas** automaticamente
- **Cache de resultados** para requisições repetidas
- **Reutilização** de contextos de browser

#### Cache Inteligente por Similaridade de URLs
O sistema utiliza uma estratégia avançada de cache para evitar processamento e armazenamento redundante de páginas que, apesar de pequenas diferenças na URL, representam o mesmo conteúdo. 

**Como funciona:**
- Antes de consultar ou gravar no cache, a URL é normalizada:
  - Parâmetros irrelevantes (ex: `utm_*`, `ref`, `session`, `fbclid`, etc) são removidos
  - Fragmentos/anchors (`#...`) são ignorados
  - Trailing slashes são normalizados
  - O host é convertido para minúsculas
- O cache Redis e o cache de arquivos usam a URL normalizada como chave
- Isso garante que URLs como:
  - `https://site.com/page?utm_source=google`
  - `https://site.com/page/`
  - `https://SITE.com/page#section`
  - `https://site.com/page?ref=twitter`
  sejam tratadas como a mesma entrada de cache

**Benefícios:**
- Reduz drasticamente o processamento duplicado
- Economiza recursos de rede, CPU e armazenamento
- Melhora a experiência do usuário, entregando resultados mais rápidos

**Observação:**
Se necessário, a lista de parâmetros ignorados pode ser customizada no código (`util.py`).

### Processamento Paralelo
- **Semáforos** para controlar concorrência
- **Contexts isolados** para cada página
- **Cleanup automático** de recursos

## 🎯 Casos de Uso

### 1. Documentação Técnica
```bash
# Extrair toda documentação de um projeto
curl "localhost:3000/api/deep-scrape?url=https://docs.example.com&depth=4&same-domain-only=true"
```

### 2. Portal de Notícias
```bash
# Scraping de artigos recentes
curl "localhost:3000/api/deep-scrape?url=https://news.example.com&depth=2&max-urls-per-level=20"
```

### 3. Site Corporativo
```bash
# Análise completa de site
curl "localhost:3000/api/deep-scrape?url=https://company.com&depth=3&exclude-patterns=/careers,/contact"
```

## 🛡️ Considerações Éticas

### Respeito aos Servidores
- **Delay obrigatório** entre requisições (mínimo 0.1s)
- **Limites sensatos** de URLs e profundidade
- **User-Agent identificável** nas requisições

### Conformidade Legal
- **Respeite robots.txt** manualmente
- **Verifique termos de uso** dos sites
- **Use apenas para fins legítimos**

### Boas Práticas
- **Teste com profundidade baixa** primeiro
- **Monitor logs** para detectar problemas
- **Configure delays adequados** para cada site

## 🔧 Troubleshooting

### Erro: "Muitas URLs encontradas"
- Reduza `max-urls-per-level`
- Adicione `exclude-patterns` mais específicos
- Diminua a `depth`

### Erro: "Timeout na requisição"
- Aumente `timeout` nos parâmetros de browser
- Verifique conectividade com o site
- Reduza `max-urls-per-level`

### Performance Lenta
- Aumente `delay-between-requests`
- Reduza `depth` e `max-urls-per-level`
- Use `same-domain-only=true`

## 📈 Monitoramento

### Logs Importantes
```bash
# Acompanhar progresso do deep scraping
docker-compose logs -f scrapper | grep "deep-scrape"
```

### Métricas de Performance
- **Total de páginas** processadas
- **Tempo total** de execução
- **URLs ignoradas** por filtros
- **Erros por nível** de profundidade

## 🔄 Atualizações Futuras

### Funcionalidades Planejadas
- [ ] **Scraping paralelo** por nível
- [ ] **Base de dados** para resultados grandes
- [ ] **API de status** para acompanhar progresso
- [ ] **Webhooks** para notificações
- [ ] **Filtros ML** para relevância de conteúdo

### Melhorias de Performance
- [ ] **Redis** para cache distribuído
- [ ] **Queue system** para processamento assíncrono
- [ ] **CDN** para screenshots e assets
- [ ] **Compressão** de resultados grandes 