import random

from config import (
    TIN_ANUAL_CREDITO,
    TIN_ANUAL_DESCUBIERTO,
    COMISION_DESCUBIERTO,
    COMISION_MINIMA_DESCUBIERTO,
    LIMITE_DESCUBIERTO,
    COSTE_DIARIO_ALMACENAJE_POR_UNIDAD,
    DURACION_EPISODIO,
    DIAS_LIQUIDACION_INTERESES_CREDITO,
    DIAS_LIQUIDACION_DESCUBIERTO,
    COSTE_VARIABLE_UNIDAD_VENDIDA,
)
from environment import generar_demanda_diaria, generar_cobro_venta
from state import EstadoEmpresa


def procesar_ventas_diarias(estado: EstadoEmpresa, id_venta: int):
    """
    Genera la demanda del día y ejecuta las ventas reales.
    La demanda puede verse afectada por el marketing.
    """
    demanda = generar_demanda_diaria(estado)
    unidades_vendidas = min(demanda, estado.inventario)

    if unidades_vendidas > 0:
        estado.inventario -= unidades_vendidas

        cobro = generar_cobro_venta(
            dia=estado.dia,
            id_venta=id_venta,
            cantidad=unidades_vendidas,
        )
        estado.cobros_pendientes.append(cobro)

        coste_variable_hoy = unidades_vendidas * COSTE_VARIABLE_UNIDAD_VENDIDA
        estado.caja -= coste_variable_hoy

        return id_venta + 1, {
            "demanda": demanda,
            "unidades_vendidas": unidades_vendidas,
            "ventas_perdidas": demanda - unidades_vendidas,
            "coste_variable_hoy": round(coste_variable_hoy, 2),
            "importe_cobro_generado": round(cobro.importe, 2),
        }

    return id_venta, {
        "demanda": demanda,
        "unidades_vendidas": 0,
        "ventas_perdidas": demanda,
        "coste_variable_hoy": 0.0,
        "importe_cobro_generado": 0.0,
    }


def recibir_pedidos_compra(estado: EstadoEmpresa):
    """
    Mete en inventario los pedidos cuyo día de entrega ya ha llegado.
    """
    pedidos_recibidos_hoy = []

    for pedido in estado.pedidos_compra:
        if pedido.recibido:
            continue

        if estado.dia >= pedido.dia_entrega:
            pedido.recibido = True
            pedido.dia_recepcion = estado.dia
            estado.inventario += pedido.cantidad
            pedidos_recibidos_hoy.append(pedido.id)

    return pedidos_recibidos_hoy


def aplicar_coste_almacenaje(estado: EstadoEmpresa):
    """
    Cobra el coste diario de mantener stock en almacén.
    Puede dejar la caja en negativo.
    """
    coste_almacenaje_hoy = estado.inventario * COSTE_DIARIO_ALMACENAJE_POR_UNIDAD
    estado.caja -= coste_almacenaje_hoy
    estado.coste_almacenaje_pagado += coste_almacenaje_hoy

    return coste_almacenaje_hoy


def procesar_cobros_pendientes(estado: EstadoEmpresa):
    """
    Procesa los cobros pendientes:
    - cobro normal
    - un único retraso posible
    - impago
    """
    for cobro in estado.cobros_pendientes:
        if cobro.cobrado or cobro.impagado:
            continue

        if estado.dia >= cobro.dia_esperado_cobro:
            if random.random() < cobro.probabilidad_impago:
                cobro.impagado = True
                cobro.cobrado = False
                cobro.dia_cobro = None
                continue

            if random.random() < cobro.probabilidad_retraso:
                retraso = random.randint(1, cobro.maximo_dias_retraso)
                cobro.dia_esperado_cobro += retraso

                # Solo puede retrasarse una vez
                cobro.probabilidad_retraso = 0.0
            else:
                estado.caja += cobro.importe
                cobro.cobrado = True
                cobro.dia_cobro = estado.dia


def devengar_interes_credito_diario(estado: EstadoEmpresa):
    """
    Devenga el interés diario de la póliza sobre el principal pendiente.
    No sale de caja automáticamente: se acumula hasta la liquidación mensual.
    """
    if estado.deuda <= 0:
        return 0.0

    tipo_diario = TIN_ANUAL_CREDITO / 365.0
    interes_hoy = estado.deuda * tipo_diario

    estado.intereses_credito_acumulados += interes_hoy

    return interes_hoy


def devengar_interes_descubierto_diario(estado: EstadoEmpresa):
    """
    Si la caja está en negativo al cierre operativo del día, se considera
    descubierto tácito y se devenga interés diario sobre ese saldo negativo.
    """
    if estado.caja >= 0:
        return 0.0

    descubierto_actual = abs(estado.caja)
    estado.maximo_descubierto_periodo = max(
        estado.maximo_descubierto_periodo,
        descubierto_actual,
    )
    estado.dias_en_descubierto += 1

    tipo_diario = TIN_ANUAL_DESCUBIERTO / 365.0
    interes_hoy = descubierto_actual * tipo_diario

    estado.intereses_descubierto_acumulados += interes_hoy

    return interes_hoy


def liquidar_intereses_mensuales_credito(estado: EstadoEmpresa):
    """
    Cada 30 días liquida automáticamente de caja los intereses acumulados
    de la póliza y reinicia el acumulado.
    """
    if estado.dia == 0:
        return 0.0

    if estado.dia % DIAS_LIQUIDACION_INTERESES_CREDITO != 0:
        return 0.0

    if estado.intereses_credito_acumulados <= 0:
        return 0.0

    importe_liquidado = estado.intereses_credito_acumulados

    estado.caja -= importe_liquidado
    estado.intereses_pagados += importe_liquidado
    estado.intereses_credito_acumulados = 0.0

    return importe_liquidado


def liquidar_descubierto_mensual(estado: EstadoEmpresa):
    """
    Cada 30 días liquida:
    - intereses acumulados del descubierto
    - comisión por descubierto sobre el máximo saldo negativo del periodo

    La comisión se cobra solo si hubo descubierto en el periodo.
    """
    if estado.dia == 0:
        return {
            "intereses_descubierto_liquidados": 0.0,
            "comision_descubierto_liquidada": 0.0,
            "total_descubierto_liquidado": 0.0,
        }

    if estado.dia % DIAS_LIQUIDACION_DESCUBIERTO != 0:
        return {
            "intereses_descubierto_liquidados": 0.0,
            "comision_descubierto_liquidada": 0.0,
            "total_descubierto_liquidado": 0.0,
        }

    intereses = estado.intereses_descubierto_acumulados
    comision = 0.0

    if estado.maximo_descubierto_periodo > 0:
        comision = max(
            estado.maximo_descubierto_periodo * COMISION_DESCUBIERTO,
            COMISION_MINIMA_DESCUBIERTO,
        )

    total = intereses + comision

    if total > 0:
        estado.caja -= total
        estado.intereses_descubierto_pagados += intereses
        estado.comisiones_descubierto_pagadas += comision

    estado.intereses_descubierto_acumulados = 0.0
    estado.maximo_descubierto_periodo = max(0.0, -estado.caja)

    return {
        "intereses_descubierto_liquidados": intereses,
        "comision_descubierto_liquidada": comision,
        "total_descubierto_liquidado": total,
    }


def comprobar_quiebra(estado: EstadoEmpresa):
    """
    La empresa quiebra si:
    - un pago crítico lleva más de 5 días vencido, o
    - el descubierto supera el límite máximo tolerado.
    """
    for pago in estado.pagos_pendientes:
        if pago.pagado:
            continue

        if pago.critico:
            dias_retraso = estado.dia - pago.dia_vencimiento
            if dias_retraso > 5:
                estado.en_quiebra = True
                return True

    if estado.caja < -LIMITE_DESCUBIERTO:
        estado.en_quiebra = True
        return True

    return False


def avanzar_dia(estado: EstadoEmpresa):
    """
    Avanza un día en la simulación.

    Orden:
    1. avanzar día
    2. recibir pedidos del proveedor
    3. cobrar coste de almacenaje
    4. devengar interés diario de la póliza
    5. procesar cobros pendientes
    6. devengar interés diario del descubierto si la caja está en negativo
    7. liquidar intereses mensuales de la póliza si toca
    8. liquidar descubierto mensual si toca
    9. comprobar quiebra
    """
    estado.dia += 1

    pedidos_recibidos = recibir_pedidos_compra(estado)
    coste_almacenaje_hoy = aplicar_coste_almacenaje(estado)
    interes_credito_devengado_hoy = devengar_interes_credito_diario(estado)
    procesar_cobros_pendientes(estado)
    interes_descubierto_devengado_hoy = devengar_interes_descubierto_diario(estado)

    intereses_credito_liquidados_hoy = liquidar_intereses_mensuales_credito(estado)
    liquidacion_descubierto = liquidar_descubierto_mensual(estado)

    comprobar_quiebra(estado)

    return {
        "dia": estado.dia,
        "pedidos_recibidos": pedidos_recibidos,
        "coste_almacenaje_hoy": round(coste_almacenaje_hoy, 2),
        "interes_credito_devengado_hoy": round(interes_credito_devengado_hoy, 2),
        "interes_descubierto_devengado_hoy": round(interes_descubierto_devengado_hoy, 2),
        "intereses_credito_liquidados_hoy": round(intereses_credito_liquidados_hoy, 2),
        "intereses_descubierto_liquidados_hoy": round(
            liquidacion_descubierto["intereses_descubierto_liquidados"], 2
        ),
        "comision_descubierto_liquidada_hoy": round(
            liquidacion_descubierto["comision_descubierto_liquidada"], 2
        ),
        "total_descubierto_liquidado_hoy": round(
            liquidacion_descubierto["total_descubierto_liquidado"], 2
        ),
        "intereses_credito_acumulados": round(estado.intereses_credito_acumulados, 2),
        "intereses_descubierto_acumulados": round(
            estado.intereses_descubierto_acumulados, 2
        ),
        "maximo_descubierto_periodo": round(estado.maximo_descubierto_periodo, 2),
        "dias_en_descubierto": estado.dias_en_descubierto,
        "caja": round(estado.caja, 2),
        "en_quiebra": estado.en_quiebra,
    }


def episodio_terminado(estado: EstadoEmpresa):
    return estado.en_quiebra or estado.dia >= DURACION_EPISODIO