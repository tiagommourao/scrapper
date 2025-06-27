"""
Translator - Tradução Contextual para Manuais

Este módulo é responsável por:
- Traduzir conteúdo de manuais mantendo contexto técnico
- Preservar terminologia consistente
- Usar múltiplas APIs de tradução
- Manter glossários de termos técnicos
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class TranslationProvider(Enum):
    """Provedores de tradução disponíveis"""
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPL = "deepl"
    LIBRE = "libre"


@dataclass
class TranslationConfig:
    """Configuração de tradução"""
    provider: TranslationProvider
    source_language: str
    target_language: str
    preserve_formatting: bool = True
    use_glossary: bool = True
    technical_context: str = ""
    api_key: Optional[str] = None


@dataclass
class GlossaryEntry:
    """Entrada do glossário técnico"""
    term: str
    translation: str
    context: str
    category: str


class Translator:
    """Tradutor contextual para manuais"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Glossário técnico padrão
        self.default_glossary = self._load_default_glossary()
        
        # Padrões para preservar durante tradução
        self.preserve_patterns = [
            r'<[^>]+>',  # Tags HTML
            r'```[^`]*```',  # Blocos de código
            r'`[^`]+`',  # Código inline
            r'\[.*?\]\(.*?\)',  # Links Markdown
            r'!\[.*?\]\(.*?\)',  # Imagens Markdown
            r'https?://[^\s]+',  # URLs
            r'\b\w+\.\w+\b',  # Domínios/arquivos
        ]
    
    def translate_manual_structure(self, structure: Dict, config: TranslationConfig) -> Dict:
        """
        Traduz estrutura completa de manual
        
        Args:
            structure: Estrutura analisada do manual
            config: Configuração de tradução
            
        Returns:
            Estrutura traduzida
        """
        self.logger.info(f"Iniciando tradução de {config.source_language} para {config.target_language}")
        
        translated_structure = structure.copy()
        
        # Traduzir título principal
        translated_structure['title'] = self._translate_text(
            structure['title'], config
        )
        
        # Traduzir introdução
        if structure.get('introduction'):
            translated_structure['introduction'] = self._translate_section(
                structure['introduction'], config
            )
        
        # Traduzir capítulos
        translated_chapters = []
        for chapter in structure.get('chapters', []):
            translated_chapter = self._translate_section(chapter, config)
            translated_chapters.append(translated_chapter)
        
        translated_structure['chapters'] = translated_chapters
        
        # Traduzir apêndices
        translated_appendices = []
        for appendix in structure.get('appendices', []):
            translated_appendix = self._translate_section(appendix, config)
            translated_appendices.append(translated_appendix)
        
        translated_structure['appendices'] = translated_appendices
        
        # Atualizar metadados
        translated_structure['metadata']['translation'] = {
            'source_language': config.source_language,
            'target_language': config.target_language,
            'provider': config.provider.value,
            'translated_at': self._get_current_timestamp()
        }
        
        self.logger.info("Tradução concluída")
        return translated_structure
    
    def _translate_section(self, section, config: TranslationConfig):
        """Traduz uma seção individual"""
        from .content_analyzer import ContentSection
        
        # Criar cópia da seção
        translated_section = ContentSection(
            title=self._translate_text(section.title, config),
            content=self._translate_content(section.content, config),
            content_type=section.content_type,
            hierarchy_level=section.hierarchy_level,
            subsections=[],
            metadata=section.metadata.copy(),
            original_url=section.original_url
        )
        
        # Traduzir subseções
        for subsection in section.subsections:
            translated_subsection = self._translate_section(subsection, config)
            translated_section.subsections.append(translated_subsection)
        
        return translated_section
    
    def _translate_content(self, content: str, config: TranslationConfig) -> str:
        """Traduz conteúdo preservando formatação"""
        if not content.strip():
            return content
        
        # Extrair elementos a preservar
        preserved_elements = self._extract_preserved_elements(content)
        
        # Substituir elementos por placeholders
        content_with_placeholders = self._replace_with_placeholders(content, preserved_elements)
        
        # Aplicar glossário antes da tradução
        if config.use_glossary:
            content_with_placeholders = self._apply_glossary(content_with_placeholders, config)
        
        # Traduzir texto
        translated_content = self._translate_text(content_with_placeholders, config)
        
        # Restaurar elementos preservados
        final_content = self._restore_preserved_elements(translated_content, preserved_elements)
        
        return final_content
    
    def _translate_text(self, text: str, config: TranslationConfig) -> str:
        """Traduz texto usando provedor configurado"""
        if not text.strip():
            return text
        
        try:
            if config.provider == TranslationProvider.OPENAI:
                return self._translate_with_openai(text, config)
            elif config.provider == TranslationProvider.GOOGLE:
                return self._translate_with_google(text, config)
            elif config.provider == TranslationProvider.DEEPL:
                return self._translate_with_deepl(text, config)
            elif config.provider == TranslationProvider.LIBRE:
                return self._translate_with_libre(text, config)
            else:
                raise ValueError(f"Provedor não suportado: {config.provider}")
        
        except Exception as e:
            self.logger.error(f"Erro na tradução: {e}")
            return f"[ERRO DE TRADUÇÃO: {text}]"
    
    def _translate_with_openai(self, text: str, config: TranslationConfig) -> str:
        """Traduz usando OpenAI GPT"""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI não está disponível")
        
        if not config.api_key:
            raise ValueError("API key do OpenAI é obrigatória")
        
        # Configurar cliente OpenAI
        client = openai.OpenAI(api_key=config.api_key)
        
        # Preparar prompt contextual
        prompt = self._prepare_openai_prompt(text, config)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um tradutor especializado em documentação técnica. "
                                 "Mantenha a precisão técnica e preserve a formatação."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            self.logger.error(f"Erro na tradução OpenAI: {e}")
            raise
    
    def _translate_with_google(self, text: str, config: TranslationConfig) -> str:
        """Traduz usando Google Translate API"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("Requests não está disponível")
        
        if not config.api_key:
            raise ValueError("API key do Google é obrigatória")
        
        url = "https://translation.googleapis.com/language/translate/v2"
        
        params = {
            'key': config.api_key,
            'q': text,
            'source': config.source_language,
            'target': config.target_language,
            'format': 'text'
        }
        
        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
            
            result = response.json()
            return result['data']['translations'][0]['translatedText']
        
        except Exception as e:
            self.logger.error(f"Erro na tradução Google: {e}")
            raise
    
    def _translate_with_deepl(self, text: str, config: TranslationConfig) -> str:
        """Traduz usando DeepL API"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("Requests não está disponível")
        
        if not config.api_key:
            raise ValueError("API key do DeepL é obrigatória")
        
        url = "https://api-free.deepl.com/v2/translate"
        
        data = {
            'auth_key': config.api_key,
            'text': text,
            'source_lang': config.source_language.upper(),
            'target_lang': config.target_language.upper(),
            'preserve_formatting': '1' if config.preserve_formatting else '0'
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            return result['translations'][0]['text']
        
        except Exception as e:
            self.logger.error(f"Erro na tradução DeepL: {e}")
            raise
    
    def _translate_with_libre(self, text: str, config: TranslationConfig) -> str:
        """Traduz usando LibreTranslate (gratuito)"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("Requests não está disponível")
        
        url = "https://libretranslate.de/translate"
        
        data = {
            'q': text,
            'source': config.source_language,
            'target': config.target_language,
            'format': 'text'
        }
        
        if config.api_key:
            data['api_key'] = config.api_key
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            return result['translatedText']
        
        except Exception as e:
            self.logger.error(f"Erro na tradução LibreTranslate: {e}")
            raise
    
    def _prepare_openai_prompt(self, text: str, config: TranslationConfig) -> str:
        """Prepara prompt contextual para OpenAI"""
        context_info = ""
        if config.technical_context:
            context_info = f"\n\nContexto técnico: {config.technical_context}"
        
        return f"""Traduza o seguinte texto de {config.source_language} para {config.target_language}.

Este texto faz parte de um manual técnico. Por favor:
1. Mantenha a precisão técnica
2. Preserve toda formatação (HTML, Markdown, etc.)
3. Mantenha terminologia técnica consistente
4. Use linguagem clara e profissional{context_info}

Texto para traduzir:
{text}

Tradução:"""
    
    def _extract_preserved_elements(self, content: str) -> List[Tuple[str, str]]:
        """Extrai elementos que devem ser preservados"""
        preserved = []
        
        for pattern in self.preserve_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                preserved.append((match.group(), f"__PRESERVE_{len(preserved)}__"))
        
        return preserved
    
    def _replace_with_placeholders(self, content: str, preserved_elements: List[Tuple[str, str]]) -> str:
        """Substitui elementos preservados por placeholders"""
        for original, placeholder in preserved_elements:
            content = content.replace(original, placeholder)
        
        return content
    
    def _restore_preserved_elements(self, content: str, preserved_elements: List[Tuple[str, str]]) -> str:
        """Restaura elementos preservados"""
        for original, placeholder in preserved_elements:
            content = content.replace(placeholder, original)
        
        return content
    
    def _apply_glossary(self, content: str, config: TranslationConfig) -> str:
        """Aplica glossário técnico ao conteúdo"""
        # Por enquanto, usar glossário padrão
        # Em implementação futura, permitir glossários customizados
        
        for entry in self.default_glossary:
            if config.source_language == 'en' and config.target_language == 'pt':
                pattern = r'\b' + re.escape(entry.term) + r'\b'
                content = re.sub(pattern, entry.translation, content, flags=re.IGNORECASE)
        
        return content
    
    def _load_default_glossary(self) -> List[GlossaryEntry]:
        """Carrega glossário técnico padrão"""
        # Glossário básico inglês -> português
        return [
            GlossaryEntry("API", "API", "Interface de programação", "tecnologia"),
            GlossaryEntry("endpoint", "endpoint", "Ponto de acesso da API", "tecnologia"),
            GlossaryEntry("database", "banco de dados", "Armazenamento de dados", "tecnologia"),
            GlossaryEntry("server", "servidor", "Computador que fornece serviços", "tecnologia"),
            GlossaryEntry("client", "cliente", "Aplicação que consome serviços", "tecnologia"),
            GlossaryEntry("authentication", "autenticação", "Verificação de identidade", "segurança"),
            GlossaryEntry("authorization", "autorização", "Controle de acesso", "segurança"),
            GlossaryEntry("configuration", "configuração", "Definições do sistema", "geral"),
            GlossaryEntry("deployment", "implantação", "Publicação do sistema", "devops"),
            GlossaryEntry("framework", "framework", "Estrutura de desenvolvimento", "tecnologia"),
        ]
    
    def _get_current_timestamp(self) -> str:
        """Retorna timestamp atual"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def add_glossary_entry(self, term: str, translation: str, context: str = "", category: str = "custom"):
        """Adiciona entrada ao glossário"""
        entry = GlossaryEntry(term, translation, context, category)
        self.default_glossary.append(entry)
        
        self.logger.info(f"Adicionada entrada ao glossário: {term} -> {translation}")
    
    def get_supported_languages(self) -> Dict[str, List[str]]:
        """Retorna idiomas suportados por provedor"""
        return {
            'openai': ['en', 'pt', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh'],
            'google': ['en', 'pt', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh', 'ru', 'ar'],
            'deepl': ['en', 'pt', 'es', 'fr', 'de', 'it', 'ja', 'zh'],
            'libre': ['en', 'pt', 'es', 'fr', 'de', 'it', 'ja', 'zh', 'ru', 'ar']
        } 