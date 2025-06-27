"use strict";
!function() {
    function formatParams() {
        let url = document.getElementById("url").value;
        if (!url) return "";
        let params = {
          url: url
        };

        // Add deep scraping specific parameters if on deep-scrape page
        if (window.location.pathname === '/deep-scrape') {
            let depth = document.getElementById("depth");
            let maxUrls = document.getElementById("max-urls");
            let delay = document.getElementById("delay");
            let sameDomain = document.getElementById("same-domain");
            let excludePatterns = document.getElementById("exclude-patterns");
            
            if (depth && depth.value) params.depth = depth.value;
            if (maxUrls && maxUrls.value) params["max-urls-per-level"] = maxUrls.value;
            if (delay && delay.value) params["delay-between-requests"] = delay.value;
            if (sameDomain) params["same-domain-only"] = sameDomain.checked ? "true" : "false";
            if (excludePatterns && excludePatterns.value) params["exclude-patterns"] = excludePatterns.value;
        }

        document.getElementById("query-params").value.split(/\r?\n/).forEach((line) => {
            line = line.replace(/^\s+|\s+$/g, '');
            if (line) {
                let parts = line.split("=");
                if (parts.length === 2) {
                    params[parts[0]] = parts[1];
                } else if (parts.length === 1) {
                    params[parts[0]] = null;
                }
            }
        });

        return "?" + Object
            .keys(params)
            .map((key) => {
                if (params[key] === null) return key;
                return key+"="+encodeURIComponent(params[key]);
            })
            .join("&");
    };

    let selectRoute = document.getElementById("select-route");
    let scrapeIt = document.getElementById("scrape-it");
    scrapeIt.addEventListener("click", (e) => {
        e.preventDefault();
        let errors = document.getElementById("errors");
        let params = formatParams();
        
        // Use async endpoint for deep scraping
        if (window.location.pathname === '/deep-scrape') {
            startAsyncDeepScrape(params, errors, scrapeIt, selectRoute);
        } else {
            // Use synchronous endpoint for article and links
            let xhr = new XMLHttpRequest();
            xhr.open("GET", apiEndpoint + params, true);
            xhr.send();
            xhr.onreadystatechange = (e) => {
                if (xhr.readyState == 4) { // DONE: The operation is complete.
                    if (xhr.status == 200) {
                        let response = JSON.parse(xhr.responseText);
                        window.location.href = "/view/" + response.id;
                    } else {
                        // Handle error
                        try {
                            let json = JSON.parse(xhr.responseText);
                            errors.innerHTML = "<pre>An error occurred\n" + JSON.stringify(json, null, 2) + "</pre>";
                        } catch(err) {
                            let lines = ["An error occurred. See the server log for more details.", xhr.responseText]
                            errors.innerHTML = "<pre>" + lines.join("\n\n") + "</pre>"
                        }
                        errors.style.display = "block";
                    }
                    scrapeIt.innerHTML = "Scrape it!";
                    scrapeIt.removeAttribute("aria-busy");
                    selectRoute.style.visibility = "visible";
                }
            };
            scrapeIt.innerHTML = "Please wait…";
            scrapeIt.setAttribute("aria-busy", "true");
            selectRoute.style.visibility = "hidden";
        }
    });

    var url = document.getElementById("url");
    var queryParams = document.getElementById("query-params");

    // watch for changes in the query params and update the snippet
    function updateSnippet() {
        let params = formatParams();

        // create a snippet
        let snippet = document.getElementById("snippet");
        let snippetLink = document.getElementById("snippetLink");
        let snippetLabel = document.getElementById("snippetLabel");
        if (params === "") {
            snippet.style.display = "none";
        } else {
            let hostname = window.location.protocol + "//" + window.location.host;
            snippetLink.innerHTML = hostname + apiEndpoint + params;
            snippetLink.setAttribute("href", apiEndpoint + params);
            snippetLabel.innerHTML = "Request URL:"
            snippet.style.display = "block";
        }

        // save the query params to local storage
        localStorage.setItem("url", url.value);
        localStorage.setItem("queryParams", queryParams.value);
    }

    // code below is executed when the page loads...
    url.value = localStorage.getItem("url") || "";
    queryParams.value = localStorage.getItem("queryParams") || "";
    updateSnippet();

    // add event listeners to the url and query params fields to update the snippet and save to local storage
    url.addEventListener("input", updateSnippet);
    queryParams.addEventListener("input", updateSnippet);
    
    // add event listeners for deep scraping controls if they exist
    if (window.location.pathname === '/deep-scrape') {
        let deepScrapeControls = ['depth', 'max-urls', 'delay', 'same-domain', 'exclude-patterns'];
        deepScrapeControls.forEach(controlId => {
            let control = document.getElementById(controlId);
            if (control) {
                control.addEventListener("input", updateSnippet);
                control.addEventListener("change", updateSnippet);
            }
        });
    }

    // then open the query params details if there are query params in local storage already (i.e. the user has already used the scrapper)
    if (queryParams.value) {
        document.getElementById("query-params-details").setAttribute("open", "");
    }

    // --- Async Deep Scraping Functions ---
    
    function startAsyncDeepScrape(params, errors, scrapeIt, selectRoute) {
        // Parse params to create request payload
        let urlParams = new URLSearchParams(params.substring(1)); // remove leading '?'
        let payload = {
            // Default values
            depth: 3,
            max_urls_per_level: 10,
            same_domain_only: true,
            delay_between_requests: 1.0,
            exclude_patterns: [],
            cache: true,
            screenshot: false,
            timeout: 30,
            readability: true,
            include_raw_html: false,
            include_screenshot: false
        };
        
        for (let [key, value] of urlParams) {
            if (key === 'url') {
                payload.url = value;
            } else if (key === 'depth') {
                payload.depth = parseInt(value);
            } else if (key === 'max-urls-per-level') {
                payload.max_urls_per_level = parseInt(value);
            } else if (key === 'delay-between-requests') {
                payload.delay_between_requests = parseFloat(value);
            } else if (key === 'same-domain-only') {
                payload.same_domain_only = value === 'true';
            } else if (key === 'exclude-patterns') {
                payload.exclude_patterns = value.split(',').map(p => p.trim()).filter(p => p);
            } else if (key === 'cache') {
                payload.cache = value === 'true';
            } else if (key === 'screenshot') {
                payload.screenshot = value === 'true';
            } else if (key === 'timeout') {
                payload.timeout = parseInt(value);
            } else if (key === 'readability') {
                payload.readability = value === 'true';
            } else if (key === 'include_raw_html') {
                payload.include_raw_html = value === 'true';
            } else if (key === 'include_screenshot') {
                payload.include_screenshot = value === 'true';
            }
            // Ignorar outros parâmetros que não são reconhecidos
        }

        scrapeIt.innerHTML = "Iniciando...";
        scrapeIt.setAttribute("aria-busy", "true");
        selectRoute.style.visibility = "hidden";
        errors.style.display = "none";

        // Debug: log payload
        console.log('Deep scrape payload:', JSON.stringify(payload, null, 2));

        fetch('/api/deep-scrape/async', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success && result.job_id) {
                showProgressModal();
                startDeepScrapeWebSocket(result.job_id, function onDone() {
                    // Buscar resultado ao finalizar
                    fetchStatusWithRetry(result.job_id, 5, 500)
                        .then(statusData => {
                            hideProgressModal();
                            checkForManualGeneration(statusData.result_id);
                        })
                        .catch(() => {
                            hideProgressModal();
                            showError(errors, 'Erro ao obter resultado final.');
                            resetButton(scrapeIt, selectRoute);
                        });
                });
            } else {
                showError(errors, result.error || 'Erro ao enfileirar scraping.');
                resetButton(scrapeIt, selectRoute);
            }
        })
        .catch(err => {
            console.error('Erro detalhado:', err);
            showError(errors, 'Erro de conexão ao iniciar scraping: ' + err.message);
            resetButton(scrapeIt, selectRoute);
        });
    }

    function startDeepScrapeWebSocket(jobId, onDone) {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/deep-scrape/${jobId}`;
        const progressBar = document.getElementById('progress-bar');
        const progressStatus = document.getElementById('progress-status');
        const progressError = document.getElementById('progress-error');

        let ws;
        try {
            ws = new WebSocket(wsUrl);
        } catch (e) {
            showProgressError('Erro ao conectar ao WebSocket.');
            return;
        }

        ws.onopen = () => {
            updateProgressStatus('Conectado. Processando...');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.error) {
                    showProgressError('Erro: ' + data.error);
                    ws.close();
                    return;
                }
                const percent = data.percent || 0;
                updateProgress(percent, `Progresso: ${percent}% | Nível: ${data.current_level ?? '-'} | Página: ${data.current_page ?? '-'}`);
                
                if (percent >= 100) {
                    updateProgressStatus('Finalizado! Redirecionando...');
                    setTimeout(() => {
                        ws.close();
                        if (typeof onDone === 'function') onDone();
                    }, 1000);
                }
            } catch (e) {
                showProgressError('Erro ao processar evento.');
            }
        };

        ws.onerror = (e) => {
            showProgressError('Erro de conexão WebSocket.');
        };

        ws.onclose = () => {
            const currentProgress = progressBar ? progressBar.value : 0;
            if (currentProgress < 100) {
                showProgressError('Conexão encerrada antes do fim.');
            }
        };
    }

    // Progress Modal Functions
    function showProgressModal() {
        let modal = document.getElementById('progress-modal');
        if (!modal) {
            modal = createProgressModal();
        }
        modal.style.display = 'flex';
        updateProgress(0, 'Iniciando...');
    }

    function hideProgressModal() {
        const modal = document.getElementById('progress-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    function createProgressModal() {
        const modal = document.createElement('div');
        modal.id = 'progress-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 8px;
            max-width: 500px;
            width: 90%;
            text-align: center;
        `;

        content.innerHTML = `
            <h3>Processando Deep Scraping</h3>
            <progress id="progress-bar" value="0" max="100" style="width: 100%; height: 20px; margin: 1rem 0;"></progress>
            <p id="progress-status">Iniciando...</p>
            <p id="progress-error" style="color: #c00; display: none;"></p>
        `;

        modal.appendChild(content);
        document.body.appendChild(modal);
        return modal;
    }

    function updateProgress(percent, status) {
        const progressBar = document.getElementById('progress-bar');
        const progressStatus = document.getElementById('progress-status');
        if (progressBar) progressBar.value = percent;
        if (progressStatus) progressStatus.textContent = status;
    }

    function updateProgressStatus(status) {
        const progressStatus = document.getElementById('progress-status');
        if (progressStatus) progressStatus.textContent = status;
    }

    function showProgressError(error) {
        const progressError = document.getElementById('progress-error');
        if (progressError) {
            progressError.textContent = error;
            progressError.style.display = 'block';
        }
    }

    function showError(errorsElement, message) {
        errorsElement.innerHTML = `<pre>Erro: ${message}</pre>`;
        errorsElement.style.display = "block";
    }

    function resetButton(scrapeIt, selectRoute) {
        scrapeIt.innerHTML = "Scrape it!";
        scrapeIt.removeAttribute("aria-busy");
        selectRoute.style.visibility = "visible";
    }

    function fetchStatusWithRetry(jobId, retries = 5, delay = 500) {
        return new Promise((resolve, reject) => {
            function attempt(n) {
                fetch(`/api/deep-scrape/status/${jobId}`)
                    .then(resp => resp.json())
                    .then(statusData => {
                        if (statusData.success && statusData.result_id) {
                            resolve(statusData);
                        } else if (n > 0) {
                            setTimeout(() => attempt(n - 1), delay);
                        } else {
                            reject(statusData);
                        }
                    })
                    .catch(reject);
            }
            attempt(retries);
        });
    }
    
    function checkForManualGeneration(resultId) {
        const enableManual = document.getElementById('enable-manual');
        
        if (enableManual && enableManual.checked) {
            // Gerar manual
            generateManual(resultId);
        } else {
            // Ir direto para o resultado
            window.location.href = "/view/" + resultId;
        }
    }
    
    function generateManual(resultId) {
        const format = document.getElementById('manual-format').value;
        const style = document.getElementById('manual-style').value;
        const enableTranslation = document.getElementById('enable-translation').checked;
        const prepareForRag = document.getElementById('prepare-for-rag').checked;
        const sourceLanguage = document.getElementById('source-language').value;
        const targetLanguage = document.getElementById('target-language').value;
        const translationProvider = document.getElementById('translation-provider').value;
        const translationApiKey = document.getElementById('translation-api-key').value;
        
        const payload = {
            result_id: resultId,
            format_type: format,
            style: style,
            translate: enableTranslation,
            prepare_for_rag: prepareForRag,
            source_language: sourceLanguage,
            target_language: targetLanguage,
            translation_provider: translationProvider,
            translation_api_key: translationApiKey || null,
            manual_type: 'general',
            include_toc: true,
            include_metadata: true
        };
        
        // Atualizar UI
        showProgressModal();
        const statusMessage = prepareForRag ? 'Gerando manual para RAG (chunks)...' : 'Gerando manual profissional...';
        updateProgressStatus(statusMessage);
        
        fetch('/api/deep-scrape/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(result => {
            console.log('Manual generation result:', result); // Debug log
            hideProgressModal();
            
            if (result.error) {
                showError(document.getElementById("errors"), 'Erro na geração do manual: ' + result.error);
                resetButton(document.getElementById("scrape-it"), document.getElementById("select-route"));
            } else {
                // Manual gerado com sucesso
                showManualResult(result);
            }
        })
        .catch(error => {
            console.error('Erro na geração do manual:', error);
            hideProgressModal();
            
            // Log detalhado do erro para debug
            if (error.response) {
                console.error('Response status:', error.response.status);
                console.error('Response data:', error.response.data);
            }
            
            showError(document.getElementById("errors"), 'Erro de conexão: ' + error.message);
            resetButton(document.getElementById("scrape-it"), document.getElementById("select-route"));
        });
    }
    
    function showManualResult(manualData) {
        console.log('Manual data received:', manualData); // Debug log
        
        // Verificar se os dados necessários existem
        if (!manualData) {
            showError(document.getElementById("errors"), 'Dados do manual não recebidos');
            return;
        }
        
        // Valores padrão para campos que podem estar ausentes
        const title = manualData.title || 'Manual Gerado';
        const format = manualData.format || 'html';
        const style = manualData.style || 'professional';
        const downloadUrl = manualData.download_url || '#';
        
        // Verificar se structure_analysis existe e tem os campos necessários
        const structureAnalysis = manualData.structure_analysis || {};
        const qualityScore = structureAnalysis.quality_score || 0;
        const pattern = structureAnalysis.pattern || 'desconhecido';
        const recommendations = structureAnalysis.recommendations || [];
        
        // Verificar se metadata existe
        const metadata = manualData.metadata || {};
        const totalWords = metadata.total_words || 0;
        const readingTime = metadata.estimated_reading_time || 0;
        const translated = metadata.translated || false;
        const isRagFormat = manualData.format === 'markdown' && manualData.content && manualData.content.includes('+++');
        
        // Criar modal para mostrar resultado do manual
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 80%;
            max-height: 80%;
            overflow-y: auto;
            position: relative;
        `;
        
        const qualityColor = qualityScore > 70 ? '#27ae60' : 
                           qualityScore > 50 ? '#f39c12' : '#e74c3c';
        
        // Extrair result_id do manual_id para o link "Ver Dados Originais"
        let resultId = '';
        if (manualData.manual_id) {
            const parts = manualData.manual_id.split('_');
            if (parts.length >= 2) {
                resultId = parts[1];
            }
        }
        
        content.innerHTML = `
            <button onclick="this.parentElement.parentElement.remove()" style="position: absolute; top: 10px; right: 15px; background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            <h2>${isRagFormat ? '🤖 Manual RAG Gerado!' : '📖 Manual Gerado com Sucesso!'}</h2>
            <div style="margin: 20px 0;">
                <h3>${title}</h3>
                <p><strong>Formato:</strong> ${format.toUpperCase()}${isRagFormat ? ' (RAG Chunks)' : ''}</p>
                <p><strong>Estilo:</strong> ${style}</p>
                <p><strong>Qualidade da Estrutura:</strong> <span style="color: ${qualityColor}; font-weight: bold;">${qualityScore.toFixed(1)}%</span></p>
                <p><strong>Padrão Detectado:</strong> ${pattern}</p>
                <p><strong>Palavras:</strong> ${totalWords}</p>
                <p><strong>Tempo de Leitura:</strong> ${readingTime} minutos</p>
                ${translated ? '<p style="color: #27ae60;"><strong>✓ Traduzido</strong></p>' : ''}
                ${isRagFormat ? '<p style="color: #007bff;"><strong>🤖 Otimizado para RAG (dividido em chunks com separador +++)</strong></p>' : ''}
            </div>
            
            ${recommendations.length > 0 ? `
            <div style="margin: 20px 0;">
                <h4>Recomendações de Estrutura:</h4>
                <ul>
                    ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
            
            <div style="margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="${downloadUrl}" target="_blank" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    📥 Download Manual
                </a>
                ${resultId ? `
                <a href="/view/${resultId}" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    👁️ Ver Dados Originais
                </a>
                ` : ''}
                ${(format === 'html' || format === 'markdown') ? 
                    `<button onclick="window.open('${downloadUrl}', '_blank')" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                        👀 Preview
                    </button>` : ''
                }
            </div>
        `;
        
        modal.appendChild(content);
        document.body.appendChild(modal);
        
        // Reset button
        resetButton(document.getElementById("scrape-it"), document.getElementById("select-route"));
    }

}();
