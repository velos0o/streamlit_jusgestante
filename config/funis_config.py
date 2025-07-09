"""
Configuração dos funis do Bitrix24
Seguindo Object Calisthenics: encapsulamento de tipos primitivos e evitando números mágicos
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Stage:
    """Representa um estágio do funil"""
    id: int
    stage_id: str
    stage_name: str
    sort_order: int
    semantics: Optional[str]
    semantics_description: str


@dataclass
class Category:
    """Representa uma categoria/funil do Bitrix24"""
    category_id: int
    category_name: str
    total_stages: int
    description: str
    stages: List[Stage]


class FunilConfig:
    """Configuração centralizada dos funis"""
    
    COMERCIAL_ID = 0
    TRAMITES_ID = 2
    AUDIENCIA_ID = 4
    RECEBIMENTO_ID = 6
    DESPESAS_ID = 8
    ENTREVISTA_ID = 11
    
    @classmethod
    def get_comercial_config(cls) -> Category:
        """Retorna configuração do funil comercial"""
        stages = [
            Stage(101, "NEW", "EM ESPERA DE ATENDIMENTO", 10, None, "Neutro"),
            Stage(103, "PREPARATION", "NÃO INTERAGIU", 20, None, "Neutro"),
            Stage(105, "PREPAYMENT_INVOICE", "QUEBRA NA COMUNICAÇÃO", 30, None, "Neutro"),
            Stage(184, "UC_V6262P", "ABORDAGEM INICIAL", 40, None, "Neutro"),
            Stage(107, "EXECUTING", "AGENDADO", 50, None, "Neutro"),
            Stage(109, "FINAL_INVOICE", "REMARCA AGENDA", 60, None, "Neutro"),
            Stage(178, "1", "NEGOCIAÇÃO", 70, None, "Neutro"),
            Stage(236, "UC_0NW0PY", "CONTRATO/PROCURAÇÃO/TERMOS", 80, None, "Neutro"),
            Stage(182, "3", "DOCUMENTAÇÕES PENDENTES", 90, None, "Neutro"),
            Stage(180, "2", "ASSINATURAS PENDENTES", 100, None, "Neutro"),
            Stage(303, "UC_ZCYQIZ", "SEM INTERESSE", 110, None, "Neutro"),
            Stage(111, "WON", "NEGÓCIO FECHADO", 120, "S", "Sucesso"),
            Stage(113, "LOSE", "OUTROS ADVOGADOS", 130, "F", "Falha"),
            Stage(115, "APOLOGY", "NÃO HÁBIL", 140, "F", "Falha")
        ]
        
        return Category(
            category_id=cls.COMERCIAL_ID,
            category_name="COMERCIAL",
            total_stages=14,
            description="Funil de vendas e negociação comercial",
            stages=stages
        )
    
    @classmethod
    def get_tramites_config(cls) -> Category:
        """Retorna configuração do funil de trâmites administrativos"""
        stages = [
            Stage(186, "C2:NEW", "FILA", 10, None, "Neutro"),
            Stage(188, "C2:PREPARATION", "PENDENTE DOCUMENTOS", 20, None, "Neutro"),
            Stage(190, "C2:PREPAYMENT_INVOICE", "PENDENTE FORMALIZAÇÃO DE CÁLCULO", 30, None, "Neutro"),
            Stage(192, "C2:EXECUTING", "PENDENTE PETIÇÃO INICIAL", 40, None, "Neutro"),
            Stage(194, "C2:FINAL_INVOICE", "PENDENTE REVISAR PETIÇÃO", 50, None, "Neutro"),
            Stage(284, "C2:UC_U7A8AF", "REVERSÃO", 60, None, "Neutro"),
            Stage(196, "C2:WON", "PROTOCOLADO COM SUCESSO", 70, "S", "Sucesso"),
            Stage(198, "C2:LOSE", "CANCELAMENTO", 80, "F", "Falha")
        ]
        
        return Category(
            category_id=cls.TRAMITES_ID,
            category_name="TRÂMITES ADMINISTRATIVO",
            total_stages=8,
            description="Funil de processos administrativos e documentação",
            stages=stages
        )
    
    @classmethod
    def get_audiencia_config(cls) -> Category:
        """Retorna configuração do funil de audiências"""
        stages = [
            Stage(218, "C4:NEW", "PEND. HORÁRIO E LOCAL", 10, None, "Neutro"),
            Stage(244, "C4:UC_K7MNY3", "CLIENTE AVISADO", 20, None, "Neutro"),
            Stage(220, "C4:PREPARATION", "1º AUDIÊNCIA MARCADA", 30, None, "Neutro"),
            Stage(242, "C4:UC_LPKHRO", "CLIENTE AVISADO", 40, None, "Neutro"),
            Stage(226, "C4:FINAL_INVOICE", "EM ACORDO", 50, None, "Neutro"),
            Stage(224, "C4:EXECUTING", "CONTESTAÇÃO (RAZÕES FINAIS)", 60, None, "Neutro"),
            Stage(278, "C4:UC_83JT4W", "AGUARDANDO SENTENÇA", 70, None, "Neutro"),
            Stage(228, "C4:WON", "ACORDO", 80, "S", "Sucesso"),
            Stage(230, "C4:LOSE", "RECURSO", 90, "F", "Falha"),
            Stage(301, "C4:UC_PP1J4N", "CANCELADOS", 100, "F", "Falha"),
            Stage(305, "C4:UC_QK3BDP", "SENTENÇA PROCEDENTE", 110, "F", "Falha")
        ]
        
        return Category(
            category_id=cls.AUDIENCIA_ID,
            category_name="AUDIÊNCIA",
            total_stages=11,
            description="Funil de audiências e procedimentos judiciais",
            stages=stages
        )
        
    @classmethod
    def get_entrevista_config(cls) -> Category:
        """Retorna configuração do funil de entrevista"""
        stages = [
            Stage(313, "C11:NEW", "ENTREVISTA PENDENTE", 10, None, "Neutro"),
            Stage(329, "C11:UC_RA8DBB", "ENTREVISTA AGENDADA", 20, None, "Neutro"),
            Stage(331, "C11:UC_7TNBPV", "ENTREVISTA REALIZADA", 30, None, "Neutro"),
            Stage(335, "C11:UC_JKFZFO", "PEND. ASSINATURA", 40, None, "Neutro"),
            Stage(333, "C11:UC_8LT60K", "PEND. DOC", 50, None, "Neutro"),
            Stage(323, "C11:WON", "VALIDADO", 60, "S", "Sucesso"),
            Stage(325, "C11:LOSE", "APENAS AUXILO", 70, "F", "Falha"),
            Stage(339, "C11:UC_ASF49M", "RECUSADO", 80, "F", "Falha"),
            Stage(341, "C11:UC_VDDDMG", "DESQUALIFICADO", 90, "F", "Falha"),
        ]
        
        return Category(
            category_id=cls.ENTREVISTA_ID,
            category_name="ENTREVISTA",
            total_stages=9,
            description="Funil de entrevista de validação",
            stages=stages
        )
    
    @classmethod
    def get_all_categories(cls) -> Dict[str, Category]:
        """Retorna todas as categorias disponíveis"""
        return {
            "COMERCIAL": cls.get_comercial_config(),
            "TRAMITES": cls.get_tramites_config(),
            "AUDIENCIA": cls.get_audiencia_config(),
            "ENTREVISTA": cls.get_entrevista_config()
        }
    
    @classmethod
    def get_category_by_id(cls, category_id: int) -> Optional[Category]:
        """Retorna categoria por ID"""
        category_map = {
            cls.COMERCIAL_ID: cls.get_comercial_config(),
            cls.TRAMITES_ID: cls.get_tramites_config(),
            cls.AUDIENCIA_ID: cls.get_audiencia_config(),
            cls.ENTREVISTA_ID: cls.get_entrevista_config()
        }
        return category_map.get(category_id) 