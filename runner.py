from __future__ import annotations

import random
from typing import Any, Callable, Dict

from config import (
    DURACION_EPISODIO,
    INVENTARIO_INICIAL,
    PROBABILIDAD_GASTO_VARIABLE,
)
from environment import generar_pagos_fijos, generar_pago_variable_aleatorio
from simulator import avanzar_dia, episodio_terminado, procesar_ventas_diarias
from state import EstadoEmpresa, PagoPendiente
from tools import HerramientasTesoreria


TipoAgente = Callable[[HerramientasTesoreria], None]


def calcular_importe_pago_exigible(pago: PagoPendiente, dia_actual: int) -> float:
    """
    Devuelve lo que realmente pesa económicamente un pago pendiente a fecha de hoy:
    principal + penalización de demora acumulada.
    """
    dias_retraso = max(0, dia_actual - pago.dia_vencimiento)
    penalizacion = pago.importe * (pago.interes_anual_demora / 365.0) * dias_retraso
    return pago.importe + penalizacion


def calcular_score(estado: EstadoEmpresa) -> float:
    """
    Score económico final.

    Suma:
    - caja
    - cobros pendientes no impagados

    Resta:
    - deuda principal de la póliza
    - intereses de crédito acumulados no liquidados
    - intereses de descubierto acumulados no liquidados
    - pagos pendientes valorados por su coste exigible hoy

    El inventario final NO entra en el score.
    """
    importe_cobros_pendientes = sum(
        cobro.importe
        for cobro in estado.cobros_pendientes
        if not cobro.cobrado and not cobro.impagado
    )

    importe_pagos_pendientes_exigible = sum(
        calcular_importe_pago_exigible(pago, estado.dia)
        for pago in estado.pagos_pendientes
        if not pago.pagado
    )

    score = (
        estado.caja
        + importe_cobros_pendientes
        - estado.deuda
        - estado.intereses_credito_acumulados
        - estado.intereses_descubierto_acumulados
        - importe_pagos_pendientes_exigible
    )

    return round(score, 2)


def ejecutar_episodio(
    funcion_agente: TipoAgente,
    semilla: int = 0,
    limite_credito: float = 15000.0,
) -> Dict[str, Any]:
    random.seed(semilla)

    estado = EstadoEmpresa(
        dia=0,
        caja=5000.0,
        deuda=0.0,
        intereses_credito_acumulados=0.0,
        intereses_descubierto_acumulados=0.0,
        inventario=INVENTARIO_INICIAL,
    )

    estado.pagos_pendientes.extend(
        generar_pagos_fijos(duracion_episodio_dias=DURACION_EPISODIO)
    )

    herramientas = HerramientasTesoreria(estado=estado, limite_credito=limite_credito)

    id_venta = 0
    id_gasto = 0

    while not episodio_terminado(estado):
        id_venta, _ = procesar_ventas_diarias(estado, id_venta)

        if random.random() < PROBABILIDAD_GASTO_VARIABLE:
            nuevo_gasto = generar_pago_variable_aleatorio(estado.dia, id_gasto)
            estado.pagos_pendientes.append(nuevo_gasto)
            id_gasto += 1

        funcion_agente(herramientas)

        avanzar_dia(estado)

    total_cobros = len(estado.cobros_pendientes)
    cobrados = sum(1 for cobro in estado.cobros_pendientes if cobro.cobrado)
    impagados = sum(1 for cobro in estado.cobros_pendientes if cobro.impagado)

    total_pagos_no_pagados = sum(
        1 for pago in estado.pagos_pendientes if not pago.pagado
    )

    importe_cobros_pendientes = sum(
        cobro.importe
        for cobro in estado.cobros_pendientes
        if not cobro.cobrado and not cobro.impagado
    )

    importe_pagos_pendientes_principal = sum(
        pago.importe
        for pago in estado.pagos_pendientes
        if not pago.pagado
    )

    importe_pagos_pendientes_exigible = sum(
        calcular_importe_pago_exigible(pago, estado.dia)
        for pago in estado.pagos_pendientes
        if not pago.pagado
    )

    total_unidades_pedidas = sum(pedido.cantidad for pedido in estado.pedidos_compra)
    total_unidades_recibidas = sum(
        pedido.cantidad for pedido in estado.pedidos_compra if pedido.recibido
    )

    # Cálculo detallado del score para devolución
    importe_cobros_score = round(importe_cobros_pendientes, 2)
    importe_pagos_score = round(importe_pagos_pendientes_exigible, 2)
    deuda_score = round(estado.deuda, 2)
    int_credito_score = round(estado.intereses_credito_acumulados, 2)
    int_desc_score = round(estado.intereses_descubierto_acumulados, 2)
    caja_score = round(estado.caja, 2)
    
    score_final = calcular_score(estado)

    return {
        "dia_final": estado.dia,
        "caja_final": caja_score,
        "deuda_final": deuda_score,
        "intereses_credito_acumulados": int_credito_score,
        "intereses_descubierto_acumulados": int_desc_score,
        "inventario_final": estado.inventario,
        "intereses_pagados": round(estado.intereses_pagados, 2),
        "intereses_descubierto_pagados": round(
            estado.intereses_descubierto_pagados, 2
        ),
        "comisiones_descubierto_pagadas": round(
            estado.comisiones_descubierto_pagadas, 2
        ),
        "penalizaciones_pagadas": round(estado.penalizaciones_pagadas, 2),
        "coste_almacenaje_pagado": round(estado.coste_almacenaje_pagado, 2),
        "dias_en_descubierto": estado.dias_en_descubierto,
        "maximo_descubierto_periodo_final": round(
            estado.maximo_descubierto_periodo, 2
        ),
        "marketing_activado": estado.marketing_activado,
        "dia_activacion_marketing": estado.dia_activacion_marketing,
        "dia_fin_marketing": estado.dia_fin_marketing,
        "gasto_marketing_pagado": round(estado.gasto_marketing_pagado, 2),
        "cobros_totales": total_cobros,
        "cobrados": cobrados,
        "impagados": impagados,
        "importe_cobros_pendientes_score": importe_cobros_score,
        "pagos_totales": len(estado.pagos_pendientes),
        "pagos_no_pagados": total_pagos_no_pagados,
        "importe_pagos_pendientes_exigible_score": importe_pagos_score,
        "pedidos_compra_totales": len(estado.pedidos_compra),
        "unidades_pedidas_totales": total_unidades_pedidas,
        "unidades_recibidas_totales": total_unidades_recibidas,
        "en_quiebra": estado.en_quiebra,
        "score": score_final,
        "detalle_score": {
            "caja": caja_score,
            "cobros_pendientes": importe_cobros_score,
            "deuda_póliza": -deuda_score,
            "intereses_póliza_acum": -int_credito_score,
            "intereses_descubierto_acum": -int_desc_score,
            "pagos_pendientes_exigibles": -importe_pagos_score
        }
    }
