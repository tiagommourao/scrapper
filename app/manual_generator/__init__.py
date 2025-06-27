"""
Manual Generator Module

Este módulo é responsável por transformar conteúdo scraped em manuais estruturados e profissionais.
Funciona como uma extensão do sistema de deep scraping existente.
"""

from manual_generator.content_analyzer import ContentAnalyzer
from manual_generator.structure_detector import StructureDetector
from manual_generator.manual_formatter import ManualFormatter
from manual_generator.translator import Translator

__all__ = [
    'ContentAnalyzer',
    'StructureDetector', 
    'ManualFormatter',
    'Translator'
] 