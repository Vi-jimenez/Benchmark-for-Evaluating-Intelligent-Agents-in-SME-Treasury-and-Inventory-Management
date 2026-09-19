from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import (
    NOMBRE_PROVEEDOR,
    COSTE_COMPRA_UNIDAD,
    COSTE_EMISION_PEDIDO,
    DIA_OPORTUNIDAD_MARKETING,
    COSTE_MARKETING,
    INCREMENTO_PROBABILIDAD_VENTA_MARKETING,
    DURACION_EFECTO_MARKETING,
    PROBABILIDAD_DIARIA_VENTA,
)
from environment import generar_pedido_compra
from state import EstadoEmpresa, PagoPendiente


class HerramientasTesoreria:
    """
    Interfaz entre el agente y el entorno.
    El agente no modifica el estado directamente; solo usa estas tools.
    """

    def __init__(self, estado: EstadoEmpresa, limite_credito: float):
        self.estado = estado
        self.limite_credito = limite_credito
        self.siguiente_id_pedido = 0

    def _calcular_penalizacion_pago(self, pago: PagoPendiente, dia_actual: int) -> float:
        dias_retraso = max(0, dia_actual - pago.dia_vencimiento)
        tipo_diario_demora = pago.interes_anual_demora / 365.0
        penalizacion = pago.importe * tipo_diario_demora * dias_retraso
        return penalizacion

    def _marketing_disponible_hoy(self) -> bool:
        return (
            not self.estado.marketing_activado
            and self.estado.dia == DIA_OPORTUNIDAD_MARKETING
        )

    def _marketing_activo_hoy(self) -> bool:
        if not self.estado.marketing_activado:
            return False

        if (
            self.estado.dia_activacion_marketing is None
            or self.estado.dia_fin_marketing is None
        ):
            return False

        return (
            self.estado.dia > self.estado.dia_activacion_marketing
            and self.estado.dia <= self.estado.dia_fin_marketing
        )

    def _probabilidad_venta_efectiva_hoy(self) -> float:
        probabilidad = PROBABILIDAD_DIARIA_VENTA
        if self._marketing_activo_hoy():
            probabilidad += INCREMENTO_PROBABILIDAD_VENTA_MARKETING
        return min(1.0, probabilidad)

    def obtener_estado(self) -> Dict[str, Any]:
        credito_disponible = max(0.0, self.limite_credito - self.estado.deuda)

        pedidos_pendientes = [
            pedido for pedido in self.estado.pedidos_compra
            if not pedido.recibido
        ]

        pagos_pendientes = [
            pago for pago in self.estado.pagos_pendientes
            if not pago.pagado
        ]

        cobros_pendientes = [
            cobro for cobro in self.estado.cobros_pendientes
            if not cobro.cobrado and not cobro.impagado
        ]

        dias_restantes_marketing = 0
        if self._marketing_activo_hoy() and self.estado.dia_fin_marketing is not None:
            dias_restantes_marketing = self.estado.dia_fin_marketing - self.estado.dia + 1

        return {
            "dia": self.estado.dia,
            "caja": round(self.estado.caja, 2),
            "en_descubierto": self.estado.caja < 0,
            "saldo_descubierto_actual": round(max(0.0, -self.estado.caja), 2),
            "deuda": round(self.estado.deuda, 2),
            "intereses_credito_acumulados": round(
                self.estado.intereses_credito_acumulados, 2
            ),
            "intereses_descubierto_acumulados": round(
                self.estado.intereses_descubierto_acumulados, 2
            ),
            "limite_credito": round(self.limite_credito, 2),
            "credito_disponible": round(credito_disponible, 2),
            "inventario": self.estado.inventario,
            "pedidos_compra_pendientes": len(pedidos_pendientes),
            "pagos_pendientes": len(pagos_pendientes),
            "cobros_pendientes": len(cobros_pendientes),
            "penalizaciones_pagadas": round(self.estado.penalizaciones_pagadas, 2),
            "intereses_pagados": round(self.estado.intereses_pagados, 2),
            "intereses_descubierto_pagados": round(
                self.estado.intereses_descubierto_pagados, 2
            ),
            "comisiones_descubierto_pagadas": round(
                self.estado.comisiones_descubierto_pagadas, 2
            ),
            "coste_almacenaje_pagado": round(self.estado.coste_almacenaje_pagado, 2),
            "maximo_descubierto_periodo": round(
                self.estado.maximo_descubierto_periodo, 2
            ),
            "dias_en_descubierto": self.estado.dias_en_descubierto,
            "marketing_disponible_hoy": self._marketing_disponible_hoy(),
            "marketing_activado": self.estado.marketing_activado,
            "marketing_activo_hoy": self._marketing_activo_hoy(),
            "dia_oportunidad_marketing": DIA_OPORTUNIDAD_MARKETING,
            "coste_marketing": round(COSTE_MARKETING, 2),
            "incremento_probabilidad_venta_marketing": (
                INCREMENTO_PROBABILIDAD_VENTA_MARKETING
            ),
            "duracion_efecto_marketing": DURACION_EFECTO_MARKETING,
            "dia_activacion_marketing": self.estado.dia_activacion_marketing,
            "dia_fin_marketing": self.estado.dia_fin_marketing,
            "dias_restantes_marketing": dias_restantes_marketing,
            "gasto_marketing_pagado": round(self.estado.gasto_marketing_pagado, 2),
            "probabilidad_venta_efectiva_hoy": round(
                self._probabilidad_venta_efectiva_hoy(), 4
            ),
            "en_quiebra": self.estado.en_quiebra,
        }

    def listar_pagos_pendientes(
        self, horizonte_dias: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        hoy = self.estado.dia
        elementos = []

        for pago in self.estado.pagos_pendientes:
            if pago.pagado:
                continue

            if horizonte_dias is not None and pago.dia_vencimiento > hoy + horizonte_dias:
                continue

            dias_retraso = max(0, hoy - pago.dia_vencimiento)
            penalizacion_hoy = self._calcular_penalizacion_pago(pago, hoy)
            total_si_se_paga_hoy = pago.importe + penalizacion_hoy

            elementos.append(
                {
                    "id": pago.id,
                    "proveedor": pago.proveedor,
                    "importe": round(pago.importe, 2),
                    "dia_vencimiento": pago.dia_vencimiento,
                    "dias_hasta_vencimiento": pago.dia_vencimiento - hoy,
                    "dias_retraso_actual": dias_retraso,
                    "critico": pago.critico,
                    "interes_anual_demora": pago.interes_anual_demora,
                    "penalizacion_si_se_paga_hoy": round(penalizacion_hoy, 2),
                    "total_si_se_paga_hoy": round(total_si_se_paga_hoy, 2),
                }
            )

        elementos.sort(key=lambda x: (not x["critico"], x["dia_vencimiento"]))
        return elementos

    def listar_cobros_pendientes(self) -> List[Dict[str, Any]]:
        hoy = self.estado.dia
        elementos = []

        for cobro in self.estado.cobros_pendientes:
            if cobro.cobrado or cobro.impagado:
                continue

            elementos.append(
                {
                    "id": cobro.id,
                    "cliente": cobro.cliente,
                    "importe": round(cobro.importe, 2),
                    "dia_esperado_cobro": cobro.dia_esperado_cobro,
                    "dias_hasta_cobro": cobro.dia_esperado_cobro - hoy,
                    "probabilidad_retraso": cobro.probabilidad_retraso,
                    "maximo_dias_retraso": cobro.maximo_dias_retraso,
                    "probabilidad_impago": cobro.probabilidad_impago,
                }
            )

        elementos.sort(key=lambda x: x["dia_esperado_cobro"])
        return elementos

    def listar_pedidos_compra(self) -> List[Dict[str, Any]]:
        elementos = []

        for pedido in self.estado.pedidos_compra:
            elementos.append(
                {
                    "id": pedido.id,
                    "proveedor": pedido.proveedor,
                    "cantidad": pedido.cantidad,
                    "dia_pedido": pedido.dia_pedido,
                    "dia_entrega": pedido.dia_entrega,
                    "recibido": pedido.recibido,
                    "dia_recepcion": pedido.dia_recepcion,
                }
            )

        elementos.sort(key=lambda x: x["dia_entrega"])
        return elementos

    def hacer_pedido(self, cantidad: int) -> Dict[str, Any]:
        """
        Hace un pedido al proveedor.
        El cargo se acepta aunque la caja quede negativa.
        """
        if cantidad <= 0:
            return {
                "ok": False,
                "error": "CANTIDAD_INVALIDA",
                "cantidad": cantidad,
            }

        coste_total = round(cantidad * COSTE_COMPRA_UNIDAD + COSTE_EMISION_PEDIDO, 2)
        caja_antes = self.estado.caja
        self.estado.caja -= coste_total

        pedido = generar_pedido_compra(
            dia=self.estado.dia,
            id_pedido=self.siguiente_id_pedido,
            cantidad=cantidad,
        )
        self.siguiente_id_pedido += 1

        self.estado.pedidos_compra.append(pedido)

        return {
            "ok": True,
            "id_pedido": pedido.id,
            "proveedor": NOMBRE_PROVEEDOR,
            "cantidad": cantidad,
            "coste_unitario": round(COSTE_COMPRA_UNIDAD, 2),
            "coste_emision": round(COSTE_EMISION_PEDIDO, 2),
            "coste_total": coste_total,
            "dia_pedido": pedido.dia_pedido,
            "dia_entrega": pedido.dia_entrega,
            "caja_antes": round(caja_antes, 2),
            "caja_despues": round(self.estado.caja, 2),
            "entra_en_descubierto": self.estado.caja < 0,
            "saldo_descubierto_actual": round(max(0.0, -self.estado.caja), 2),
        }

    def hacer_marketing(self) -> Dict[str, Any]:
        """
        Contrata la campaña de marketing.
        Solo puede hacerse una vez y solo está disponible en el día fijado.
        El cargo se acepta aunque la caja quede negativa.
        """
        if self.estado.marketing_activado:
            return {
                "ok": False,
                "error": "MARKETING_YA_ACTIVADO",
                "dia_activacion_marketing": self.estado.dia_activacion_marketing,
                "dia_fin_marketing": self.estado.dia_fin_marketing,
            }

        if not self._marketing_disponible_hoy():
            return {
                "ok": False,
                "error": "MARKETING_NO_DISPONIBLE_HOY",
                "dia_actual": self.estado.dia,
                "dia_oportunidad_marketing": DIA_OPORTUNIDAD_MARKETING,
            }

        caja_antes = self.estado.caja
        self.estado.caja -= COSTE_MARKETING
        self.estado.marketing_activado = True
        self.estado.dia_activacion_marketing = self.estado.dia
        self.estado.dia_fin_marketing = self.estado.dia + DURACION_EFECTO_MARKETING
        self.estado.gasto_marketing_pagado += COSTE_MARKETING

        return {
            "ok": True,
            "dia_activacion_marketing": self.estado.dia_activacion_marketing,
            "dia_inicio_efecto_marketing": self.estado.dia_activacion_marketing + 1,
            "dia_fin_marketing": self.estado.dia_fin_marketing,
            "coste_marketing": round(COSTE_MARKETING, 2),
            "incremento_probabilidad_venta_marketing": (
                INCREMENTO_PROBABILIDAD_VENTA_MARKETING
            ),
            "duracion_efecto_marketing": DURACION_EFECTO_MARKETING,
            "caja_antes": round(caja_antes, 2),
            "caja_despues": round(self.estado.caja, 2),
            "entra_en_descubierto": self.estado.caja < 0,
            "saldo_descubierto_actual": round(max(0.0, -self.estado.caja), 2),
        }

    def pagar(self, id_pago: str) -> Dict[str, Any]:
        pago_objetivo = None
        for pago in self.estado.pagos_pendientes:
            if pago.id == id_pago:
                pago_objetivo = pago
                break

        if pago_objetivo is None:
            return {
                "ok": False,
                "error": "PAGO_NO_ENCONTRADO",
                "id": id_pago,
            }

        if pago_objetivo.pagado:
            return {
                "ok": False,
                "error": "PAGO_YA_REALIZADO",
                "id": id_pago,
            }

        dias_retraso = max(0, self.estado.dia - pago_objetivo.dia_vencimiento)
        penalizacion = self._calcular_penalizacion_pago(
            pago_objetivo, self.estado.dia
        )
        total_a_pagar = pago_objetivo.importe + penalizacion

        caja_antes = self.estado.caja
        self.estado.caja -= total_a_pagar
        self.estado.penalizaciones_pagadas += penalizacion

        pago_objetivo.pagado = True
        pago_objetivo.dia_pago = self.estado.dia

        return {
            "ok": True,
            "id": id_pago,
            "dia_pago": self.estado.dia,
            "dias_retraso": dias_retraso,
            "principal": round(pago_objetivo.importe, 2),
            "penalizacion": round(penalizacion, 2),
            "total_pagado": round(total_a_pagar, 2),
            "caja_antes": round(caja_antes, 2),
            "caja_despues": round(self.estado.caja, 2),
            "entra_en_descubierto": self.estado.caja < 0,
            "saldo_descubierto_actual": round(max(0.0, -self.estado.caja), 2),
        }

    def disponer_credito(self, importe: float) -> Dict[str, Any]:
        """
        Dispone principal de la póliza de crédito.
        """
        if importe <= 0:
            return {
                "ok": False,
                "error": "IMPORTE_INVALIDO",
                "importe": importe,
            }

        credito_disponible = max(0.0, self.limite_credito - self.estado.deuda)
        importe_dispuesto = min(importe, credito_disponible)

        if importe_dispuesto <= 0:
            return {
                "ok": False,
                "error": "CREDITO_NO_DISPONIBLE",
                "credito_disponible": round(credito_disponible, 2),
            }

        self.estado.deuda += importe_dispuesto
        self.estado.caja += importe_dispuesto

        return {
            "ok": True,
            "importe_solicitado": round(importe, 2),
            "importe_dispuesto": round(importe_dispuesto, 2),
            "caja_despues": round(self.estado.caja, 2),
            "deuda_despues": round(self.estado.deuda, 2),
            "intereses_credito_acumulados": round(
                self.estado.intereses_credito_acumulados, 2
            ),
            "credito_disponible_despues": round(
                max(0.0, self.limite_credito - self.estado.deuda), 2
            ),
        }

    def amortizar_credito(self, importe: float) -> Dict[str, Any]:
        """
        Amortiza principal de la póliza de crédito.
        No paga intereses acumulados: esos se liquidan automáticamente cada 30 días.
        """
        if importe <= 0:
            return {
                "ok": False,
                "error": "IMPORTE_INVALIDO",
                "importe": importe,
            }

        if self.estado.deuda <= 0:
            return {
                "ok": False,
                "error": "SIN_DEUDA",
                "deuda": round(self.estado.deuda, 2),
            }

        caja_utilizable = max(0.0, self.estado.caja)
        importe_amortizado = min(importe, self.estado.deuda, caja_utilizable)

        if importe_amortizado <= 0:
            return {
                "ok": False,
                "error": "CAJA_INSUFICIENTE",
                "caja": round(self.estado.caja, 2),
            }

        self.estado.deuda -= importe_amortizado
        self.estado.caja -= importe_amortizado

        return {
            "ok": True,
            "importe_solicitado": round(importe, 2),
            "importe_amortizado": round(importe_amortizado, 2),
            "caja_despues": round(self.estado.caja, 2),
            "deuda_despues": round(self.estado.deuda, 2),
            "intereses_credito_acumulados": round(
                self.estado.intereses_credito_acumulados, 2
            ),
            "credito_disponible_despues": round(
                max(0.0, self.limite_credito - self.estado.deuda), 2
            ),
        }