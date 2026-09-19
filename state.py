from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from config import INTERES_ANUAL_DEMORA


@dataclass
class PagoPendiente:
    id: str
    proveedor: str
    importe: float
    dia_vencimiento: int
    critico: bool = False

    interes_anual_demora: float = INTERES_ANUAL_DEMORA
    pagado: bool = False
    dia_pago: Optional[int] = None


@dataclass
class CobroPendiente:
    id: str
    cliente: str
    importe: float
    dia_esperado_cobro: int

    probabilidad_retraso: float
    maximo_dias_retraso: int
    probabilidad_impago: float

    cobrado: bool = False
    impagado: bool = False
    dia_cobro: Optional[int] = None


@dataclass
class PedidoCompra:
    id: str
    proveedor: str
    cantidad: int
    dia_pedido: int
    dia_entrega: int

    recibido: bool = False
    dia_recepcion: Optional[int] = None


@dataclass
class EstadoEmpresa:
    dia: int = 0
    caja: float = 0.0

    # Principal pendiente de la póliza / línea de crédito
    deuda: float = 0.0

    # Intereses devengados desde la última liquidación mensual de la póliza
    intereses_credito_acumulados: float = 0.0

    # Intereses devengados por descubierto tácito desde la última liquidación
    intereses_descubierto_acumulados: float = 0.0

    # Mayor saldo negativo (en valor absoluto) alcanzado en el periodo actual
    maximo_descubierto_periodo: float = 0.0

    pagos_pendientes: List[PagoPendiente] = field(default_factory=list)
    cobros_pendientes: List[CobroPendiente] = field(default_factory=list)

    inventario: int = 0
    pedidos_compra: List[PedidoCompra] = field(default_factory=list)

    penalizaciones_pagadas: float = 0.0

    # Intereses de la póliza ya liquidados y pagados
    intereses_pagados: float = 0.0

    # Intereses de descubierto ya liquidados y pagados
    intereses_descubierto_pagados: float = 0.0

    # Comisiones de descubierto ya cobradas
    comisiones_descubierto_pagadas: float = 0.0

    coste_almacenaje_pagado: float = 0.0

    # Métrica opcional útil para análisis
    dias_en_descubierto: int = 0

    # Marketing
    marketing_activado: bool = False
    dia_activacion_marketing: Optional[int] = None
    dia_fin_marketing: Optional[int] = None
    gasto_marketing_pagado: float = 0.0

    en_quiebra: bool = False