import random

from config import (
    PROBABILIDAD_DIARIA_VENTA,
    INCREMENTO_PROBABILIDAD_VENTA_MARKETING,
    DEMANDA_DIARIA_MAXIMA,
    DIAS_MAXIMOS_ENTREGA,
    DIAS_MAXIMOS_COBRO,
    DEMANDA_DIARIA_MINIMA,
    DIAS_MINIMOS_ENTREGA,
    DIAS_MINIMOS_COBRO,
    NOMBRE_PROVEEDOR,
    PRECIO_VENTA_UNIDAD,
)
from state import PagoPendiente, PedidoCompra, CobroPendiente, EstadoEmpresa


def marketing_activo_en_dia(estado: EstadoEmpresa) -> bool:
    """
    Devuelve True si la campaña de marketing está activa en el día actual.

    Convención:
    - si se contrata en el día 80, NO afecta al propio día 60
    - empieza a afectar desde el día 81
    - dura hasta dia_fin_marketing inclusive
    """
    if not estado.marketing_activado:
        return False

    if estado.dia_activacion_marketing is None or estado.dia_fin_marketing is None:
        return False

    return estado.dia > estado.dia_activacion_marketing and estado.dia <= estado.dia_fin_marketing


def obtener_probabilidad_venta_hoy(estado: EstadoEmpresa) -> float:
    """
    Calcula la probabilidad efectiva de venta del día,
    teniendo en cuenta si el marketing está activo.
    """
    probabilidad = PROBABILIDAD_DIARIA_VENTA

    if marketing_activo_en_dia(estado):
        probabilidad += INCREMENTO_PROBABILIDAD_VENTA_MARKETING

    return min(1.0, probabilidad)


def generar_demanda_diaria(estado: EstadoEmpresa) -> int:
    """
    Genera la demanda potencial del día.

    - No todos los días hay ventas.
    - Si hay ventas, la demanda será un número entero de unidades.
    - La probabilidad de venta puede aumentar si el marketing está activo.
    """
    probabilidad_venta_hoy = obtener_probabilidad_venta_hoy(estado)

    if random.random() < probabilidad_venta_hoy:
        return random.randint(DEMANDA_DIARIA_MINIMA, DEMANDA_DIARIA_MAXIMA)

    return 0


def generar_cobro_venta(dia: int, id_venta: int, cantidad: int) -> CobroPendiente:
    """
    Genera el cobro pendiente asociado a una venta real.
    """
    tipo_riesgo = random.choice(["bajo", "medio", "alto"])

    if tipo_riesgo == "bajo":
        probabilidad_retraso = random.uniform(0.05, 0.15)
        probabilidad_impago = random.uniform(0.00, 0.01)

    elif tipo_riesgo == "medio":
        probabilidad_retraso = random.uniform(0.15, 0.30)
        probabilidad_impago = random.uniform(0.01, 0.03)

    else:
        probabilidad_retraso = random.uniform(0.30, 0.60)
        probabilidad_impago = random.uniform(0.03, 0.08)

    return CobroPendiente(
        id=f"venta_{id_venta}",
        cliente=f"Cliente_{id_venta}",
        importe=round(cantidad * PRECIO_VENTA_UNIDAD, 2),
        dia_esperado_cobro=dia + random.randint(DIAS_MINIMOS_COBRO, DIAS_MAXIMOS_COBRO),
        probabilidad_retraso=probabilidad_retraso,
        maximo_dias_retraso=random.randint(1, 20),
        probabilidad_impago=probabilidad_impago,
    )


def generar_pedido_compra(dia: int, id_pedido: int, cantidad: int) -> PedidoCompra:
    """
    Genera un pedido al proveedor.
    El pago se hace al realizar la compra, así que aquí solo modelamos la parte logística.
    """
    dia_entrega = dia + random.randint(DIAS_MINIMOS_ENTREGA, DIAS_MAXIMOS_ENTREGA)

    return PedidoCompra(
        id=f"pedido_{id_pedido}",
        proveedor=NOMBRE_PROVEEDOR,
        cantidad=cantidad,
        dia_pedido=dia,
        dia_entrega=dia_entrega,
    )


def generar_pagos_fijos(
    duracion_episodio_dias: int = 180,
    periodo_dias: int = 30,
    importe_alquiler: float = 2000.0,
    importe_nominas: float = 8000.0,
):
    """
    Genera los pagos fijos recurrentes:
    - Alquiler
    - Nóminas

    Son críticos pero no tienen interés de demora.
    """
    pagos = []
    dias_vencimiento = list(range(periodo_dias, duracion_episodio_dias, periodo_dias))

    for dia_vencimiento in dias_vencimiento:
        pagos.append(
            PagoPendiente(
                id=f"alquiler_{dia_vencimiento}",
                proveedor="Alquiler",
                importe=importe_alquiler,
                dia_vencimiento=dia_vencimiento,
                critico=True,
                interes_anual_demora=0.0,
            )
        )

        pagos.append(
            PagoPendiente(
                id=f"nominas_{dia_vencimiento}",
                proveedor="Nominas",
                importe=importe_nominas,
                dia_vencimiento=dia_vencimiento,
                critico=True,
                interes_anual_demora=0.0,
            )
        )

    return pagos


def generar_pago_variable_aleatorio(dia: int, id_gasto: int) -> PagoPendiente:
    """
    Genera un gasto variable aleatorio no crítico.
    """
    return PagoPendiente(
        id=f"gasto_variable_{id_gasto}",
        proveedor="GastoVariable",
        importe=round(random.uniform(100.0, 600.0), 2),
        dia_vencimiento=dia,
        critico=False,
    )