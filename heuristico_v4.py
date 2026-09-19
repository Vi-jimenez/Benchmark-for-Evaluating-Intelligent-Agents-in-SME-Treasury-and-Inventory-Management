from __future__ import annotations
from config import (
    COSTE_COMPRA_UNIDAD,
    COSTE_EMISION_PEDIDO,
    COSTE_MARKETING,
    DIA_OPORTUNIDAD_MARKETING,
    LIMITE_DESCUBIERTO,
)

# --- Parámetros definidos por el usuario para v4 ---
PP_FIJO = 5    # Punto de pedido (REDUCIDO de 7 a 5)
Q_FIJO = 12    # Cantidad a pedir (12 unidades)

# --- Parámetros de Tesorería Optimizados (Basados en v3 Survival) ---
MARGEN_SEGURIDAD_CAJA = 1000.0
PREVISION_GASTOS_FIJOS = 12000.0

def _stock_en_camino(pedidos: list[dict]) -> int:
    return sum(int(p["cantidad"]) for p in pedidos if not p["recibido"])

def agent_heuristico_v4(h):
    """
    Heurístico v4:
    - Inventario: PP=5, Q=12.
    - Tesorería: Modo Supervivencia "Tacaño Extremis" para aguantar baches.
    """
    estado = h.obtener_estado()
    dia = int(estado["dia"])
    caja = float(estado["caja"])
    credito_disp = float(estado["credito_disponible"])
    deuda = float(estado["deuda"])
    
    pagos = h.listar_pagos_pendientes()
    pedidos = h.listar_pedidos_compra()

    # 1. GESTIÓN DE LIQUIDEZ Y CRÉDITO
    dias_para_fin_mes = 30 - (dia % 30)
    vienen_gastos_fuertes = dias_para_fin_mes <= 7
    
    objetivo_liquidez = MARGEN_SEGURIDAD_CAJA
    if vienen_gastos_fuertes:
        objetivo_liquidez += PREVISION_GASTOS_FIJOS

    if caja < objetivo_liquidez and credito_disp > 0:
        necesidad = objetivo_liquidez - caja
        h.disponer_credito(min(necesidad, credito_disp))
        estado = h.obtener_estado()
        caja = float(estado["caja"])
        credito_disp = float(estado["credito_disponible"])

    # 2. PRIORIZACIÓN DE PAGOS (Modo Tacaño Extremis)
    pagos_ordenados = sorted(
        pagos, 
        key=lambda p: (not bool(p["critico"]), int(p["dias_hasta_vencimiento"]))
    )

    for p in pagos_ordenados:
        importe = float(p.get("total_si_se_paga_hoy", p.get("importe")))
        es_critico = bool(p["critico"])
        dias_vencimiento = int(p["dias_hasta_vencimiento"])

        if es_critico and dias_vencimiento <= 2:
            if caja < importe and credito_disp > 0:
                h.disponer_credito(min(importe - caja + 200, credito_disp))
                estado = h.obtener_estado()
                caja = float(estado["caja"])
            
            if caja >= importe:
                h.pagar(p["id"])
                caja -= importe
        
        elif not es_critico:
            if deuda < 5000.0 and not vienen_gastos_fuertes:
                if caja > (MARGEN_SEGURIDAD_CAJA + importe + 1000.0):
                    h.pagar(p["id"])
                    caja -= importe

    # 3. MARKETING
    if hasattr(h, "hacer_marketing") and estado.get("marketing_disponible_hoy", False):
        if deuda < 5000.0 and (caja + credito_disp) >= (COSTE_MARKETING + 5000.0):
            if caja < COSTE_MARKETING:
                h.disponer_credito(COSTE_MARKETING - caja + 100)
            h.hacer_marketing()
            caja -= COSTE_MARKETING

    # 4. GESTIÓN DE INVENTARIO (PP=5, Q=12) - Veto de Supervivencia
    posicion_inventario = int(estado["inventario"]) + _stock_en_camino(pedidos)
    
    if posicion_inventario <= PP_FIJO:
        coste_pedido = Q_FIJO * COSTE_COMPRA_UNIDAD + COSTE_EMISION_PEDIDO
        puedo_pedir = True
        
        if vienen_gastos_fuertes:
            if (caja + credito_disp) < (coste_pedido + PREVISION_GASTOS_FIJOS + 2000.0):
                puedo_pedir = False
        
        if puedo_pedir:
            if caja < coste_pedido and credito_disp > 0:
                h.disponer_credito(min(coste_pedido - caja + 200, credito_disp))
            h.hacer_pedido(Q_FIJO)

    # 5. AMORTIZACIÓN TÉCNICA
    if deuda > 0 and caja > (objetivo_liquidez + 3000.0) and not vienen_gastos_fuertes:
        sobrante = caja - (objetivo_liquidez + 1000.0)
        h.amortizar_credito(min(sobrante, deuda))
