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
                            window.location.href = "/view/" + statusData.result_id;
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
            showError(errors, 'Erro de conexão ao iniciar scraping.');
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

}();
