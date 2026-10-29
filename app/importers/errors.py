class ImportFileError(Exception):
    """Erro de leitura/validação de um arquivo. A mensagem vai direto para a tela."""

    def __init__(self, message: str, *, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}
