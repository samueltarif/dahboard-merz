from app.domain.cfop import classify, normalize_cfop


def test_normalize_cfop():
    assert normalize_cfop("5102/AA") == "5102"
    assert normalize_cfop(None) == ""
    assert normalize_cfop("12") == ""


def test_classify_saida_interestadual_venda():
    info = classify("6108/AA")
    assert (info.movimento, info.operacao, info.natureza) == ("Saída", "Interestadual", "Venda")


def test_classify_entradas():
    assert classify("3102").natureza == "Compra"
    assert classify("3102").operacao == "Exterior"
    assert classify("1556").natureza == "Uso e consumo"
    assert classify("1353").natureza == "Frete (CT-e)"
    assert classify("2202").natureza == "Devolução de venda"


def test_classify_sem_cfop_usa_direcao():
    assert classify(None, "1").movimento == "Entrada"
