"""
Content Analyzer - Análise Semântica de Conteúdo

Este módulo analisa o conteúdo scraped para identificar:
- Tipos de informação (conceitual, procedimental, referência)
- Hierarquia natural do conteúdo
- Seções, procedimentos, listas, códigos
- Elementos que devem ser agrupados ou separados
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
from enum import Enum


class ContentType(Enum):
    """Tipos de conteúdo identificados"""
    CONCEPTUAL = "conceptual"      # Explicações, definições, teoria
    PROCEDURAL = "procedural"      # Passos, instruções, tutoriais
    REFERENCE = "reference"        # Tabelas, listas, especificações
    NAVIGATION = "navigation"      # Menus, links, navegação
    INTRODUCTION = "introduction"  # Introduções, resumos
    CONCLUSION = "conclusion"      # Conclusões, resumos finais


@dataclass
class ContentSection:
    """Representa uma seção de conteúdo analisada"""
    title: str
    content: str
    content_type: ContentType
    hierarchy_level: int
    subsections: List['ContentSection']
    metadata: Dict
    original_url: str
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class ContentAnalyzer:
    """Analisador de conteúdo para geração de manuais"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Padrões para identificar tipos de conteúdo
        self.procedural_patterns = [
            r'\b(?:step|passo|etapa)\s*\d+',
            r'\b(?:primeiro|segundo|terceiro|em seguida|depois|finalmente)',
            r'\b(?:first|second|third|then|next|finally)',
            r'^\s*\d+\.\s+',  # Listas numeradas
            r'(?:como|how\s+to)',
            r'(?:tutorial|guide|guia)',
        ]
        
        self.conceptual_patterns = [
            r'\b(?:o que é|what is|definição|definition)',
            r'\b(?:conceito|concept|teoria|theory)',
            r'\b(?:entenda|understand|compreenda)',
            r'\b(?:introdução|introduction|overview)',
        ]
        
        self.reference_patterns = [
            r'<table',
            r'<ul|<ol',  # Listas
            r'\b(?:especificação|specification|referência|reference)',
            r'\b(?:parâmetros|parameters|propriedades|properties)',
        ]
    
    def analyze_scraped_data(self, scraped_data: Dict) -> Dict:
        """
        Analisa dados do deep scraping e retorna estrutura organizada para manual
        
        Args:
            scraped_data: Dados retornados pelo deep scraping
            
        Returns:
            Dict com estrutura analisada e organizada
        """
        self.logger.info("Iniciando análise de conteúdo para geração de manual")
        
        analyzed_structure = {
            'title': self._extract_main_title(scraped_data),
            'introduction': None,
            'chapters': [],
            'appendices': [],
            'metadata': {
                'total_pages': scraped_data.get('total_pages', 0),
                'domain': scraped_data.get('domain', ''),
                'analysis_date': scraped_data.get('date', ''),
                'content_types_found': set(),
                'estimated_reading_time': 0
            }
        }
        
        # Processar cada nível do scraping
        for level_data in scraped_data.get('levels', []):
            level_number = level_data.get('level', 0)
            
            for page_data in level_data.get('pages', []):
                section = self._analyze_page_content(page_data, level_number)
                if section:
                    self._categorize_and_place_section(section, analyzed_structure)
        
        # Organizar e estruturar capítulos
        analyzed_structure['chapters'] = self._organize_chapters(analyzed_structure['chapters'])
        
        # Calcular metadados finais
        self._calculate_metadata(analyzed_structure)
        
        self.logger.info(f"Análise concluída. {len(analyzed_structure['chapters'])} capítulos identificados")
        
        return analyzed_structure
    
    def _extract_main_title(self, scraped_data: Dict) -> str:
        """Extrai o título principal do manual"""
        base_url = scraped_data.get('base_url', '')
        domain = scraped_data.get('domain', '')
        
        # Tentar extrair título da primeira página
        levels = scraped_data.get('levels', [])
        if levels and levels[0].get('pages'):
            first_page = levels[0]['pages'][0]
            title = first_page.get('title', '')
            if title and title.lower() not in ['home', 'index', 'início']:
                return f"Manual: {title}"
        
        # Fallback para domínio
        return f"Manual: {domain}"
    
    def _analyze_page_content(self, page_data: Dict, level: int) -> Optional[ContentSection]:
        """Analisa o conteúdo de uma página individual"""
        title = page_data.get('title', 'Sem título')
        content = page_data.get('content', '')
        url = page_data.get('url', '')
        
        if not content.strip():
            return None
        
        # Detectar tipo de conteúdo
        content_type = self._detect_content_type(title, content)
        
        # Extrair metadados
        metadata = {
            'word_count': len(content.split()),
            'has_images': bool(re.search(r'<img|!\[.*?\]\(', content)),
            'has_code': bool(re.search(r'<code|```', content)),
            'has_lists': bool(re.search(r'<ul|<ol|^\s*[-*]\s+', content, re.MULTILINE)),
            'url': url,
            'level': level
        }
        
        # Detectar subseções
        subsections = self._extract_subsections(content)
        
        return ContentSection(
            title=title,
            content=content,
            content_type=content_type,
            hierarchy_level=level,
            subsections=subsections,
            metadata=metadata,
            original_url=url
        )
    
    def _detect_content_type(self, title: str, content: str) -> ContentType:
        """Detecta o tipo de conteúdo baseado em padrões"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Verificar padrões procedurais
        procedural_score = sum(1 for pattern in self.procedural_patterns 
                             if re.search(pattern, content_lower, re.IGNORECASE))
        
        # Verificar padrões conceituais
        conceptual_score = sum(1 for pattern in self.conceptual_patterns 
                             if re.search(pattern, content_lower, re.IGNORECASE))
        
        # Verificar padrões de referência
        reference_score = sum(1 for pattern in self.reference_patterns 
                            if re.search(pattern, content, re.IGNORECASE))
        
        # Verificar introdução/conclusão
        if any(word in title_lower for word in ['introdução', 'introduction', 'overview', 'início']):
            return ContentType.INTRODUCTION
        
        if any(word in title_lower for word in ['conclusão', 'conclusion', 'resumo', 'summary']):
            return ContentType.CONCLUSION
        
        # Determinar tipo baseado em scores
        if reference_score > max(procedural_score, conceptual_score):
            return ContentType.REFERENCE
        elif procedural_score > conceptual_score:
            return ContentType.PROCEDURAL
        else:
            return ContentType.CONCEPTUAL
    
    def _extract_subsections(self, content: str) -> List[ContentSection]:
        """Extrai subseções do conteúdo baseado em headers HTML"""
        subsections = []
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for header in headers:
                level = int(header.name[1])  # h1 -> 1, h2 -> 2, etc.
                title = header.get_text().strip()
                
                # Extrair conteúdo até o próximo header do mesmo nível ou superior
                section_content = self._extract_section_content(header)
                
                if section_content.strip():
                    subsection = ContentSection(
                        title=title,
                        content=section_content,
                        content_type=self._detect_content_type(title, section_content),
                        hierarchy_level=level,
                        subsections=[],
                        metadata={'extracted_from_header': True},
                        original_url=''
                    )
                    subsections.append(subsection)
        
        except Exception as e:
            self.logger.warning(f"Erro ao extrair subseções: {e}")
        
        return subsections
    
    def _extract_section_content(self, header_element) -> str:
        """Extrai conteúdo de uma seção até o próximo header"""
        content_parts = []
        current = header_element.next_sibling
        
        while current:
            if hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            
            if hasattr(current, 'get_text'):
                content_parts.append(current.get_text())
            elif isinstance(current, str):
                content_parts.append(current)
            
            current = current.next_sibling
        
        return ' '.join(content_parts).strip()
    
    def _categorize_and_place_section(self, section: ContentSection, structure: Dict):
        """Categoriza e posiciona uma seção na estrutura do manual"""
        
        # Introdução vai para campo específico
        if section.content_type == ContentType.INTRODUCTION and not structure['introduction']:
            structure['introduction'] = section
            structure['metadata']['content_types_found'].add(section.content_type.value)
            return
        
        # Referências vão para apêndices
        if section.content_type == ContentType.REFERENCE:
            structure['appendices'].append(section)
            structure['metadata']['content_types_found'].add(section.content_type.value)
            return
        
        # Demais conteúdos vão para capítulos
        structure['chapters'].append(section)
        structure['metadata']['content_types_found'].add(section.content_type.value)
    
    def _organize_chapters(self, chapters: List[ContentSection]) -> List[ContentSection]:
        """Organiza capítulos em ordem lógica"""
        if not chapters:
            return []
        
        # Separar por tipo de conteúdo
        conceptual_chapters = [c for c in chapters if c.content_type == ContentType.CONCEPTUAL]
        procedural_chapters = [c for c in chapters if c.content_type == ContentType.PROCEDURAL]
        other_chapters = [c for c in chapters if c.content_type not in [ContentType.CONCEPTUAL, ContentType.PROCEDURAL]]
        
        # Ordem lógica: conceitual primeiro, depois procedimental, depois outros
        organized = []
        
        # Ordenar cada grupo por nível hierárquico
        for group in [conceptual_chapters, procedural_chapters, other_chapters]:
            group.sort(key=lambda x: (x.hierarchy_level, x.title))
            organized.extend(group)
        
        return organized
    
    def _calculate_metadata(self, structure: Dict):
        """Calcula metadados finais da estrutura"""
        total_words = 0
        
        # Contar palavras em introdução
        if structure['introduction']:
            total_words += structure['introduction'].metadata.get('word_count', 0)
        
        # Contar palavras em capítulos
        for chapter in structure['chapters']:
            total_words += chapter.metadata.get('word_count', 0)
        
        # Contar palavras em apêndices
        for appendix in structure['appendices']:
            total_words += appendix.metadata.get('word_count', 0)
        
        # Estimar tempo de leitura (250 palavras por minuto)
        structure['metadata']['estimated_reading_time'] = max(1, total_words // 250)
        structure['metadata']['total_words'] = total_words
        structure['metadata']['content_types_found'] = list(structure['metadata']['content_types_found']) 