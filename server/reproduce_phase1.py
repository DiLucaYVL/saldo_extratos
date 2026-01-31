
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add project root to sys.path
file_path = Path(__file__).resolve()
root_path = file_path.parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from server.app.conciliacao.motor import _fase_agrupamento_conta_item

def test_phase1_concatenation():
    print("\n--- Testing Phase 1 (Agrupamento Conta/Item) ---")
    # Phase 1: Same Item, Same Date
    seta_1 = {
        "_id": "seta_p1_1",
        "conta_norm": "12345",
        "data_norm": "2023-10-27",
        "data_obj": date(2023, 10, 27),
        "valor_decimal": Decimal("100.00"),
        "item": "001",
        "registro": {
            "descricao": "DESC 1",
            "valor": 100.00,
            "item": "001",
            "documento": "DOC1",
            "rp": "A",
            "conta": "12345-6",
            "data": "2023-10-27"
        }
    }
    seta_2 = {
        "_id": "seta_p1_2",
        "conta_norm": "12345",
        "data_norm": "2023-10-27",
        "data_obj": date(2023, 10, 27),
        "valor_decimal": Decimal("200.00"),
        "item": "001",
        "registro": {
            "descricao": "DESC 2",
            "valor": 200.00,
            "item": "001",
            "documento": "DOC2",
            "rp": "B",
            "conta": "12345-6",
            "data": "2023-10-27"
        }
    }
    
    # Bank item: Sum 300.00
    banco_1 = {
        "_id": "banco_p1",
        "conta_norm": "12345",
        "data_norm": "2023-10-27",
        "data_obj": date(2023, 10, 27),
        "valor_decimal": Decimal("300.00"),
        "registro": {
            "descricao": "BANK SUM",
            "valor": 300.00,
            "conta": "12345-6",
            "data": "2023-10-27"
        }
    }
    
    result = _fase_agrupamento_conta_item([banco_1], [seta_1, seta_2])
    conciliados = result["conciliados"]
    print(f"Conciliados count: {len(conciliados)}")
    
    if conciliados:
        c = conciliados[0]
        seta_res = c["seta"]
        print(f"Fase: {c['fase']}")
        print(f"Valor: {seta_res.get('valor')}")
        print(f"Item: {seta_res.get('item')}")
        print(f"Documento: {seta_res.get('documento')}")
        
        if c['fase'] == 1 and ";" in str(seta_res.get('valor')):
            print("PASS: Phase 1 concatenated correctly.")
        else:
             print("FAIL: Phase 1 check failed.")
    else:
        print("FAIL: Phase 1 no match.")

def test_phase1_5_concatenation():
    print("\n--- Testing Phase 1.5 (Agrupamento Conta/RP/Documento) ---")
    # Phase 1.5: Different Item, Same RP, Same Date
    seta_1 = {
        "_id": "seta_p15_1",
        "conta_norm": "12345",
        "data_norm": "2023-10-28",
        "data_obj": date(2023, 10, 28),
        "valor_decimal": Decimal("50.00"),
        "item": "002",
        "registro": {
            "descricao": "DESC 3",
            "valor": 50.00,
            "item": "002",
            "documento": "DOC3",
            "rp": "SAME_RP",
            "conta": "12345-6",
            "data": "2023-10-28"
        }
    }
    seta_2 = {
        "_id": "seta_p15_2",
        "conta_norm": "12345",
        "data_norm": "2023-10-28",
        "data_obj": date(2023, 10, 28),
        "valor_decimal": Decimal("60.00"),
        "item": "003",
        "registro": {
            "descricao": "DESC 4",
            "valor": 60.00,
            "item": "003",
            "documento": "DOC3", # Same doc to trigger connected components
            "rp": "SAME_RP",
            "conta": "12345-6",
            "data": "2023-10-28"
        }
    }
    
    # Bank item: Sum 110.00
    banco_1 = {
        "_id": "banco_p15",
        "conta_norm": "12345",
        "data_norm": "2023-10-28",
        "data_obj": date(2023, 10, 28),
        "valor_decimal": Decimal("110.00"),
        "registro": {
            "descricao": "BANK SUM 2",
            "valor": 110.00,
            "conta": "12345-6",
            "data": "2023-10-28"
        }
    }
    
    result = _fase_agrupamento_conta_item([banco_1], [seta_1, seta_2])
    conciliados = result["conciliados"]
    print(f"Conciliados count: {len(conciliados)}")
    
    if conciliados:
        c = conciliados[0]
        seta_res = c["seta"]
        print(f"Fase: {c['fase']}")
        print(f"Valor: {seta_res.get('valor')}")
        print(f"Item: {seta_res.get('item')}")
        print(f"Documento: {seta_res.get('documento')}")
        
        if c['fase'] == 1.5 and ";" in str(seta_res.get('valor')) and ";" in str(seta_res.get('item')):
            print("PASS: Phase 1.5 concatenated correctly.")
        else:
             print("FAIL: Phase 1.5 check failed.")
    else:
        print("FAIL: Phase 1.5 no match.")

if __name__ == "__main__":
    test_phase1_concatenation()
    test_phase1_5_concatenation()
