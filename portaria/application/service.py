"""Fachada de aplicação: composição das operações e estado de execução.

A UI depende apenas de PortariaService. As capacidades são verificadas aqui,
não dependem da visibilidade de botões ou menus.
"""
from pathlib import Path
from ..config import (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS,
                      ARQUIVO_PESSOAS, ARQUIVO_VEICULOS, ARQUIVO_AUTORIZACOES,
                      CABECALHO, CABECALHO_AUDITORIA, CABECALHO_TIPOS_TEMP,
                      COLUNAS_OPCIONAIS_REGISTRO)
from ..domain.permissions import allowed
from ..domain.validation import PermissionDenied
from ..infrastructure.storage import CsvRepository, JsonRepository, JsonListRepository
from ..infrastructure.vault import EncryptedVault
from .vault_lifecycle import VaultLifecycle
from .access_operations import AccessOperations
from .identity_operations import IdentityOperations
from .gate_operations import GateOperations


class PortariaService(VaultLifecycle, AccessOperations, IdentityOperations, GateOperations):
    """Fachada compatível com chamadas da versão anterior."""

    def __init__(self, data_dir=None):
        if data_dir:
            from pathlib import Path
            base = Path(data_dir)
            paths = [base / x.name for x in (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS,
                                             ARQUIVO_PESSOAS, ARQUIVO_VEICULOS, ARQUIVO_AUTORIZACOES)]
        else:
            paths = [ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS,
                     ARQUIVO_PESSOAS, ARQUIVO_VEICULOS, ARQUIVO_AUTORIZACOES]
        self._plain_paths = paths
        self.cofre = EncryptedVault(paths[0].parent / 'dados_portaria.enc')
        self.registros_repo = CsvRepository(paths[0], CABECALHO, optional_columns=COLUNAS_OPCIONAIS_REGISTRO)
        self.auditoria_repo = CsvRepository(paths[1], CABECALHO_AUDITORIA, optional_columns=('Usuario',))
        self.tipos_repo = CsvRepository(paths[2], CABECALHO_TIPOS_TEMP)
        self.usuarios_repo = JsonRepository(paths[3])
        self.pessoas_repo = JsonListRepository(paths[4])
        self.veiculos_repo = JsonListRepository(paths[5])
        self.autorizacoes_repo = JsonListRepository(paths[6])
        self.registros = []
        self.auditoria = []
        self.tipos_temporarios = []
        self.usuarios = []
        self.pessoas = []
        self.veiculos = []
        self.autorizacoes = []
        self.sessao = {'usuario': None}
        self.chave_recuperacao = None  # exibida apenas uma vez; nunca persiste em texto puro
        self._recovery_grants = {}

    def pode(self, acao):
        u = self.sessao['usuario']
        return bool(u and allowed(u.get('Cargo'), acao))

    def exigir(self, acao):
        if not self.pode(acao):
            raise PermissionDenied('Seu cargo não tem permissão para esta ação.')

    def nome_sessao(self):
        u = self.sessao['usuario']
        return u.get('NomeExibicao', '') if u else ''

