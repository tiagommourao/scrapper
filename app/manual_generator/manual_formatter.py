"""
Manual Formatter - Formatação Profissional de Manuais

Este módulo é responsável por:
- Gerar estrutura profissional de manual
- Criar sumários automáticos
- Formatar conteúdo em diferentes formatos (HTML, Markdown, PDF, DOCX)
- Aplicar templates e estilos consistentes
"""

import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import tempfile
import os

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from manual_generator.content_analyzer import ContentSection, ContentType


class ManualFormatter:
    """Formatador de manuais profissionais"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Templates CSS para diferentes estilos
        self.css_templates = {
            'professional': self._get_professional_css(),
            'technical': self._get_technical_css(),
            'minimal': self._get_minimal_css()
        }
        
        # Configurações de numeração
        self.numbering_config = {
            'chapters': True,
            'sections': True,
            'figures': True,
            'tables': True
        }
    
    def format_manual(self, analyzed_structure: Dict, format_type: str = 'html', 
                     style: str = 'professional', options: Dict = None) -> Dict:
        """
        Formata manual analisado em formato específico
        
        Args:
            analyzed_structure: Estrutura analisada pelo ContentAnalyzer
            format_type: 'html', 'markdown', 'pdf', 'docx'
            style: 'professional', 'technical', 'minimal'
            options: Opções adicionais de formatação
            
        Returns:
            Dict com conteúdo formatado e metadados
        """
        if options is None:
            options = {}
        
        self.logger.info(f"Formatando manual em {format_type} com estilo {style}")
        
        # Preparar estrutura base
        formatted_manual = {
            'title': analyzed_structure['title'],
            'generated_at': datetime.now().isoformat(),
            'format': format_type,
            'style': style,
            'content': '',
            'metadata': analyzed_structure['metadata'].copy(),
            'table_of_contents': [],
            'options': options
        }
        
        # Gerar sumário
        toc = self._generate_table_of_contents(analyzed_structure)
        formatted_manual['table_of_contents'] = toc
        
        # Verificar se é para RAG - força markdown e aplica formatação específica
        if options.get('prepare_for_rag', False):
            self.logger.info("🤖 Modo RAG ativado - aplicando formatação especial")
            formatted_manual['content'] = self._format_markdown_for_rag(analyzed_structure, options)
            formatted_manual['format'] = 'markdown'  # Força markdown para RAG
            formatted_manual['rag_optimized'] = True  # Flag para identificar conteúdo RAG
        else:
            # Formatar baseado no tipo
            if format_type == 'html':
                formatted_manual['content'] = self._format_html(analyzed_structure, style, options)
            elif format_type == 'markdown':
                formatted_manual['content'] = self._format_markdown(analyzed_structure, options)
            elif format_type == 'pdf':
                formatted_manual = self._format_pdf(analyzed_structure, style, options, formatted_manual)
            elif format_type == 'docx':
                formatted_manual = self._format_docx(analyzed_structure, style, options, formatted_manual)
            else:
                raise ValueError(f"Formato não suportado: {format_type}")
        
        self.logger.info("Formatação concluída")
        return formatted_manual
    
    def _generate_table_of_contents(self, structure: Dict) -> List[Dict]:
        """Gera sumário automático"""
        toc = []
        chapter_num = 1
        
        # Introdução
        if structure.get('introduction'):
            toc.append({
                'title': 'Introdução',
                'level': 0,
                'number': '',
                'page_ref': 'introduction'
            })
        
        # Capítulos
        for chapter in structure.get('chapters', []):
            toc.append({
                'title': chapter.title,
                'level': 1,
                'number': str(chapter_num),
                'page_ref': f'chapter_{chapter_num}',
                'content_type': chapter.content_type.value
            })
            
            # Subseções
            section_num = 1
            for subsection in chapter.subsections:
                toc.append({
                    'title': subsection.title,
                    'level': 2,
                    'number': f'{chapter_num}.{section_num}',
                    'page_ref': f'section_{chapter_num}_{section_num}',
                    'content_type': subsection.content_type.value
                })
                section_num += 1
            
            chapter_num += 1
        
        # Apêndices
        appendix_letter = 'A'
        for appendix in structure.get('appendices', []):
            toc.append({
                'title': f'Apêndice {appendix_letter}: {appendix.title}',
                'level': 1,
                'number': appendix_letter,
                'page_ref': f'appendix_{appendix_letter}',
                'content_type': appendix.content_type.value
            })
            appendix_letter = chr(ord(appendix_letter) + 1)
        
        return toc
    
    def _format_html(self, structure: Dict, style: str, options: Dict) -> str:
        """Formata manual em HTML"""
        html_parts = []
        
        # Header HTML
        html_parts.append(self._get_html_header(structure['title'], style))
        
        # Página de título
        html_parts.append(self._generate_title_page_html(structure))
        
        # Sumário
        html_parts.append(self._generate_toc_html(structure))
        
        # Introdução
        if structure.get('introduction'):
            html_parts.append(self._format_section_html(structure['introduction'], 'introduction'))
        
        # Capítulos
        for i, chapter in enumerate(structure.get('chapters', []), 1):
            html_parts.append(self._format_chapter_html(chapter, i))
        
        # Apêndices
        for i, appendix in enumerate(structure.get('appendices', [])):
            appendix_letter = chr(ord('A') + i)
            html_parts.append(self._format_appendix_html(appendix, appendix_letter))
        
        # Footer HTML
        html_parts.append(self._get_html_footer())
        
        return '\n'.join(html_parts)
    
    def _format_markdown(self, structure: Dict, options: Dict) -> str:
        """Formata manual em Markdown"""
        md_parts = []
        
        # Título principal
        md_parts.append(f"# {structure['title']}\n")
        md_parts.append(f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")
        md_parts.append(f"*Domínio: {structure['metadata'].get('domain', 'N/A')}*\n")
        md_parts.append(f"*Total de páginas: {structure['metadata'].get('total_pages', 0)}*\n")
        md_parts.append(f"*Tempo estimado de leitura: {structure['metadata'].get('estimated_reading_time', 0)} minutos*\n\n")
        
        # Sumário
        md_parts.append("## Sumário\n")
        for item in self._generate_table_of_contents(structure):
            indent = "  " * item['level']
            number = f"{item['number']}. " if item['number'] else ""
            md_parts.append(f"{indent}- {number}{item['title']}")
        md_parts.append("\n")
        
        # Introdução
        if structure.get('introduction'):
            md_parts.append("## Introdução\n")
            md_parts.append(self._clean_content_for_markdown(structure['introduction'].content))
            md_parts.append("\n\n")
        
        # Capítulos
        for i, chapter in enumerate(structure.get('chapters', []), 1):
            md_parts.append(f"## {i}. {chapter.title}\n")
            md_parts.append(self._clean_content_for_markdown(chapter.content))
            
            # Subseções
            for j, subsection in enumerate(chapter.subsections, 1):
                md_parts.append(f"\n### {i}.{j} {subsection.title}\n")
                md_parts.append(self._clean_content_for_markdown(subsection.content))
            
            md_parts.append("\n\n")
        
        # Apêndices
        for i, appendix in enumerate(structure.get('appendices', [])):
            appendix_letter = chr(ord('A') + i)
            md_parts.append(f"## Apêndice {appendix_letter}: {appendix.title}\n")
            md_parts.append(self._clean_content_for_markdown(appendix.content))
            md_parts.append("\n\n")
        
        return '\n'.join(md_parts)
    
    def _format_markdown_for_rag(self, structure: Dict, options: Dict) -> str:
        """
        Formata manual em Markdown otimizado para RAG
        - Remove imagens e referências visuais
        - Não inclui sumário
        - Divide em chunks de 1500-2000 caracteres por seção
        - Mantém apenas texto puro
        - Usa +++ como separador de chunks
        """
        self.logger.info("📋 Iniciando formatação RAG - removendo elementos visuais e criando chunks")
        
        chunks = []
        max_chunk_size = 1800  # Tamanho ideal para GPT (1500-2000 chars)
        
        # Título principal (sem metadados visuais)
        title_chunk = f"# {structure['title']}\n\nDocumento otimizado para RAG (Retrieval-Augmented Generation)"
        chunks.append(title_chunk)
        
        # Introdução (se existir)
        if structure.get('introduction'):
            intro_content = self._clean_content_for_rag(structure['introduction'].content)
            if intro_content.strip():
                intro_chunks = self._split_content_into_chunks(
                    f"## Introdução\n\n{intro_content}", 
                    max_chunk_size,
                    "Introdução"
                )
                chunks.extend(intro_chunks)
        
        # Capítulos
        for i, chapter in enumerate(structure.get('chapters', []), 1):
            chapter_content = self._clean_content_for_rag(chapter.content)
            if chapter_content.strip():
                chapter_chunks = self._split_content_into_chunks(
                    f"## {chapter.title}\n\n{chapter_content}",
                    max_chunk_size,
                    f"Capítulo {i}: {chapter.title}"
                )
                chunks.extend(chapter_chunks)
            
            # Subseções
            for j, subsection in enumerate(chapter.subsections, 1):
                subsection_content = self._clean_content_for_rag(subsection.content)
                if subsection_content.strip():
                    subsection_chunks = self._split_content_into_chunks(
                        f"### {subsection.title}\n\n{subsection_content}",
                        max_chunk_size,
                        f"Seção {i}.{j}: {subsection.title}"
                    )
                    chunks.extend(subsection_chunks)
        
        # Apêndices
        for i, appendix in enumerate(structure.get('appendices', [])):
            appendix_content = self._clean_content_for_rag(appendix.content)
            if appendix_content.strip():
                appendix_chunks = self._split_content_into_chunks(
                    f"## {appendix.title}\n\n{appendix_content}",
                    max_chunk_size,
                    f"Apêndice {chr(ord('A') + i)}: {appendix.title}"
                )
                chunks.extend(appendix_chunks)
        
        self.logger.info(f"✅ RAG: Criados {len(chunks)} chunks otimizados para retrieval")
        
        # Juntar chunks com separador +++
        return '\n\n+++\n\n'.join(chunks)
    
    def _split_content_into_chunks(self, content: str, max_size: int, section_name: str) -> List[str]:
        """
        Divide conteúdo em chunks inteligentes respeitando limites de tamanho
        Prioriza quebras por parágrafos e frases
        """
        if len(content) <= max_size:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Dividir por parágrafos primeiro
        paragraphs = content.split('\n\n')
        
        for para in paragraphs:
            # Se o parágrafo é muito grande, dividir por frases
            if len(para) > max_size:
                sentences = para.split('. ')
                for sentence in sentences:
                    test_chunk = current_chunk + '\n\n' + sentence if current_chunk else sentence
                    
                    if len(test_chunk) > max_size and current_chunk:
                        # Finalizar chunk atual
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk = test_chunk
            else:
                test_chunk = current_chunk + '\n\n' + para if current_chunk else para
                
                if len(test_chunk) > max_size and current_chunk:
                    # Finalizar chunk atual
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk = test_chunk
        
        # Adicionar último chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        self.logger.info(f"📄 {section_name}: {len(content)} chars → {len(chunks)} chunks")
        return chunks
    
    def _clean_content_for_rag(self, content: str) -> str:
        """
        Limpa conteúdo para RAG removendo elementos visuais e formatação desnecessária
        - Remove todas as imagens e referências visuais
        - Remove HTML e formatação complexa
        - Mantém apenas texto puro e estrutura básica
        """
        if not content:
            return ""
        
        import re
        
        # Remover tags HTML se existirem
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remover TODAS as referências a imagens e mídia
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # Markdown images
        content = re.sub(r'\[.*?\]\(.*?\.(jpg|jpeg|png|gif|bmp|svg|webp|mp4|avi|mov|pdf).*?\)', '', content, flags=re.IGNORECASE)  # Media links
        content = re.sub(r'<img[^>]*>', '', content, flags=re.IGNORECASE)  # HTML images
        content = re.sub(r'<video[^>]*>.*?</video>', '', content, flags=re.IGNORECASE | re.DOTALL)  # HTML videos
        content = re.sub(r'<audio[^>]*>.*?</audio>', '', content, flags=re.IGNORECASE | re.DOTALL)  # HTML audio
        
        # Remover elementos visuais e decorativos
        content = re.sub(r'---+', '', content)  # Separadores visuais
        content = re.sub(r'===+', '', content)  # Separadores visuais
        content = re.sub(r'\*\*\*+', '', content)  # Separadores visuais
        content = re.sub(r'_{3,}', '', content)  # Underlines decorativos
        
        # Remover formatação de código complexa (manter apenas texto)
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)  # Code blocks
        content = re.sub(r'`[^`]+`', '', content)  # Inline code
        
        # Remover tabelas complexas (manter apenas conteúdo textual)
        content = re.sub(r'\|[^\n]*\|', '', content)  # Table rows
        content = re.sub(r'^\s*[-|:]+\s*$', '', content, flags=re.MULTILINE)  # Table separators
        
        # Limpar formatação markdown excessiva
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Italic
        content = re.sub(r'__(.*?)__', r'\1', content)  # Bold
        content = re.sub(r'_(.*?)_', r'\1', content)  # Italic
        
        # Remover links mas manter texto
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # [text](url) -> text
        
        # Limpar quebras de linha e espaçamento
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Múltiplas quebras
        content = re.sub(r'[ \t]+', ' ', content)  # Espaços em excesso
        content = re.sub(r'^\s+|\s+$', '', content, flags=re.MULTILINE)  # Espaços nas bordas das linhas
        
        # Remover linhas vazias no início e fim
        content = content.strip()
        
        return content
    
    def _format_pdf(self, structure: Dict, style: str, options: Dict, formatted_manual: Dict) -> Dict:
        """Formata manual em PDF usando WeasyPrint"""
        # Verificar WeasyPrint diretamente
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise RuntimeError("WeasyPrint não está disponível para geração de PDF")
        
        # Gerar HTML primeiro
        html_content = self._format_html(structure, style, options)
        
        # Criar arquivo temporário para PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            try:
                # Gerar PDF
                html_doc = HTML(string=html_content)
                css_style = CSS(string=self.css_templates[style])
                html_doc.write_pdf(tmp_file.name, stylesheets=[css_style])
                
                # Ler arquivo gerado
                with open(tmp_file.name, 'rb') as pdf_file:
                    formatted_manual['content'] = pdf_file.read()
                
                formatted_manual['file_path'] = tmp_file.name
                
            except Exception as e:
                self.logger.error(f"Erro ao gerar PDF: {e}")
                raise
        
        return formatted_manual
    
    def _format_docx(self, structure: Dict, style: str, options: Dict, formatted_manual: Dict) -> Dict:
        """Formata manual em DOCX usando Pandoc"""
        # Gerar Markdown primeiro
        markdown_content = self._format_markdown(structure, options)
        
        # Criar arquivo temporário para DOCX
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            try:
                # Usar Pandoc para converter MD para DOCX
                import subprocess
                
                # Criar arquivo MD temporário
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as md_file:
                    md_file.write(markdown_content)
                    md_file.flush()
                    
                    # Executar Pandoc
                    cmd = [
                        'pandoc',
                        md_file.name,
                        '-o', tmp_file.name,
                        '--from', 'markdown',
                        '--to', 'docx',
                        '--standalone',
                        '--toc'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        raise RuntimeError(f"Erro no Pandoc: {result.stderr}")
                    
                    # Limpar arquivo MD temporário
                    os.unlink(md_file.name)
                
                # Ler arquivo gerado
                with open(tmp_file.name, 'rb') as docx_file:
                    formatted_manual['content'] = docx_file.read()
                
                formatted_manual['file_path'] = tmp_file.name
                
            except Exception as e:
                self.logger.error(f"Erro ao gerar DOCX: {e}")
                raise
        
        return formatted_manual
    
    def _get_html_header(self, title: str, style: str) -> str:
        """Gera header HTML com CSS"""
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self.css_templates[style]}
    </style>
</head>
<body>"""
    
    def _get_html_footer(self) -> str:
        """Gera footer HTML"""
        return """</body>
</html>"""
    
    def _generate_title_page_html(self, structure: Dict) -> str:
        """Gera página de título"""
        metadata = structure['metadata']
        return f"""
<div class="title-page">
    <h1 class="main-title">{structure['title']}</h1>
    <div class="title-metadata">
        <p><strong>Domínio:</strong> {metadata.get('domain', 'N/A')}</p>
        <p><strong>Total de páginas analisadas:</strong> {metadata.get('total_pages', 0)}</p>
        <p><strong>Tempo estimado de leitura:</strong> {metadata.get('estimated_reading_time', 0)} minutos</p>
        <p><strong>Tipos de conteúdo encontrados:</strong> {', '.join(metadata.get('content_types_found', []))}</p>
        <p><strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
    </div>
</div>
<div class="page-break"></div>
"""
    
    def _generate_toc_html(self, structure: Dict) -> str:
        """Gera sumário em HTML"""
        toc_items = []
        
        for item in self._generate_table_of_contents(structure):
            indent_class = f"toc-level-{item['level']}"
            number = f"<span class='toc-number'>{item['number']}</span>" if item['number'] else ""
            
            toc_items.append(
                f'<div class="toc-item {indent_class}">'
                f'{number}<span class="toc-title">{item["title"]}</span>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-page">#{item["page_ref"]}</span>'
                f'</div>'
            )
        
        return f"""
<div class="table-of-contents">
    <h2>Sumário</h2>
    {''.join(toc_items)}
</div>
<div class="page-break"></div>
"""
    
    def _format_section_html(self, section: ContentSection, section_id: str) -> str:
        """Formata seção individual em HTML"""
        content_type_class = f"content-type-{section.content_type.value}"
        
        return f"""
<div class="section {content_type_class}" id="{section_id}">
    <h2>{section.title}</h2>
    <div class="section-content">
        {self._clean_content_for_html(section.content)}
    </div>
</div>
"""
    
    def _format_chapter_html(self, chapter: ContentSection, chapter_num: int) -> str:
        """Formata capítulo em HTML"""
        content_type_class = f"content-type-{chapter.content_type.value}"
        
        html = f"""
<div class="chapter {content_type_class}" id="chapter_{chapter_num}">
    <h1><span class="chapter-number">{chapter_num}.</span> {chapter.title}</h1>
    <div class="chapter-content">
        {self._clean_content_for_html(chapter.content)}
    </div>
"""
        
        # Adicionar subseções
        for i, subsection in enumerate(chapter.subsections, 1):
            subsection_id = f"section_{chapter_num}_{i}"
            subsection_class = f"content-type-{subsection.content_type.value}"
            
            html += f"""
    <div class="subsection {subsection_class}" id="{subsection_id}">
        <h2><span class="section-number">{chapter_num}.{i}</span> {subsection.title}</h2>
        <div class="subsection-content">
            {self._clean_content_for_html(subsection.content)}
        </div>
    </div>
"""
        
        html += "</div>"
        return html
    
    def _format_appendix_html(self, appendix: ContentSection, appendix_letter: str) -> str:
        """Formata apêndice em HTML"""
        content_type_class = f"content-type-{appendix.content_type.value}"
        
        return f"""
<div class="appendix {content_type_class}" id="appendix_{appendix_letter}">
    <h1><span class="appendix-letter">Apêndice {appendix_letter}:</span> {appendix.title}</h1>
    <div class="appendix-content">
        {self._clean_content_for_html(appendix.content)}
    </div>
</div>
"""
    
    def _clean_content_for_html(self, content: str) -> str:
        """Limpa e formata conteúdo para HTML"""
        # Remover scripts e estilos
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Limpar atributos desnecessários
        content = re.sub(r'<(\w+)[^>]*class="[^"]*"[^>]*>', r'<\1>', content)
        content = re.sub(r'<(\w+)[^>]*style="[^"]*"[^>]*>', r'<\1>', content)
        
        return content
    
    def _clean_content_for_markdown(self, content: str) -> str:
        """Converte HTML para Markdown limpo"""
        from internal.util import html_to_markdown
        return html_to_markdown(content)
    
    def _get_professional_css(self) -> str:
        """CSS para estilo profissional"""
        return """
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }
        
        .title-page {
            text-align: center;
            padding: 100px 0;
            border-bottom: 3px solid #2c3e50;
        }
        
        .main-title {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 30px;
            font-weight: bold;
        }
        
        .title-metadata {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }
        
        .table-of-contents {
            padding: 20px 0;
        }
        
        .toc-item {
            display: flex;
            align-items: center;
            margin: 8px 0;
            padding: 4px 0;
        }
        
        .toc-level-0 { margin-left: 0; font-weight: bold; }
        .toc-level-1 { margin-left: 20px; }
        .toc-level-2 { margin-left: 40px; font-size: 0.9em; }
        
        .toc-number {
            min-width: 30px;
            font-weight: bold;
        }
        
        .toc-dots {
            flex: 1;
            border-bottom: 1px dotted #ccc;
            margin: 0 10px;
        }
        
        .chapter {
            margin: 40px 0;
            page-break-before: always;
        }
        
        .chapter h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        
        .chapter-number, .section-number, .appendix-letter {
            color: #3498db;
        }
        
        .subsection {
            margin: 30px 0;
        }
        
        .content-type-procedural {
            border-left: 4px solid #27ae60;
            padding-left: 15px;
        }
        
        .content-type-conceptual {
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        
        .content-type-reference {
            border-left: 4px solid #f39c12;
            padding-left: 15px;
        }
        
        .page-break {
            page-break-after: always;
        }
        
        @media print {
            body { margin: 0; }
            .page-break { page-break-after: always; }
        }
        """
    
    def _get_technical_css(self) -> str:
        """CSS para estilo técnico"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.5;
            color: #2c3e50;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .title-page {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 80px 20px;
            border-radius: 10px;
        }
        
        .main-title {
            font-size: 2.8em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .chapter, .section, .appendix {
            background: white;
            margin: 20px 0;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chapter h1 {
            background: #34495e;
            color: white;
            margin: -25px -25px 20px -25px;
            padding: 15px 25px;
            border-radius: 8px 8px 0 0;
        }
        
        code, pre {
            background: #f1f2f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        
        pre {
            padding: 15px;
            border-left: 4px solid #3498db;
        }
        """
    
    def _get_minimal_css(self) -> str:
        """CSS para estilo minimalista"""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .title-page {
            text-align: left;
            padding: 40px 0;
            border-bottom: 1px solid #eee;
        }
        
        .main-title {
            font-size: 2.2em;
            font-weight: 300;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        h1, h2, h3 {
            font-weight: 400;
            color: #2c3e50;
        }
        
        .chapter {
            margin: 60px 0;
        }
        
        .chapter h1 {
            font-size: 1.8em;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .subsection {
            margin: 40px 0;
        }
        
        .table-of-contents {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 6px;
            margin: 40px 0;
        }
        """ 