"""
Structure Detector - Detecção de Estrutura Hierárquica

Este módulo é responsável por:
- Detectar hierarquia natural do conteúdo
- Organizar informações em estrutura lógica
- Identificar dependências entre seções
- Sugerir reorganização otimizada para manuais
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

from manual_generator.content_analyzer import ContentSection, ContentType


class StructurePattern(Enum):
    """Padrões de estrutura identificados"""
    SEQUENTIAL = "sequential"      # Sequência linear (tutoriais)
    HIERARCHICAL = "hierarchical"  # Estrutura em árvore (documentação)
    REFERENCE = "reference"        # Estrutura de referência (APIs)
    MIXED = "mixed"               # Estrutura mista


@dataclass
class StructureNode:
    """Nó da estrutura hierárquica"""
    section: ContentSection
    parent: Optional['StructureNode']
    children: List['StructureNode']
    dependencies: List['StructureNode']
    importance_score: float
    suggested_order: int
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class StructureAnalysis:
    """Resultado da análise de estrutura"""
    pattern: StructurePattern
    root_nodes: List[StructureNode]
    suggested_reorganization: List[ContentSection]
    quality_score: float
    recommendations: List[str]


class StructureDetector:
    """Detector de estrutura hierárquica"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Palavras que indicam dependência/sequência
        self.dependency_indicators = [
            'antes', 'depois', 'primeiro', 'segundo', 'terceiro',
            'before', 'after', 'first', 'second', 'third',
            'prerequisite', 'prerequisito', 'requer', 'requires',
            'depende', 'depends', 'baseado', 'based'
        ]
        
        # Palavras que indicam introdução
        self.introduction_indicators = [
            'introdução', 'introduction', 'overview', 'visão geral',
            'começando', 'getting started', 'início', 'start'
        ]
        
        # Palavras que indicam conclusão
        self.conclusion_indicators = [
            'conclusão', 'conclusion', 'resumo', 'summary',
            'fim', 'end', 'finalização', 'finalization'
        ]
    
    def analyze_structure(self, analyzed_content: Dict) -> StructureAnalysis:
        """
        Analisa estrutura do conteúdo e sugere reorganização
        
        Args:
            analyzed_content: Conteúdo analisado pelo ContentAnalyzer
            
        Returns:
            Análise da estrutura com sugestões
        """
        self.logger.info("Iniciando análise de estrutura")
        
        # Criar nós da estrutura
        nodes = self._create_structure_nodes(analyzed_content)
        
        # Detectar padrão de estrutura
        pattern = self._detect_structure_pattern(nodes)
        
        # Analisar dependências
        self._analyze_dependencies(nodes)
        
        # Calcular scores de importância
        self._calculate_importance_scores(nodes)
        
        # Organizar hierarquia
        root_nodes = self._organize_hierarchy(nodes)
        
        # Sugerir reorganização
        reorganized_content = self._suggest_reorganization(root_nodes, pattern)
        
        # Calcular qualidade da estrutura
        quality_score = self._calculate_quality_score(root_nodes, pattern)
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(root_nodes, pattern, quality_score)
        
        analysis = StructureAnalysis(
            pattern=pattern,
            root_nodes=root_nodes,
            suggested_reorganization=reorganized_content,
            quality_score=quality_score,
            recommendations=recommendations
        )
        
        self.logger.info(f"Análise concluída. Padrão: {pattern.value}, Qualidade: {quality_score:.2f}")
        
        return analysis
    
    def _create_structure_nodes(self, analyzed_content: Dict) -> List[StructureNode]:
        """Cria nós da estrutura a partir do conteúdo analisado"""
        nodes = []
        
        # Processar introdução
        if analyzed_content.get('introduction'):
            node = StructureNode(
                section=analyzed_content['introduction'],
                parent=None,
                children=[],
                dependencies=[],
                importance_score=0.0,
                suggested_order=0
            )
            nodes.append(node)
        
        # Processar capítulos
        for chapter in analyzed_content.get('chapters', []):
            node = StructureNode(
                section=chapter,
                parent=None,
                children=[],
                dependencies=[],
                importance_score=0.0,
                suggested_order=0
            )
            nodes.append(node)
            
            # Processar subseções
            for subsection in chapter.subsections:
                sub_node = StructureNode(
                    section=subsection,
                    parent=node,
                    children=[],
                    dependencies=[],
                    importance_score=0.0,
                    suggested_order=0
                )
                node.children.append(sub_node)
                nodes.append(sub_node)
        
        # Processar apêndices
        for appendix in analyzed_content.get('appendices', []):
            node = StructureNode(
                section=appendix,
                parent=None,
                children=[],
                dependencies=[],
                importance_score=0.0,
                suggested_order=0
            )
            nodes.append(node)
        
        return nodes
    
    def _detect_structure_pattern(self, nodes: List[StructureNode]) -> StructurePattern:
        """Detecta o padrão predominante da estrutura"""
        content_types = [node.section.content_type for node in nodes]
        
        # Contar tipos de conteúdo
        type_counts = defaultdict(int)
        for content_type in content_types:
            type_counts[content_type] += 1
        
        total_nodes = len(nodes)
        procedural_ratio = type_counts[ContentType.PROCEDURAL] / total_nodes
        conceptual_ratio = type_counts[ContentType.CONCEPTUAL] / total_nodes
        reference_ratio = type_counts[ContentType.REFERENCE] / total_nodes
        
        # Determinar padrão baseado nas proporções
        if procedural_ratio > 0.6:
            return StructurePattern.SEQUENTIAL
        elif reference_ratio > 0.5:
            return StructurePattern.REFERENCE
        elif conceptual_ratio > 0.5:
            return StructurePattern.HIERARCHICAL
        else:
            return StructurePattern.MIXED
    
    def _analyze_dependencies(self, nodes: List[StructureNode]):
        """Analisa dependências entre nós"""
        for node in nodes:
            content_lower = node.section.content.lower()
            title_lower = node.section.title.lower()
            
            # Procurar indicadores de dependência
            for indicator in self.dependency_indicators:
                if indicator in content_lower or indicator in title_lower:
                    # Encontrar nós relacionados
                    related_nodes = self._find_related_nodes(node, nodes, indicator)
                    node.dependencies.extend(related_nodes)
    
    def _find_related_nodes(self, current_node: StructureNode, all_nodes: List[StructureNode], 
                           indicator: str) -> List[StructureNode]:
        """Encontra nós relacionados baseado em indicadores"""
        related = []
        
        # Lógica simples: se menciona "primeiro", procurar por "segundo", etc.
        sequence_map = {
            'primeiro': ['segundo', 'third'],
            'first': ['second', 'third'],
            'segundo': ['terceiro', 'primeiro'],
            'second': ['third', 'first']
        }
        
        if indicator in sequence_map:
            for target in sequence_map[indicator]:
                for node in all_nodes:
                    if node != current_node and target in node.section.title.lower():
                        related.append(node)
        
        return related
    
    def _calculate_importance_scores(self, nodes: List[StructureNode]):
        """Calcula scores de importância para cada nó"""
        for node in nodes:
            score = 0.0
            
            # Score baseado no tipo de conteúdo
            if node.section.content_type == ContentType.INTRODUCTION:
                score += 10.0
            elif node.section.content_type == ContentType.CONCEPTUAL:
                score += 8.0
            elif node.section.content_type == ContentType.PROCEDURAL:
                score += 7.0
            elif node.section.content_type == ContentType.REFERENCE:
                score += 5.0
            
            # Score baseado na hierarquia
            score += (5 - node.section.hierarchy_level) * 2
            
            # Score baseado no tamanho do conteúdo
            word_count = node.section.metadata.get('word_count', 0)
            if word_count > 500:
                score += 3.0
            elif word_count > 200:
                score += 2.0
            elif word_count > 50:
                score += 1.0
            
            # Score baseado em indicadores especiais
            title_lower = node.section.title.lower()
            if any(indicator in title_lower for indicator in self.introduction_indicators):
                score += 5.0
            
            # Penalizar conclusões (devem vir por último)
            if any(indicator in title_lower for indicator in self.conclusion_indicators):
                score -= 3.0
            
            node.importance_score = score
    
    def _organize_hierarchy(self, nodes: List[StructureNode]) -> List[StructureNode]:
        """Organiza nós em hierarquia otimizada"""
        # Separar nós raiz (sem parent)
        root_nodes = [node for node in nodes if node.parent is None]
        
        # Ordenar por importância e dependências
        root_nodes.sort(key=lambda n: (-n.importance_score, n.section.hierarchy_level))
        
        # Organizar filhos de cada nó raiz
        for root in root_nodes:
            self._organize_children(root)
        
        return root_nodes
    
    def _organize_children(self, parent_node: StructureNode):
        """Organiza filhos de um nó recursivamente"""
        if not parent_node.children:
            return
        
        # Ordenar filhos por importância e dependências
        parent_node.children.sort(key=lambda n: (-n.importance_score, n.section.hierarchy_level))
        
        # Recursivamente organizar netos
        for child in parent_node.children:
            self._organize_children(child)
    
    def _suggest_reorganization(self, root_nodes: List[StructureNode], 
                              pattern: StructurePattern) -> List[ContentSection]:
        """Sugere reorganização baseada no padrão detectado"""
        reorganized = []
        
        if pattern == StructurePattern.SEQUENTIAL:
            # Para conteúdo sequencial, manter ordem lógica
            reorganized = self._reorganize_sequential(root_nodes)
        elif pattern == StructurePattern.HIERARCHICAL:
            # Para conteúdo hierárquico, organizar por importância
            reorganized = self._reorganize_hierarchical(root_nodes)
        elif pattern == StructurePattern.REFERENCE:
            # Para referência, organizar alfabeticamente ou por categoria
            reorganized = self._reorganize_reference(root_nodes)
        else:
            # Para estrutura mista, usar abordagem híbrida
            reorganized = self._reorganize_mixed(root_nodes)
        
        return reorganized
    
    def _reorganize_sequential(self, root_nodes: List[StructureNode]) -> List[ContentSection]:
        """Reorganiza conteúdo sequencial"""
        sections = []
        
        # Primeiro, introduções
        intro_nodes = [n for n in root_nodes if n.section.content_type == ContentType.INTRODUCTION]
        sections.extend([n.section for n in intro_nodes])
        
        # Depois, conteúdo conceitual
        conceptual_nodes = [n for n in root_nodes if n.section.content_type == ContentType.CONCEPTUAL]
        conceptual_nodes.sort(key=lambda n: n.importance_score, reverse=True)
        sections.extend([n.section for n in conceptual_nodes])
        
        # Em seguida, conteúdo procedimental
        procedural_nodes = [n for n in root_nodes if n.section.content_type == ContentType.PROCEDURAL]
        procedural_nodes.sort(key=lambda n: n.importance_score, reverse=True)
        sections.extend([n.section for n in procedural_nodes])
        
        # Por último, referências
        reference_nodes = [n for n in root_nodes if n.section.content_type == ContentType.REFERENCE]
        sections.extend([n.section for n in reference_nodes])
        
        return sections
    
    def _reorganize_hierarchical(self, root_nodes: List[StructureNode]) -> List[ContentSection]:
        """Reorganiza conteúdo hierárquico"""
        sections = []
        
        def add_node_and_children(node: StructureNode):
            sections.append(node.section)
            for child in node.children:
                add_node_and_children(child)
        
        # Adicionar nós em ordem hierárquica
        for root in root_nodes:
            add_node_and_children(root)
        
        return sections
    
    def _reorganize_reference(self, root_nodes: List[StructureNode]) -> List[ContentSection]:
        """Reorganiza conteúdo de referência"""
        sections = []
        
        # Agrupar por tipo de conteúdo
        grouped = defaultdict(list)
        for node in root_nodes:
            grouped[node.section.content_type].append(node)
        
        # Ordenar cada grupo alfabeticamente
        for content_type in [ContentType.INTRODUCTION, ContentType.CONCEPTUAL, 
                           ContentType.PROCEDURAL, ContentType.REFERENCE]:
            if content_type in grouped:
                nodes = grouped[content_type]
                nodes.sort(key=lambda n: n.section.title)
                sections.extend([n.section for n in nodes])
        
        return sections
    
    def _reorganize_mixed(self, root_nodes: List[StructureNode]) -> List[ContentSection]:
        """Reorganiza conteúdo misto usando abordagem híbrida"""
        # Usar reorganização hierárquica como base
        return self._reorganize_hierarchical(root_nodes)
    
    def _calculate_quality_score(self, root_nodes: List[StructureNode], 
                               pattern: StructurePattern) -> float:
        """Calcula score de qualidade da estrutura"""
        score = 0.0
        total_nodes = sum(1 + len(node.children) for node in root_nodes)
        
        if total_nodes == 0:
            return 0.0
        
        # Pontos por ter introdução
        has_intro = any(n.section.content_type == ContentType.INTRODUCTION for n in root_nodes)
        if has_intro:
            score += 20.0
        
        # Pontos por hierarquia bem definida
        hierarchy_score = 0.0
        for node in root_nodes:
            if node.children:
                hierarchy_score += 10.0
                # Bonus por subseções bem organizadas
                if len(node.children) > 1:
                    hierarchy_score += 5.0
        
        score += min(hierarchy_score, 30.0)  # Máximo 30 pontos
        
        # Pontos por diversidade de tipos de conteúdo
        content_types = set()
        for node in root_nodes:
            content_types.add(node.section.content_type)
            for child in node.children:
                content_types.add(child.section.content_type)
        
        diversity_score = len(content_types) * 5.0
        score += min(diversity_score, 25.0)  # Máximo 25 pontos
        
        # Pontos por padrão adequado
        if pattern in [StructurePattern.SEQUENTIAL, StructurePattern.HIERARCHICAL]:
            score += 15.0
        elif pattern == StructurePattern.REFERENCE:
            score += 10.0
        else:
            score += 5.0
        
        # Penalizar por falta de conteúdo
        if total_nodes < 3:
            score -= 20.0
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self, root_nodes: List[StructureNode], 
                                pattern: StructurePattern, quality_score: float) -> List[str]:
        """Gera recomendações para melhorar a estrutura"""
        recommendations = []
        
        # Recomendações baseadas na qualidade
        if quality_score < 50:
            recommendations.append("A estrutura do manual pode ser significativamente melhorada")
        elif quality_score < 70:
            recommendations.append("A estrutura está adequada, mas há espaço para melhorias")
        else:
            recommendations.append("A estrutura está bem organizada")
        
        # Verificar se tem introdução
        has_intro = any(n.section.content_type == ContentType.INTRODUCTION for n in root_nodes)
        if not has_intro:
            recommendations.append("Considere adicionar uma seção de introdução")
        
        # Verificar hierarquia
        nodes_with_children = sum(1 for n in root_nodes if n.children)
        if nodes_with_children == 0:
            recommendations.append("Considere organizar o conteúdo em seções e subseções")
        
        # Recomendações baseadas no padrão
        if pattern == StructurePattern.SEQUENTIAL:
            recommendations.append("Estrutura sequencial detectada - mantenha ordem lógica dos passos")
        elif pattern == StructurePattern.HIERARCHICAL:
            recommendations.append("Estrutura hierárquica detectada - organize por tópicos principais")
        elif pattern == StructurePattern.REFERENCE:
            recommendations.append("Conteúdo de referência detectado - considere organização alfabética")
        else:
            recommendations.append("Estrutura mista - considere separar diferentes tipos de conteúdo")
        
        # Verificar balanceamento
        total_nodes = len(root_nodes)
        if total_nodes > 10:
            recommendations.append("Muitas seções principais - considere agrupar conteúdo relacionado")
        elif total_nodes < 3:
            recommendations.append("Poucas seções - considere dividir conteúdo em mais seções")
        
        return recommendations 